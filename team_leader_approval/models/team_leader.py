from odoo import api, fields, models, exceptions


class HrLeaveInherit(models.Model):
    _inherit = 'hr.leave'

    team_leader_approved = fields.Boolean(
        string='Team Leader Approved',
        default=False,
        tracking=True,
    )

    team_leader_approval_date = fields.Datetime(
        string='Team Leader Approval Date',
        readonly=True,
    )

    @api.model
    def create(self, vals):
        """Override create to set initial state for team leader approval"""
        leave = super(HrLeaveInherit, self).create(vals)

        # If employee has a team leader (parent_id), set state to team_leader_approval
        if leave.employee_id.parent_id:
            leave.state = 'team_leader_approval'

        return leave

    def write(self, vals):
        """Override write to track team leader approval"""
        if vals.get('team_leader_approved'):
            vals['team_leader_approval_date'] = fields.Datetime.now()

        return super(HrLeaveInherit, self).write(vals)

    def action_approve(self):
        """Override approval to check team leader approval first"""
        for leave in self:
            if leave.employee_id.parent_id and not leave.team_leader_approved:
                raise exceptions.UserError(
                    'This leave request must be approved by the team leader first.'
                )
        return super(HrLeaveInherit, self).action_approve()


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_team_leader = fields.Boolean(
        string='Is Team Leader',
        compute='_compute_is_team_leader',
        store=True,
    )

    @api.depends('child_ids')
    def _compute_is_team_leader(self):
        """Compute if employee is a team leader"""
        for employee in self:
            employee.is_team_leader = bool(employee.child_ids)