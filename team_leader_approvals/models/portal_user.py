from odoo import models, fields, api, _
from odoo.exceptions import AccessError


class PortalUser(models.Model):
    _inherit = 'res.users'

    team_leader_for_ids = fields.One2many(
        'hr.employee',
        'team_leader_id',
        string='Team Members',
        compute='_compute_team_leader_for_ids'
    )

    def _compute_team_leader_for_ids(self):
        """Compute team members for portal user"""
        for user in self:
            if user.has_group('base.group_portal'):
                # Find employee record for this user
                employee = self.env['hr.employee'].search([
                    ('user_id', '=', user.id),
                    ('is_team_leader', '=', True)
                ], limit=1)
                user.team_leader_for_ids = employee.team_member_ids if employee else False
            else:
                user.team_leader_for_ids = False

    def check_team_leader_access(self):
        """Check if user is a team leader"""
        self.ensure_one()
        employee = self.env['hr.employee'].search([
            ('user_id', '=', self.id),
            ('is_team_leader', '=', True)
        ], limit=1)
        return bool(employee)