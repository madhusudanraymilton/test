from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_team_leader = fields.Boolean(string='Is Team Leader', default=False)
    team_leader_id = fields.Many2one(
        'hr.employee',
        string='Team Leader',
        domain="[('is_team_leader', '=', True), ('id', '!=', id)]",
        help="The team leader of this employee"
    )
    team_member_ids = fields.One2many(
        'hr.employee',
        'team_leader_id',
        string='Team Members',
        domain="[('is_team_leader', '=', False)]"
    )

    @api.constrains('team_leader_id')
    def _check_team_leader_hierarchy(self):
        """Prevent circular hierarchy"""
        for employee in self:
            if employee.team_leader_id:
                # Check if creating a loop
                leaders = set()
                current = employee.team_leader_id
                while current:
                    if current.id in leaders:
                        raise ValidationError(_("Circular hierarchy detected. Cannot set this team leader."))
                    if current == employee:
                        raise ValidationError(_("An employee cannot be their own team leader."))
                    leaders.add(current.id)
                    current = current.team_leader_id

    @api.onchange('is_team_leader')
    def _onchange_is_team_leader(self):
        """Reset team leader when becoming a team leader"""
        if self.is_team_leader:
            self.team_leader_id = False

    def action_create_portal_user(self):
        """Create portal user for team leader"""
        self.ensure_one()
        if not self.is_team_leader:
            raise UserError(_("Only team leaders can have portal access."))

        if not self.user_id:
            raise UserError(_("Employee must have a linked user first."))

        # Add portal access
        portal_group = self.env.ref('base.group_portal')
        if portal_group not in self.user_id.groups_id:
            self.user_id.groups_id = [(4, portal_group.id)]
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Portal access granted to team leader.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Info'),
                    'message': _('User already has portal access.'),
                    'type': 'info',
                    'sticky': False,
                }
            }