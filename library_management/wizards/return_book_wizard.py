# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReturnBookWizard(models.TransientModel):
    _name = 'return.book.wizard'
    _description = 'Return Book Wizard'

    borrowing_ids = fields.Many2many(
        comodel_name='library.borrowing',
        string='Borrowings to Return',
        required=True
    )
    return_date = fields.Date(
        string='Return Date',
        required=True,
        default=fields.Date.today
    )
    create_fines = fields.Boolean(
        string='Create Fines for Overdue Books',
        default=True
    )
    notes = fields.Text(
        string='Notes'
    )
    borrowing_line_ids = fields.One2many(
        comodel_name='return.book.wizard.line',
        inverse_name='wizard_id',
        string='Borrowing Lines'
    )
    total_fines = fields.Float(
        string='Total Fines',
        compute='_compute_total_fines'
    )

    @api.model
    def default_get(self, fields_list):
        """Set default borrowings from context"""
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])

        if active_ids:
            borrowings = self.env['library.borrowing'].browse(active_ids)
            valid_borrowings = borrowings.filtered(lambda b: b.status == 'borrowed')

            if not valid_borrowings:
                raise UserError(_('Please select borrowed books to return.'))

            res['borrowing_ids'] = [(6, 0, valid_borrowings.ids)]

            # Create lines
            lines = []
            for borrowing in valid_borrowings:
                days_overdue = 0
                if self.env.context.get('return_date', fields.Date.today()) > borrowing.due_date:
                    days_overdue = (self.env.context.get('return_date', fields.Date.today()) - borrowing.due_date).days

                fine_per_day = float(self.env['ir.config_parameter'].sudo().get_param(
                    'library.fine_per_day', default=5.0
                ))
                fine_amount = days_overdue * fine_per_day

                lines.append((0, 0, {
                    'borrowing_id': borrowing.id,
                    'days_overdue': days_overdue,
                    'fine_amount': fine_amount,
                }))

            res['borrowing_line_ids'] = lines

        return res

    @api.depends('borrowing_line_ids.fine_amount')
    def _compute_total_fines(self):
        """Compute total fines"""
        for wizard in self:
            wizard.total_fines = sum(wizard.borrowing_line_ids.mapped('fine_amount'))

    def action_return_books(self):
        """Process bulk book returns"""
        self.ensure_one()

        for borrowing in self.borrowing_ids:
            if borrowing.status != 'borrowed':
                continue

            borrowing.return_date = self.return_date
            borrowing.status = 'returned'

            if borrowing.notes:
                borrowing.notes = f"{borrowing.notes}\n{self.notes or ''}"
            else:
                borrowing.notes = self.notes

            # Create fine if overdue and create_fines is True
            line = self.borrowing_line_ids.filtered(lambda l: l.borrowing_id == borrowing)
            if self.create_fines and line and line.days_overdue > 0 and line.fine_amount > 0:
                fine = self.env['library.fine'].create({
                    'borrowing_id': borrowing.id,
                    'member_id': borrowing.member_id.id,
                    'fine_amount': line.fine_amount,
                    'fine_reason': _('Book returned %d days late') % line.days_overdue,
                    'payment_status': 'unpaid',
                })
                borrowing.fine_id = fine.id

                # Send fine notification
                template = self.env.ref('library_management.email_template_fine_notification', raise_if_not_found=False)
                if template:
                    template.send_mail(fine.id, force_send=False)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('%d book(s) returned successfully.') % len(self.borrowing_ids),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class ReturnBookWizardLine(models.TransientModel):
    _name = 'return.book.wizard.line'
    _description = 'Return Book Wizard Line'

    wizard_id = fields.Many2one(
        comodel_name='return.book.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    borrowing_id = fields.Many2one(
        comodel_name='library.borrowing',
        string='Borrowing',
        required=True
    )
    member_id = fields.Many2one(
        related='borrowing_id.member_id',
        string='Member',
        readonly=True
    )
    book_id = fields.Many2one(
        related='borrowing_id.book_id',
        string='Book',
        readonly=True
    )
    due_date = fields.Date(
        related='borrowing_id.due_date',
        string='Due Date',
        readonly=True
    )
    days_overdue = fields.Integer(
        string='Days Overdue',
        readonly=True
    )
    fine_amount = fields.Float(
        string='Fine Amount',
        readonly=True,
        digits='Product Price'
    )