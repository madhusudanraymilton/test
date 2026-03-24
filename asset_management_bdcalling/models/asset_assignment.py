# # -*- coding: utf-8 -*-
# from odoo import api, fields, models, _
# from odoo.exceptions import ValidationError, UserError


# class AssetAssignment(models.Model):
#     _name = 'asset.assignment'
#     _description = 'Asset Assignment Record'
#     _order = 'assign_date desc'
#     _rec_name = 'asset_id'

#     asset_id = fields.Many2one(
#         'account.asset',
#         string='Asset',
#         required=True,
#         ondelete='restrict',
#         index=True,
#     )
#     employee_id = fields.Many2one(
#         'hr.employee',
#         string='Employee',
#         required=True,
#         ondelete='restrict',
#         index=True,
#     )
#     assign_date = fields.Date(
#         string='Assignment Date',
#         required=True,
#         default=fields.Date.today,
#     )
#     return_date = fields.Date(string='Return Date')
#     assigned_by = fields.Many2one(
#         'res.users',
#         string='Assigned By',
#         required=True,
#         default=lambda self: self.env.uid,
#     )
#     returned_by = fields.Many2one(
#         'res.users',
#         string='Returned By',
#         ondelete='set null',
#     )
#     condition_on_assign = fields.Selection(
#         selection=[
#             ('new', 'New'),
#             ('good', 'Good'),
#             ('fair', 'Fair'),
#             ('poor', 'Poor'),
#         ],
#         string='Condition on Assignment',
#     )
#     condition_on_return = fields.Selection(
#         selection=[
#             ('good', 'Good'),
#             ('fair', 'Fair'),
#             ('poor', 'Poor'),
#             ('damaged', 'Damaged'),
#         ],
#         string='Condition on Return',
#     )
#     notes = fields.Text(string='Notes')
#     is_active = fields.Boolean(
#         string='Currently Active',
#         default=True,
#         index=True,
#     )
#     company_id = fields.Many2one(
#         'res.company',
#         string='Company',
#         required=True,
#         default=lambda self: self.env.company,
#     )

#     # ── No _sql_constraints: Odoo does not support PostgreSQL partial unique
#     # indexes or EXCLUDE constraints via _sql_constraints.
#     # The partial unique index is created in init() below.

#     def init(self):
#         """
#         Partial unique index: only one active (non-returned) assignment per asset.
#         Cannot be expressed via _sql_constraints (no partial index support in ORM).
#         """
#         self.env.cr.execute("""
#             CREATE UNIQUE INDEX IF NOT EXISTS asset_assignment_active_unique
#             ON asset_assignment (asset_id)
#             WHERE (is_active = true AND return_date IS NULL)
#         """)

#     # ── ORM-level guard (fires before DB, gives a clean UserError) ───────────

#     @api.constrains('asset_id', 'is_active', 'return_date')
#     def _check_no_double_assignment(self):
#         for rec in self:
#             if rec.is_active and not rec.return_date:
#                 duplicate = self.search([
#                     ('asset_id', '=', rec.asset_id.id),
#                     ('is_active', '=', True),
#                     ('return_date', '=', False),
#                     ('id', '!=', rec.id),
#                 ])
#                 if duplicate:
#                     raise UserError(_(
#                         'Asset "%s" already has an active assignment. '
#                         'Return it first before creating a new one.'
#                     ) % rec.asset_id.name)

#     @api.constrains('assign_date', 'return_date')
#     def _check_dates(self):
#         for rec in self:
#             if rec.return_date and rec.assign_date and rec.return_date < rec.assign_date:
#                 raise ValidationError(_(
#                     'Return date cannot be earlier than assignment date.'
#                 ))

