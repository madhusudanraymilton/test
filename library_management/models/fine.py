# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LibraryFine(models.Model):
    _name = 'library.fine'
    _description = 'Library Fine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'created_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    borrowing_id = fields.Many2one(
        comodel_name='library.borrowing',
        string='Borrowing',
        required=True,
        tracking=True,
        ondelete='restrict',
        index=True
    )
    member_id = fields.Many2one(
        comodel_name='library.member',
        string='Member',
        required=True,
        tracking=True,
        ondelete='restrict',
        index=True
    )
    book_id = fields.Many2one(
        related='borrowing_id.book_id',
        string='Book',
        readonly=True,
        store=True
    )
    fine_amount = fields.Float(
        string='Fine Amount',
        required=True,
        tracking=True,
        digits='Product Price'
    )
    fine_reason = fields.Text(
        string='Reason',
        required=True,
        tracking=True
    )
    payment_status = fields.Selection(
        selection=[
            ('unpaid', 'Unpaid'),
            ('paid', 'Paid'),
        ],
        string='Payment Status',
        default='unpaid',
        required=True,
        tracking=True,
        index=True
    )
    payment_date = fields.Date(
        string='Payment Date',
        tracking=True,
        readonly=True
    )
    created_date = fields.Date(
        string='Created Date',
        default=fields.Date.today,
        required=True,
        readonly=True,
        index=True
    )
    notes = fields.Text(
        string='Notes'
    )
    color = fields.Integer(
        string='Color Index',
        compute='_compute_color'
    )

    @api.model
    def create(self, vals):
        """Override create to generate sequence"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('library.fine') or _('New')
        return super().create(vals)

    def _compute_color(self):
        """Compute color for kanban view"""
        for fine in self:
            if fine.payment_status == 'paid':
                fine.color = 10  # Green
            else:
                fine.color = 1  # Red

    @api.constrains('fine_amount')
    def _check_fine_amount(self):
        """Validate fine amount is positive"""
        for fine in self:
            if fine.fine_amount <= 0:
                raise ValidationError(_('Fine amount must be greater than zero.'))

    def action_mark_as_paid(self):
        """Mark fine as paid"""
        for fine in self:
            if fine.payment_status == 'paid':
                raise ValidationError(_('This fine is already marked as paid.'))

            fine.write({
                'payment_status': 'paid',
                'payment_date': fields.Date.today()
            })

            # Send payment confirmation email
            template = self.env.ref('library_management.email_template_fine_payment_confirmation',
                                    raise_if_not_found=False)
            if template:
                template.send_mail(fine.id, force_send=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Fine marked as paid successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_send_payment_reminder(self):
        """Send payment reminder to member"""
        self.ensure_one()
        template = self.env.ref('library_management.email_template_fine_notification', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Payment reminder sent to %s') % self.member_id.name,
                'type': 'success',
                'sticky': False,
            }
        }