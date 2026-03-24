# # -*- coding: utf-8 -*-
# from odoo import api, fields, models, _
# from odoo.exceptions import UserError


# class AssetReturnWizard(models.TransientModel):
#     _name = 'asset.return.wizard'
#     _description = 'Asset Return Wizard'

#     asset_id = fields.Many2one(
#         'account.asset',
#         string='Asset',
#         required=True,
#     )
#     return_date = fields.Date(
#         string='Return Date',
#         required=True,
#         default=fields.Date.today,
#     )
#     condition_on_return = fields.Selection(
#         selection=[
#             ('good', 'Good'),
#             ('fair', 'Fair'),
#             ('poor', 'Poor'),
#             ('damaged', 'Damaged'),
#         ],
#         string='Condition on Return',
#         required=True,
#         default='good',
#     )
#     notes = fields.Text(string='Notes')

#     def action_return(self):
#         self.ensure_one()
#         asset = self.asset_id

#         if asset.state != 'assigned':
#             raise UserError(_(
#                 'Asset "%s" is not currently assigned and cannot be returned.'
#             ) % asset.code)

#         # ── 1. Find active assignment ─────────────────────────────────────────
#         assignment = self.env['asset.assignment'].search([
#             ('asset_id', '=', asset.id),
#             ('is_active', '=', True),
#             ('return_date', '=', False),
#         ], limit=1)

#         if not assignment:
#             raise UserError(_(
#                 'No active assignment found for asset "%s".'
#             ) % asset.code)

#         employee = assignment.employee_id

#         # ── 2. Close the assignment ───────────────────────────────────────────
#         # Use sudo to bypass write() protection (assignment is a normal model)
#         assignment.write({
#             'is_active': False,
#             'return_date': self.return_date,
#             'condition_on_return': self.condition_on_return,
#             'returned_by': self.env.uid,
#             'notes': (assignment.notes or '') + (
#                 ('\n' + self.notes) if self.notes else ''
#             ),
#         })

#         # ── 3. Update asset state ─────────────────────────────────────────────
#         asset.write({
#             'state': 'available',
#             'current_employee_id': False,
#         })

#         # ── 4. Create damage activity if needed ───────────────────────────────
#         if self.condition_on_return == 'damaged':
#             activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
#             asset.activity_schedule(
#                 activity_type_id=activity_type.id if activity_type else False,
#                 summary=_('Damaged asset returned — inspection required'),
#                 note=_(
#                     'Asset %s was returned by %s in damaged condition on %s. '
#                     'Please inspect before reassignment.'
#                 ) % (asset.code, employee.name, self.return_date),
#             )

#         # ── 5. Log history ────────────────────────────────────────────────────
#         asset._log_history(
#             event_type='return',
#             old_state='assigned',
#             new_state='available',
#             employee_id=employee.id,
#             description=_(
#                 'Asset returned by %s. Condition: %s'
#             ) % (employee.name, self.condition_on_return),
#             metadata={'condition': self.condition_on_return},
#         )

#         return {'type': 'ir.actions.act_window_close'}

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AssetReturnWizard(models.TransientModel):
    _name = 'asset.return.wizard'
    _description = 'Asset Return Wizard'

    asset_id = fields.Many2one(
        'account.asset',
        string='Asset',
        required=True,
    )
    return_date = fields.Date(
        string='Return Date',
        required=True,
        default=fields.Date.today,
    )
    condition_on_return = fields.Selection(
        selection=[
            ('good',    'Good'),
            ('fair',    'Fair'),
            ('poor',    'Poor'),
            ('damaged', 'Damaged'),
        ],
        string='Condition on Return',
        required=True,
        default='good',
    )
    notes = fields.Text(string='Notes')

    # =========================================================================
    # ACTION
    # =========================================================================

    def action_return(self):
        self.ensure_one()
        asset = self.asset_id

        # ── 1. AMS state check ────────────────────────────────────────────────
        if asset.asset_state != 'assigned':
            raise UserError(_(
                'Asset "%s" is not currently assigned and cannot be returned. '
                'Current status: %s'
            ) % (asset.code, asset.asset_state))

        # ── 2. Find the active assignment record ──────────────────────────────
        assignment = self.env['asset.assignment'].search([
            ('asset_id',    '=', asset.id),
            ('is_active',   '=', True),
            ('return_date', '=', False),
        ], limit=1)
        if not assignment:
            raise UserError(_(
                'No active assignment found for asset "%s".'
            ) % asset.code)

        employee = assignment.employee_id

        # ── 3. Close the assignment ───────────────────────────────────────────
        assignment.write({
            'is_active':          False,
            'return_date':        self.return_date,
            'condition_on_return': self.condition_on_return,
            'returned_by':        self.env.uid,
            'notes': (assignment.notes or '') + (
                ('\n' + self.notes) if self.notes else ''
            ),
        })

        # ── 4. Reset AMS asset state ──────────────────────────────────────────
        asset.write({
            'asset_state':        'available',
            'current_employee_id': False,
        })

        # ── 5. Schedule damage inspection activity if needed ──────────────────
        if self.condition_on_return == 'damaged':
            activity_type = self.env.ref(
                'mail.mail_activity_data_todo', raise_if_not_found=False
            )
            asset.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_('Damaged asset returned — inspection required'),
                note=_(
                    'Asset %s was returned by %s in damaged condition on %s. '
                    'Please inspect before reassignment.'
                ) % (asset.code, employee.name, self.return_date),
            )

        # ── 6. Log history ────────────────────────────────────────────────────
        asset._log_history(
            event_type='return',
            old_state='assigned',
            new_state='available',
            employee_id=employee.id,
            description=_(
                'Asset returned by %s. Condition: %s'
            ) % (employee.name, self.condition_on_return),
            metadata={'condition': self.condition_on_return},
        )

        return {'type': 'ir.actions.act_window_close'}