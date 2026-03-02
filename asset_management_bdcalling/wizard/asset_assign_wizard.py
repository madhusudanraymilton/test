# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AssetAssignWizard(models.TransientModel):
    _name = 'asset.assign.wizard'
    _description = 'Asset Assignment Wizard'

    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )
    assign_date = fields.Date(
        string='Assignment Date',
        required=True,
        default=fields.Date.today,
    )
    condition_on_assign = fields.Selection(
        selection=[
            ('new', 'New'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
        ],
        string='Asset Condition',
        default='good',
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )

    @api.constrains('assign_date')
    def _check_assign_date(self):
        for rec in self:
            if not self.env.company.asset_assign_date_future_allowed:
                if rec.assign_date and rec.assign_date > fields.Date.today():
                    raise UserError(_(
                        'Future assignment dates are not allowed. '
                        'Enable this in Configuration > Settings if needed.'
                    ))

    def action_assign(self):
        self.ensure_one()

        # ── 1. Lock asset row for concurrent safety ───────────────────────────
        self.env.cr.execute(
            'SELECT id FROM asset_asset WHERE id = %s FOR UPDATE NOWAIT',
            (self.asset_id.id,)
        )

        asset = self.asset_id

        # ── 2. Validate state ─────────────────────────────────────────────────
        if asset.state != 'available':
            raise UserError(_(
                'Asset "%s" must be in "Available" state to assign. Current: %s'
            ) % (asset.code, asset.state))

        # ── 3. Validate employee is active ────────────────────────────────────
        if not self.employee_id.active:
            raise UserError(_(
                'Employee "%s" is archived and cannot be assigned an asset.'
            ) % self.employee_id.name)

        # ── 4. Create assignment record ───────────────────────────────────────
        self.env['asset.assignment'].create({
            'asset_id': asset.id,
            'employee_id': self.employee_id.id,
            'assign_date': self.assign_date,
            'assigned_by': self.env.uid,
            'condition_on_assign': self.condition_on_assign,
            'notes': self.notes,
            'is_active': True,
            'company_id': asset.company_id.id,
        })

        # ── 5. Update asset state ─────────────────────────────────────────────
        asset.write({
            'state': 'assigned',
            'current_employee_id': self.employee_id.id,
        })

        # ── 6. Log history ────────────────────────────────────────────────────
        asset._log_history(
            event_type='assign',
            old_state='available',
            new_state='assigned',
            employee_id=self.employee_id.id,
            description=_(
                'Asset assigned to %s by %s'
            ) % (self.employee_id.name, self.env.user.name),
        )

        return {'type': 'ir.actions.act_window_close'}
