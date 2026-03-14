# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountAssetExtended(models.Model):
    _inherit = 'account.asset'


    # =========================================================================
    # 1. Asset Code  (auto-generated from ir.sequence on create)
    # =========================================================================

    asset_code = fields.Char(
        string='Asset Code',
        readonly=True,
        copy=False,
        index=True,
        default='New',
        tracking=True,
    )

    # =========================================================================
    # 2. Asset Details  –  product & serial / lot linkage
    # =========================================================================

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        domain=[('type', 'in', ['product', 'consu'])],
        tracking=True,
        ondelete='restrict',
    )

    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Serial / Lot',
        domain="[('product_id', '=', product_id)]",
        tracking=True,
        ondelete='restrict',
    )

    # =========================================================================
    # 3. Assignment  –  current active assignee
    # =========================================================================

    current_assignee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Current Assignee',
        tracking=True,
        copy=False,
        ondelete='restrict',
        index=True,
    )

    # Convenient related read-only fields to enrich the Assignment page
    assignee_deparmtment_id = fields.Many2one(
        comodel_nae='hr.department',
        related='current_assignee_id.department_id',
        string='Department',
        readonly=True,
    )

    assignee_job_id = fields.Many2one(
        comodel_name='hr.job',
        related='current_assignee_id.job_id',
        string='Job Position',
        readonly=True,
    )

    assignee_mobile_phone = fields.Char(
        related='current_assignee_id.mobile_phone',
        string='Mobile',
        readonly=True,
    )

    # =========================================================================
    # 4. Lifecycle History  (One2many back-relation)
    # =========================================================================

    assignment_ids = fields.One2many(
        comodel_name='asset.assignment',
        inverse_name='asset_id',
        string='Assignment History',
        readonly=True,
        copy=False,
    )

    # =========================================================================
    # 5. Custom Lifecycle State  (independent from Odoo's accounting state)
    # =========================================================================

    asset_lifecycle_state = fields.Selection(
        selection=[
            ('draft',     'Draft'),
            ('available', 'Available'),
            ('assigned',  'Assigned'),
            ('scrapped',  'Scrapped'),
            ('disposed',  'Disposed'),
        ],
        string='Asset Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )

    # =========================================================================
    # ORM Overrides
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Assign next sequence value as asset_code on record creation."""
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('asset_code') or vals['asset_code'] == 'New':
                vals['asset_code'] = seq.next_by_code('asset.code') or 'New'
        records = super().create(vals_list)

        # Log initial assignment history if assignee already set on creation
        today = fields.Date.today()
        for record in records:
            if record.current_assignee_id:
                self.env['asset.assignment.history'].create({
                    'asset_id': record.id,
                    'employee_id': record.current_assignee_id.id,
                    'assign_date': today,
                })
        return records

    def write(self, vals):
        """
        Intercept changes to current_assignee_id to:
          1. Close the open assignment history of the departing employee.
          2. Open a new history record for the incoming employee.
          3. Auto-transition asset_lifecycle_state to 'assigned' / 'available'.
        """
        if 'current_assignee_id' not in vals:
            return super().write(vals)

        today = fields.Date.today()
        new_employee_id = vals.get('current_assignee_id')  # int or False/None

        for asset in self:
            old_employee = asset.current_assignee_id

            # ------------------------------------------------------------------
            # Close the active assignment of the departing employee
            # ------------------------------------------------------------------
            if old_employee and old_employee.id != new_employee_id:
                open_hist = self.env['asset.assignment.history'].search([
                    ('asset_id',    '=', asset.id),
                    ('employee_id', '=', old_employee.id),
                    ('return_date', '=', False),
                ], limit=1)

                if open_hist:
                    open_hist.return_date = today
                else:
                    # Defensive: create a "returned" record when no open row found
                    self.env['asset.assignment.history'].create({
                        'asset_id':    asset.id,
                        'employee_id': old_employee.id,
                        'assign_date': today,
                        'return_date': today,
                        'notes': _('Auto-closed on reassignment.'),
                    })

            # ------------------------------------------------------------------
            # Open a new assignment for the incoming employee
            # ------------------------------------------------------------------
            if new_employee_id:
                self.env['asset.assignment.history'].create({
                    'asset_id':    asset.id,
                    'employee_id': new_employee_id,
                    'assign_date': today,
                })

        # Auto-sync lifecycle state (only when not explicitly overridden in vals)
        if 'asset_lifecycle_state' not in vals:
            if new_employee_id:
                vals['asset_lifecycle_state'] = 'assigned'
            # Don't auto-set 'available' here; that belongs to action_return_asset

        return super().write(vals)

    # =========================================================================
    # 6. Header Button Action Methods
    # =========================================================================

    def action_register(self):
        """
        Draft → Available
        Formally registers the asset so it becomes ready for assignment.
        """
        invalid = self.filtered(lambda a: a.asset_lifecycle_state != 'draft')
        if invalid:
            raise UserError(_(
                "The following assets are not in 'Draft' state and cannot be "
                "registered:\n%(names)s",
                names=', '.join(invalid.mapped('name')),
            ))
        self.write({'asset_lifecycle_state': 'available'})

    def action_unregister(self):
        """
        Available → Draft
        Rolls the asset back to an unregistered/draft state.
        """
        invalid = self.filtered(lambda a: a.asset_lifecycle_state != 'available')
        if invalid:
            raise UserError(_(
                "Only 'Available' assets can be unregistered. Skipping:\n%(names)s",
                names=', '.join(invalid.mapped('name')),
            ))
        self.write({'asset_lifecycle_state': 'draft'})

    def action_return_asset(self):
        """
        Assigned → Available
        Returns the asset from its current assignee, clears the assignee, and
        closes the open assignment history record.
        """
        invalid = self.filtered(lambda a: a.asset_lifecycle_state != 'assigned')
        if invalid:
            raise UserError(_(
                "Only 'Assigned' assets can be returned. Skipping:\n%(names)s",
                names=', '.join(invalid.mapped('name')),
            ))
        # write() override handles closing the history record automatically
        self.write({
            'current_assignee_id': False,
            'asset_lifecycle_state': 'available',
        })

    def action_scrap(self):
        """
        Any → Scrapped
        Marks the asset as physically scrapped / written off.
        """
        already_done = self.filtered(
            lambda a: a.asset_lifecycle_state in ('scrapped', 'disposed')
        )
        if already_done:
            raise UserError(_(
                "The following assets are already scrapped or disposed:\n%(names)s",
                names=', '.join(already_done.mapped('name')),
            ))
        self.write({'asset_lifecycle_state': 'scrapped'})

    def action_dispose(self):
        """
        Any → Disposed
        Marks the asset as permanently disposed / sold.
        """
        already_done = self.filtered(lambda a: a.asset_lifecycle_state == 'disposed')
        if already_done:
            raise UserError(_(
                "The following assets are already disposed:\n%(names)s",
                names=', '.join(already_done.mapped('name')),
            ))
        self.write({'asset_lifecycle_state': 'disposed'})

    
