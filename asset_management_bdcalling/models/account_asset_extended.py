# -*- coding: utf-8 -*-
"""
account.asset extension — Physical + Financial Asset Tracking
=============================================================
Odoo 19 specific patterns applied:
  - `aggregator='sum'` on Monetary fields  (group_operator removed in 19)
  - `asset_type` used to distinguish model-templates from real assets
    (account.asset.asset_type = 'model' | 'purchase' | 'sale' | 'expense')
  - `state` on account.asset = 'draft' | 'open' | 'paused' | 'close' | 'cancelled'
    (accounting lifecycle — DO NOT confuse with our asset_lifecycle_state)
  - `original_value`   → gross purchase value  (not purchase_price)
  - `value_residual`   → net book value         (native, read-only computed)
  - `depreciation_move_ids` → One2many to account.move (not asset.depreciation.line)
  - `acquisition_date` → accounting start date  (native)
  - Type annotations on field declarations follow Odoo 19 source style

Dependent models must declare:
  asset.assignment.asset_id  = Many2one('account.asset', ...)
  asset.history.asset_id     = Many2one('account.asset', ...)
"""
from __future__ import annotations

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    # =========================================================================
    # 1.  Asset Code  — auto-generated from ir.sequence on create
    # =========================================================================

    asset_code: str = fields.Char(
        string='Asset Code',
        readonly=True,
        copy=False,
        index=True,
        default='New',
        tracking=True,
    )

    # =========================================================================
    # 2.  Product & Serial linkage
    # =========================================================================

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        tracking=True,
        domain="[('is_asset', '=', True)]",
        ondelete='restrict',
    )
    
    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Serial Number',
        tracking=True,
        domain="[('id', 'in', available_lot_ids)]",
        ondelete='restrict',
    )
    serial_number = fields.Char(
        string='Serial No.',
        related='lot_id.name',
        store=True,
        readonly=True,
        index=True,
    )
    available_lot_ids = fields.Many2many(
        comodel_name='stock.lot',
        string='Available Serials',
        compute='_compute_available_lot_ids',
        readonly=True,
    )

    # =========================================================================
    # 3.  Name — auto-built from product + serial when product is set
    #     `precompute=True` so the name is set immediately on creation
    #     before any DB write (Odoo 19 pattern).
    # =========================================================================

    name = fields.Char(
        compute='_compute_name',
        store=True,
        readonly=False,
        precompute=True,
    )

    # =========================================================================
    # 4.  Physical location
    # =========================================================================

    asset_location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Asset Location',
        tracking=True,
        domain="[('usage', '=', 'internal')]",
    )

    # =========================================================================
    # 5.  Purchase date (physical delivery date, separate from acquisition_date)
    # =========================================================================

    purchase_date = fields.Date(
        string='Purchase Date',
        tracking=True,
        help=(
            'Physical purchase / delivery date. '
            'Use the native "Acquisition Date" for the accounting start date.'
        ),
    )
    registration_date = fields.Date(
        string='Registration Date',
        readonly=True,
        copy=False,
    )

    # =========================================================================
    # 6.  Assignment — current active assignee + read-only enrichment fields
    # =========================================================================

    current_assignee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Current Assignee',
        tracking=True,
        copy=False,
        ondelete='restrict',
        index=True,
        domain="[('company_id', '=', company_id)]",
    )
    assignee_department_id = fields.Many2one(
        comodel_name='hr.department',
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
    # 7.  Physical lifecycle state
    #     Fully independent from accounting state (draft/open/paused/close/cancelled)
    # =========================================================================

    asset_lifecycle_state = fields.Selection(
        selection=[
            ('draft',     'Draft'),
            ('available', 'Available'),
            ('assigned',  'Assigned'),
            ('returned',  'Returned'),
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
    # 8.  Relational history lines
    # =========================================================================

    assignment_ids = fields.One2many(
        comodel_name='asset.assignment',
        inverse_name='asset_id',
        string='Assignment History',
        readonly=True,
        copy=False,
    )
    history_ids = fields.One2many(
        comodel_name='asset.history',
        inverse_name='asset_id',
        string='Lifecycle History',
        readonly=True,
        copy=False,
    )

    # =========================================================================
    # 9.  Notes
    # =========================================================================

    asset_notes = fields.Text(string='Asset Notes')

    # =========================================================================
    # Compute Methods
    # =========================================================================

    @api.depends('product_id', 'lot_id')
    def _compute_name(self) -> None:
        """
        Drive name from product + serial for physical assets.
        For accounting model-templates (asset_type='model') or assets without
        a product the existing stored name is preserved — computed field
        fallback to _origin.name avoids blanking names on full recompute.
        """
        for rec in self:
            if rec.product_id and rec.lot_id:
                rec.name = f'{rec.product_id.name} [{rec.lot_id.name}]'
            elif rec.product_id:
                rec.name = rec.product_id.name
            else:
                rec.name = rec._origin.name or rec.name or _('New Asset')

    @api.depends('product_id')
    def _compute_available_lot_ids(self) -> None:
        """
        Lots not yet locked by a confirmed (non-draft lifecycle) asset,
        excluding this record itself so edit mode doesn't self-exclude.
        Searches account.asset directly — we ARE account.asset now.
        """
        locked_lots = self.env['account.asset'].search([
            ('lot_id', '!=', False),
            ('asset_lifecycle_state', '!=', 'draft'),
            ('id', 'not in', self.ids),
        ]).lot_id  # recordset attribute access = mapped('lot_id')

        for rec in self:
            domain = (
                [('product_id', '=', rec.product_id.id)]
                if rec.product_id else []
            )
            rec.available_lot_ids = (
                self.env['stock.lot'].search(domain) - locked_lots
            )

    # =========================================================================
    # ORM Overrides
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> 'AccountAsset':
        """
        Auto-generate asset_code for physical assets only.
        Template/model records (asset_type == 'model') must NOT consume a
        sequence number — they are accounting category blueprints, not assets.
        """
        seq = self.env['ir.sequence']
        for vals in vals_list:
            # Skip model/template records; they have asset_type='model'
            if (
                not vals.get('asset_code')
                and vals.get('asset_type', 'purchase') != 'model'
            ):
                vals['asset_code'] = (
                    seq.next_by_code('account.asset.code') or 'New'
                )
        return super().create(vals_list)

    def write(self, vals: dict) -> bool:
        """
        Intercept current_assignee_id changes to:
          1. Close the departing employee's open asset.assignment (set is_active=False).
          2. Create a new asset.assignment for the incoming employee.
          3. Append an asset.history record for the transition.
          4. Auto-sync asset_lifecycle_state unless the caller already sets it.
        All other writes pass straight through to super().
        """
        if 'current_assignee_id' not in vals:
            return super().write(vals)

        today = fields.Date.today()
        new_employee_id: int | bool = vals.get('current_assignee_id')

        for asset in self:
            old_employee = asset.current_assignee_id

            # ── Close departing employee's open assignment ──────────────────
            if old_employee and old_employee.id != new_employee_id:
                open_assignment = self.env['asset.assignment'].search([
                    ('asset_id',    '=', asset.id),
                    ('employee_id', '=', old_employee.id),
                    ('is_active',   '=', True),
                ], limit=1)

                if open_assignment:
                    open_assignment.write({
                        'is_active':   False,
                        'return_date': today,
                    })
                else:
                    # Defensive tombstone — should not normally occur
                    self.env['asset.assignment'].create({
                        'asset_id':    asset.id,
                        'employee_id': old_employee.id,
                        'assign_date': today,
                        'return_date': today,
                        'is_active':   False,
                        'notes':       _('Auto-closed on reassignment.'),
                    })

            # ── Open new assignment for incoming employee ───────────────────
            if new_employee_id:
                self.env['asset.assignment'].create({
                    'asset_id':    asset.id,
                    'employee_id': new_employee_id,
                    'assign_date': today,
                    'is_active':   True,
                })
                incoming_emp = self.env['hr.employee'].browse(new_employee_id)
                asset._log_history(
                    event_type='assign',
                    old_state=asset.asset_lifecycle_state,
                    new_state='assigned',
                    employee_id=new_employee_id,
                    description=_('Assigned to %(name)s', name=incoming_emp.name),
                )

        # ── Auto-sync lifecycle state unless caller already overrides it ────
        if 'asset_lifecycle_state' not in vals:
            if new_employee_id:
                vals['asset_lifecycle_state'] = 'assigned'
            # 'available' is set explicitly only through action_return()

        return super().write(vals)

    # =========================================================================
    # Action Button Methods
    # =========================================================================

    def action_register(self):
        """
        Draft → Available.
        Opens the register wizard which handles the stock move and stamps
        registration_date. Supports single-record call (ensure_one guard).
        """
        self.ensure_one()
        if self.asset_lifecycle_state != 'draft':
            raise UserError(_(
                'Only assets in "Draft" status can be registered.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Asset'),
            'res_model': 'asset.register.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id':       self.id,
                'default_lot_id':         self.lot_id.id,
                'default_original_value': self.original_value,
            },
        }

    def action_unregister(self):
        """
        Available → Draft.
        Opens the unregister wizard which reverses the stock move and clears
        the registration_date.
        """
        self.ensure_one()
        if self.asset_lifecycle_state != 'available':
            raise UserError(_(
                'Only "Available" assets can be unregistered.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Unregister Asset'),
            'res_model': 'asset.unregister.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_asset_id': self.id},
        }

    def action_assign(self):
        """
        Available → Assigned.
        Opens the assign wizard to pick employee, notes, etc.
        The wizard's confirm button calls write({'current_assignee_id': emp_id})
        which triggers the ORM override above.
        """
        self.ensure_one()
        if self.asset_lifecycle_state != 'available':
            raise UserError(_(
                'Only "Available" assets can be assigned.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Asset'),
            'res_model': 'asset.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_asset_id': self.id},
        }

    def action_return(self):
        """
        Assigned → Available.
        Opens the return wizard to capture condition, location, and notes.
        The write() override closes the active asset.assignment automatically.
        """
        self.ensure_one()
        if self.asset_lifecycle_state != 'assigned':
            raise UserError(_(
                'Only "Assigned" assets can be returned.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Asset'),
            'res_model': 'asset.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_asset_id': self.id},
        }

    def action_scrap(self):
        """
        Available | Assigned → Scrapped.
        Multi-record safe — no ensure_one().
        """
        invalid = self.filtered(
            lambda a: a.asset_lifecycle_state not in ('available', 'assigned')
        )
        if invalid:
            raise UserError(_(
                'Only available or assigned assets can be scrapped. '
                'Skipping:\n%(names)s',
                names=', '.join(invalid.mapped('name')),
            ))
        for asset in self:
            old_state = asset.asset_lifecycle_state
            asset.write({
                'asset_lifecycle_state': 'scrapped',
                'current_assignee_id':   False,
            })
            asset._log_history(
                event_type='scrap',
                old_state=old_state,
                new_state='scrapped',
                description=_(
                    'Asset scrapped by %(user)s',
                    user=self.env.user.name,
                ),
            )
        return True

    def action_dispose(self):
        """
        Available | Assigned → Disposed.
        Multi-record safe — no ensure_one().
        """
        invalid = self.filtered(
            lambda a: a.asset_lifecycle_state not in ('available', 'assigned')
        )
        if invalid:
            raise UserError(_(
                'Only available or assigned assets can be disposed. '
                'Skipping:\n%(names)s',
                names=', '.join(invalid.mapped('name')),
            ))
        for asset in self:
            old_state = asset.asset_lifecycle_state
            asset.write({
                'asset_lifecycle_state': 'disposed',
                'current_assignee_id':   False,
            })
            asset._log_history(
                event_type='dispose',
                old_state=old_state,
                new_state='disposed',
                description=_(
                    'Asset disposed by %(user)s',
                    user=self.env.user.name,
                ),
            )
        return True

    # =========================================================================
    # History Logging
    # =========================================================================

    def _log_history(
        self,
        event_type: str,
        old_state: str | None = None,
        new_state: str | None = None,
        employee_id: int | None = None,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """
        Append an immutable lifecycle record to asset.history.
        Always called on a single record; ensure_one() guard is included.
        sudo() so the caller's ACL does not block the history write.
        """
        self.ensure_one()
        self.env['asset.history'].sudo().create({
            'asset_id':    self.id,
            'event_type':  event_type,
            'event_date':  fields.Datetime.now(),
            'old_state':   old_state or self.asset_lifecycle_state,
            'new_state':   new_state or self.asset_lifecycle_state,
            'employee_id': employee_id,
            'user_id':     self.env.uid,
            'description': description or _(
                'State changed: %(old)s → %(new)s',
                old=old_state,
                new=new_state,
            ),
            'metadata':    metadata or {},
            'company_id':  self.company_id.id,
        })

    # =========================================================================
    # Scheduled Action (Cron)
    # =========================================================================

    @api.model
    def _cron_check_archived_employee_assets(self) -> None:
        """
        Daily cron: detect assets assigned to archived employees, schedule a
        To-Do activity, and optionally auto-return them when the company flag
        `auto_return_on_employee_archive` is True.
        """
        archived_employees = self.env['hr.employee'].with_context(
            active_test=False
        ).search([('active', '=', False)])

        if not archived_employees:
            return

        assets = self.search([
            ('current_assignee_id',   'in', archived_employees.ids),
            ('asset_lifecycle_state', '=',  'assigned'),
        ])
        if not assets:
            return

        activity_type = self.env.ref(
            'mail.mail_activity_data_todo', raise_if_not_found=False
        )

        for asset in assets:
            employee = asset.current_assignee_id
            _logger.warning(
                'AMS: Asset %s still assigned to archived employee %s',
                asset.asset_code,
                employee.name,
            )
            asset.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_('Asset return required — employee archived'),
                note=_(
                    'Employee %(emp)s has been archived but still holds '
                    'asset %(code)s (%(name)s). Please arrange return.',
                    emp=employee.name,
                    code=asset.asset_code,
                    name=asset.name,
                ),
            )

            if self.env.company.auto_return_on_employee_archive:
                open_assignment = self.env['asset.assignment'].search([
                    ('asset_id',  '=', asset.id),
                    ('is_active', '=', True),
                ], limit=1)
                if open_assignment:
                    open_assignment.write({
                        'is_active':           False,
                        'return_date':         fields.Date.today(),
                        'condition_on_return': 'fair',
                    })
                # write() override handles closing the assignment and
                # appending history automatically — no double-log needed.
                asset.write({
                    'asset_lifecycle_state': 'available',
                    'current_assignee_id':   False,
                })
                asset._log_history(
                    event_type='return',
                    old_state='assigned',
                    new_state='available',
                    employee_id=employee.id,
                    description=_('Auto-returned on employee archive by cron'),
                )

    # =========================================================================
    # Dashboard RPC
    # =========================================================================

    @api.model
    def get_dashboard_data(self) -> dict:
        """
        Called by the OWL dashboard component via rpc.
        Filters out accounting model-templates (asset_type == 'model').
        Uses Odoo 18/19 native field names:
          - original_value   (gross purchase price)
          - value_residual   (net book value, computed by Odoo accounting)
          - depreciation_move_ids → account.move records
        """
        domain_base = [
            ('company_id',  'in', self.env.companies.ids),
            ('asset_type',  '!=', 'model'),   # exclude accounting templates
        ]
        assets = self.search(domain_base)

        available         = assets.filtered(
            lambda a: a.asset_lifecycle_state == 'available'
        )
        assigned          = assets.filtered(
            lambda a: a.asset_lifecycle_state == 'assigned'
        )
        scrapped_disposed = assets.filtered(
            lambda a: a.asset_lifecycle_state in ('scrapped', 'disposed')
        )

        # Pending depreciation = draft account.move lines linked to these assets
        # with an accounting date ≤ today (Odoo 18/19 uses account.move, not
        # the legacy asset.depreciation.line model which was removed in v16+).
        pending_dep = self.env['account.move'].search_count([
            ('asset_id', 'in', assets.ids),
            ('state',    '=',  'draft'),
            ('date',     '<=', fields.Date.today()),
        ])

        # Category breakdown — model_id is the template asset for the record
        category_data: dict[str, int] = {}
        for asset in assets:
            cat = (
                asset.model_id.name
                if asset.model_id
                else _('Uncategorised')
            )
            category_data[cat] = category_data.get(cat, 0) + 1

        return {
            'total':                len(assets),
            'available':            len(available),
            'assigned':             len(assigned),
            'scrapped_disposed':    len(scrapped_disposed),
            'total_value':          sum(assets.mapped('original_value')),
            'net_book_value':       sum(assets.mapped('value_residual')),
            'pending_depreciation': pending_dep,
            'by_category': [
                {'category': k, 'count': v}
                for k, v in sorted(
                    category_data.items(), key=lambda x: -x[1]
                )
            ],
        }