#     @api.constrains('assign_date', 'asset_id')
#     def _check_assign_date_vs_registration(self):
#         for rec in self:
#             if rec.asset_id.registration_date and rec.assign_date:
#                 if rec.assign_date < rec.asset_id.registration_date:
#                     raise ValidationError(_(
#                         'Assignment date cannot precede the asset registration date (%s).'
#                     ) % rec.asset_id.registration_date)

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AssetAssignment(models.Model):
    _name = 'asset.assignment'
    _description = 'Asset Assignment Record'
    _order = 'assign_date desc, id desc'
    _rec_name = 'asset_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Core relational fields ────────────────────────────────────────────────

    asset_id = fields.Many2one(
        'account.asset',
        string='Asset',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
    )

    # ── Dates ─────────────────────────────────────────────────────────────────

    assign_date = fields.Date(
        string='Assignment Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    return_date = fields.Date(
        string='Return Date',
        tracking=True,
    )

    # ── Personnel ─────────────────────────────────────────────────────────────

    assigned_by = fields.Many2one(
        'res.users',
        string='Assigned By',
        required=True,
        default=lambda self: self.env.uid,
        ondelete='restrict',
    )
    returned_by = fields.Many2one(
        'res.users',
        string='Returned By',
        ondelete='set null',
    )

    # ── Condition ─────────────────────────────────────────────────────────────

    condition_on_assign = fields.Selection(
        selection=[
            ('new',  'New'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
        ],
        string='Condition on Assignment',
        tracking=True,
    )
    condition_on_return = fields.Selection(
        selection=[
            ('good',    'Good'),
            ('fair',    'Fair'),
            ('poor',    'Poor'),
            ('damaged', 'Damaged'),
        ],
        string='Condition on Return',
        tracking=True,
    )

    # ── Status & misc ─────────────────────────────────────────────────────────

    notes = fields.Text(string='Notes')
    is_active = fields.Boolean(
        string='Currently Active',
        default=True,
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # ── Computed display helpers ──────────────────────────────────────────────

    duration_days = fields.Integer(
        string='Duration (days)',
        compute='_compute_duration_days',
        store=False,
    )

    # ── SQL / DB ──────────────────────────────────────────────────────────────

    def init(self):
        """
        Partial unique index: only one open (non-returned) assignment per asset.
        Cannot be expressed via _sql_constraints (no partial-index support in ORM).
        """
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS asset_assignment_active_unique
            ON asset_assignment (asset_id)
            WHERE (is_active = TRUE AND return_date IS NULL)
        """)

    # ── Compute ───────────────────────────────────────────────────────────────

    @api.depends('assign_date', 'return_date')
    def _compute_duration_days(self):
        today = fields.Date.today()
        for rec in self:
            end = rec.return_date or today
            if rec.assign_date and end >= rec.assign_date:
                rec.duration_days = (end - rec.assign_date).days
            else:
                rec.duration_days = 0

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains('asset_id', 'is_active', 'return_date')
    def _check_no_double_assignment(self):
        for rec in self:
            if rec.is_active and not rec.return_date:
                duplicate = self.search([
                    ('asset_id',    '=', rec.asset_id.id),
                    ('is_active',   '=', True),
                    ('return_date', '=', False),
                    ('id',          '!=', rec.id),
                ])
                if duplicate:
                    raise UserError(_(
                        'Asset "%s" already has an active assignment '
                        '(record #%s). Return it before creating a new one.'
                    ) % (rec.asset_id.name, duplicate[0].id))

    @api.constrains('assign_date', 'return_date')
    def _check_dates(self):
        for rec in self:
            if rec.return_date and rec.assign_date:
                if rec.return_date < rec.assign_date:
                    raise ValidationError(_(
                        'Return date (%s) cannot be earlier than '
                        'assignment date (%s).'
                    ) % (rec.return_date, rec.assign_date))

    @api.constrains('assign_date', 'asset_id')
    def _check_assign_date_vs_registration(self):
        for rec in self:
            reg = rec.asset_id.registration_date
            if reg and rec.assign_date and rec.assign_date < reg:
                raise ValidationError(_(
                    'Assignment date (%s) cannot be before the asset '
                    'registration date (%s).'
                ) % (rec.assign_date, reg))

    # ── Smart button action ───────────────────────────────────────────────────

    def action_open_asset(self):
        """Navigate to the related asset form."""
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'name':      _('Asset'),
            'res_model': 'account.asset',
            'res_id':    self.asset_id.id,
            'view_mode': 'form',
            'target':    'current',
        }