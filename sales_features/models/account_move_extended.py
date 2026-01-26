from odoo import models, fields, api, _ 
from odoo.exceptions import UserError, ValidationError

class AccountMoveExtended(models.Model):
    _inherit = 'account.move'

    profile_id = fields.Many2one('bd.profile.name', string="Profile")
    allowed_account_ids = fields.Many2many(
        'account.account', 
        string="Allowed Account",
        compute='_compute_allowed_account_ids'
    )

    @api.depends('profile_id','allowed_account_ids')
    def _compute_allowed_account_ids(self):
        account_account = self.env['account.account']
        for record in self:
            if not self.allowed_account_ids:
                self.allowed_account_ids = account_account.search([])
                

    # @api.onchange("partner_id")
    # def get_profile(self):
            
    @api.onchange('profile_id')
    def _onchange_profile_id(self):
        if not self.profile_id:
            return

        income_account = self.profile_id.income_account
        receivable_account = self.profile_id.receivable_account
        self.allowed_account_ids = self.profile_id.allowed_account.ids

        if income_account.internal_group in ('receivable', 'payable'):
            raise ValidationError(
                "Profile income account must be an Income or Expense account, "
                "not a Receivable/Payable account."
            )
        
        # Validate receivable account
        if receivable_account and receivable_account.account_type != 'asset_receivable':
            raise ValidationError(
                "Profile receivable account must be a Receivable account type."
            )
        

        for line in self.invoice_line_ids:
            line.account_id = income_account

        
        if receivable_account:
            for line in self.line_ids.filtered(lambda l: l.display_type == 'payment_term'):
                line.account_id = receivable_account
        
        # return {
        #     'domain': {
        #         'allowed_account_ids': [('id', 'in', self.profile_id.allowed_account.ids)]
        #     }
        # }


    def action_register_payment(self):
        """
        Override the register payment action to auto-pay without wizard
        when profile_id is set with a journal
        """
        # Check if profile is set and has a journal configured
        if self.profile_id and self.profile_id.journal_id:
            return self._auto_register_payment()
        
        # Otherwise, use the default wizard behavior
        return super().action_register_payment()
    
    #new Add 
    def _auto_register_payment(self):
        """
        Automatically register payment without showing wizard
        Uses the correct Odoo 19 payment registration flow
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

            # Get payment method line
            payment_method_line = self._get_payment_method_line(journal, payment_type)

            # Create payment wizard with proper context
            payment_register = self.env['account.payment.register'].with_context(
                active_model='account.move',
                active_ids=move.ids
            ).create({
                'journal_id': journal.id,
                'payment_method_line_id': payment_method_line,
                'payment_date': fields.Date.context_today(self)
                # 'profile_id': self.profile_id.id
            })

            # Create and post the payment
            payment_register.action_create_payments()

        # Return action to refresh the view or show notification
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
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

        # Return the first available payment method line ID
        return available_payment_method_lines[0].id


