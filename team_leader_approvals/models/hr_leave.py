from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    team_leader_approval = fields.Selection([
        ('draft', 'To Submit'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused')
    ], string='Team Leader Status', default='draft', tracking=True, copy=False)

    team_leader_approval_date = fields.Datetime(string='Team Leader Approval Date', copy=False)
    team_leader_id = fields.Many2one(
        'hr.employee',
        string='Team Leader',
        compute='_compute_team_leader',
        store=True,
        readonly=True
    )

    @api.depends('employee_id', 'employee_id.team_leader_id')
    def _compute_team_leader(self):
        """Compute team leader based on employee's team leader"""
        for leave in self:
            if leave.employee_id and leave.employee_id.team_leader_id and leave.employee_id.team_leader_id.is_team_leader:
                leave.team_leader_id = leave.employee_id.team_leader_id
            else:
                leave.team_leader_id = False

    def action_team_leader_approve(self):
        """Action for team leader approval"""
        for leave in self:
            if leave.team_leader_approval != 'pending':
                raise UserError(_("This request is not pending team leader approval."))

            leave.team_leader_approval = 'approved'
            leave.team_leader_approval_date = fields.Datetime.now()

            # Submit to backend for further approval
            if leave.state == 'confirm':
                return leave.action_validate()

    def action_team_leader_refuse(self):
        """Action for team leader refusal"""
        for leave in self:
            if leave.team_leader_approval != 'pending':
                raise UserError(_("This request is not pending team leader approval."))

            leave.team_leader_approval = 'refused'
            leave.team_leader_approval_date = fields.Datetime.now()
            return leave.action_refuse()

    def action_confirm(self):
        """Override confirm to require team leader approval first"""
        for leave in self:
            # Check if employee has a team leader
            if leave.employee_id.team_leader_id and leave.employee_id.team_leader_id.is_team_leader:
                leave.team_leader_approval = 'pending'
                # Set to confirm state but don't auto-approve
                leave.state = 'confirm'
                # Send notification to team leader
                self._send_team_leader_notification(leave)
            else:
                # No team leader, go directly to backend
                return super(HrLeave, leave).action_confirm()
        return True

    def _send_team_leader_notification(self, leave):
        """Send notification to team leader about pending request"""
        template = self.env.ref('team_leader_approvals.email_template_team_leader_approval', raise_if_not_found=False)
        if template and leave.team_leader_id.user_id:
            template.sudo().with_context(
                employee_name=leave.employee_id.name,
                leave_type=leave.holiday_status_id.name,
                date_from=leave.request_date_from,
                date_to=leave.request_date_to
            ).send_mail(leave.id, force_send=True)

    def _check_approval_update(self, state):
        """Override to check team leader approval"""
        # Skip check for team leaders themselves
        if self.employee_id.is_team_leader:
            return super()._check_approval_update(state)

        if self.team_leader_id and self.team_leader_approval not in ['approved', 'refused']:
            raise UserError(_("Team leader approval is required before backend approval."))
        return super()._check_approval_update(state)

    def action_validate(self):
        """Override validate to check team leader approval"""
        for leave in self:
            # Skip check for team leaders themselves
            if leave.employee_id.is_team_leader:
                continue

            if leave.team_leader_id and leave.team_leader_approval != 'approved':
                raise UserError(_("Team leader approval is required before backend approval."))

        return super().action_validate()