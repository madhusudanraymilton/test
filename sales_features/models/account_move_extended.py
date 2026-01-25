from odoo import models, fields, api, _ 
from odoo.exceptions import UserError, ValidationError

class AccountMoveExtended(models.Model):
    _inherit = 'account.move'

    profile_id = fields.Many2one('bd.profile.name', string="Profile", tracking=True)
    
    allowed_account_ids = fields.Many2many(
        'account.account',
        compute='_compute_allowed_account_ids',
        string="Allowed Accounts",
        store=False
    )

    @api.depends('profile_id', 'profile_id.allowed_account', 'company_id')
    def _compute_allowed_account_ids(self):
        """
        Returns allowed account IDs based on profile.
        If no profile: returns ALL account IDs (so domain shows everything)
        If profile selected: returns only allowed account IDs
        """
        AccountAccount = self.env['account.account']
        
        for record in self:
            if record.profile_id and record.profile_id.allowed_account:
                # Profile with allowed accounts: restrict to those only
                record.allowed_account_ids = record.profile_id.allowed_account
            else:
                # No profile OR no allowed accounts: return ALL accounts
                all_accounts = AccountAccount.search([
                    ('company_id', 'in', [record.company_id.id, False]),
                    ('deprecated', '=', False)
                ])
                record.allowed_account_ids = all_accounts

    @api.onchange('profile_id')
    def _onchange_profile_id(self):
        """
        Trigger recompute and validate when profile changes
        """
        # Force recompute of allowed accounts
        self._compute_allowed_account_ids()
        
        if not self.profile_id:
            return 
        
        income_account = self.profile_id.income_account
        receivable_account = self.profile_id.receivable_account

        # Validate income account
        if income_account and income_account.internal_group in ('receivable', 'payable'):
            raise ValidationError(
                "Profile income account must be an Income or Expense account, "
                "not a Receivable/Payable account."
            )
        
        # Validate receivable account
        if receivable_account and receivable_account.account_type != 'asset_receivable':
            raise ValidationError(
                "Profile receivable account must be a Receivable account type."
            )

        # Update invoice lines with income account
        if income_account:
            for line in self.invoice_line_ids:
                if not line.display_type:
                    line.account_id = income_account

        # Update payment term lines with receivable account
        if receivable_account:
            for line in self.line_ids.filtered(lambda l: l.display_type == 'payment_term'):
                line.account_id = receivable_account

    @api.constrains('line_ids', 'profile_id')
    def _check_account_allowed(self):
        """
        Validate that all line accounts are in the allowed accounts list
        """
        for move in self:
            if move.profile_id and move.profile_id.allowed_account:
                allowed_ids = move.profile_id.allowed_account.ids
                for line in move.line_ids.filtered(lambda l: not l.display_type):
                    if line.account_id and line.account_id.id not in allowed_ids:
                        raise ValidationError(
                            f"Account '{line.account_id.display_name}' is not allowed for profile '{move.profile_id.name}'. "
                            f"Please select from the allowed accounts."
                        )
    
    def action_register_payment(self):
        """
        Override the register payment action to auto-pay without wizard
        when profile_id is set with a journal
        """
        # Check if profile is set and has a journal configured
        if self.profile_id and self.profile_id.journal_id:
            return self._auto_register_payment()
        
        # Otherwise, use the default wizard behavior
        return super(AccountMoveExtended, self).action_register_payment()

    def _auto_register_payment(self):
        """
        Automatically register payment without showing wizard
        """
        for move in self:
            # Validate invoice state
            if move.state != 'posted':
                raise UserError(_("You can only register payment for posted invoices."))
            
            if move.payment_state in ('paid', 'in_payment'):
                raise UserError(_("This invoice is already paid or in payment process."))
            
            # Validate profile and journal
            if not move.profile_id:
                raise UserError(_("Please set a Profile on the invoice."))
            
            if not move.profile_id.journal_id:
                raise UserError(_("Please set a Journal on the selected Profile."))

            journal = move.profile_id.journal_id
            
            # Determine payment type based on move type
            if move.move_type in ('out_invoice', 'in_refund'):
                payment_type = 'inbound'
            elif move.move_type in ('in_invoice', 'out_refund'):
                payment_type = 'outbound'
            else:
                raise UserError(_("Cannot register payment for this document type."))

            # Create payment directly without wizard (NO 'ref' field)
            payment = self.env['account.payment.register'].create({
                'payment_type': payment_type,
                #'partner_type': 'customer' if move.move_type in ('out_invoice', 'out_refund') else 'supplier',
                #'partner_id': move.commercial_partner_id.id,
                'amount': move.amount_residual,
                #'currency_id': move.currency_id.id,
                'date': fields.Date.context_today(self),
                'journal_id': journal.id,
                #'company_id': move.company_id.id,
                #'payment_method_line_id': self._get_payment_method_line(journal, payment_type),
            })

            # Post the payment
            payment.action_post()

            # Reconcile with invoice
            move_lines = move.line_ids.filtered(
                lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable') 
                and not line.reconciled
            )
            
            payment_lines = payment.line_ids.filtered(
                lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
            )

            (move_lines + payment_lines).reconcile()

        # Return action to refresh the view or show notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payment Registered'),
                'message': _('Payment has been registered successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _get_payment_method_line(self, journal, payment_type):
        """
        Get the appropriate payment method line for the journal
        """
        if payment_type == 'inbound':
            available_payment_method_lines = journal.inbound_payment_method_line_ids
        else:
            available_payment_method_lines = journal.outbound_payment_method_line_ids

        if not available_payment_method_lines:
            raise UserError(_(
                "No payment method configured for journal '%s'. "
                "Please configure payment methods in the journal settings."
            ) % journal.name)

        # Return the first available payment method
        return available_payment_method_lines[0].id


class AccountMoveLineExtended(models.Model):
    _inherit = 'account.move.line'