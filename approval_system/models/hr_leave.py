# ============================================================
# FILE: models/hr_leave.py
# ============================================================
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    # Custom validation type for three-layer approval
    validation_type = fields.Selection(
        selection_add=[('three_layer', 'Three Layer (Manager + HR/Admin)')],
        ondelete={'three_layer': 'set default'}
    )

    # Track approvers
    team_manager_id = fields.Many2one(
        'hr.employee',
        string='Team Manager',
        readonly=True,
        tracking=True,
        help='First layer approver (Team Manager)'
    )
    second_approver_type = fields.Selection([
        ('hr', 'HR Manager'),
        ('admin', 'Administration Manager')
    ], string='Second Approver Type', readonly=True, tracking=True)

    hr_or_admin_approver_id = fields.Many2one(
        'hr.employee',
        string='HR/Admin Approver',
        readonly=True,
        tracking=True,
        help='Second layer approver (HR or Admin Manager)'
    )

    # Override computed fields for approval access
    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        """Check if current user can give first approval (Team Manager)"""
        for leave in self:
            # Default behavior
            if leave.validation_type != 'three_layer':
                super(HrLeave, leave)._compute_can_approve()
                continue

            # Three-layer logic
            if leave.state == 'confirm':
                # Only team manager can approve at this stage
                is_team_manager = leave.employee_id.leave_manager_id == self.env.user
                leave.can_approve = is_team_manager or self.env.user.has_group('hr_holidays.group_hr_holidays_manager')
            else:
                leave.can_approve = False

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_validate(self):
        """Check if current user can give second approval (HR/Admin)"""
        for leave in self:
            # Default behavior
            if leave.validation_type != 'three_layer':
                super(HrLeave, leave)._compute_can_validate()
                continue

            # Three-layer logic
            if leave.state == 'validate1':
                # HR Manager or Admin Manager can validate
                is_hr_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
                is_admin_manager = self.env.user.has_group('three_layer_timeoff_approval.group_timeoff_administrator')
                leave.can_validate = is_hr_manager or is_admin_manager
            else:
                leave.can_validate = False

    def action_approve(self, check_state=True):
        """
        Override to handle three-layer approval
        Layer 1: Team Manager approval (confirm -> validate1)
        """
        three_layer_leaves = self.filtered(lambda l: l.validation_type == 'three_layer')
        other_leaves = self - three_layer_leaves

        # Handle standard leaves with default logic
        if other_leaves:
            super(HrLeave, other_leaves).action_approve(check_state=check_state)

        # Handle three-layer approval leaves
        if three_layer_leaves:
            current_employee = self.env.user.employee_id

            for leave in three_layer_leaves:
                if leave.state != 'confirm':
                    raise UserError(_('Time off must be in "To Approve" state for team manager approval.'))

                # Check if user is team manager
                is_team_manager = leave.employee_id.leave_manager_id == self.env.user
                is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')

                if not is_team_manager and not is_manager:
                    raise UserError(_(
                        'You cannot approve this time off request. '
                        'You must be the Time Off Manager of %s.'
                    ) % leave.employee_id.name)

                # First layer approval
                leave.write({
                    'state': 'validate1',
                    'team_manager_id': current_employee.id,
                })

                leave.message_post(
                    body=_('First Approval (Team Manager): %s') % current_employee.name,
                    subtype_xmlid='mail.mt_comment'
                )

            if not self.env.context.get('leave_fast_create'):
                three_layer_leaves.activity_update()

        return True

    def action_validate(self):
        """
        Override to handle three-layer approval
        Layer 2: HR Manager OR Admin Manager approval (validate1 -> validate)
        """
        three_layer_leaves = self.filtered(lambda l: l.validation_type == 'three_layer')
        other_leaves = self - three_layer_leaves

        # Handle standard leaves with default logic
        if other_leaves:
            super(HrLeave, other_leaves).action_validate()

        # Handle three-layer approval leaves
        if three_layer_leaves:
            current_employee = self.env.user.employee_id

            for leave in three_layer_leaves:
                if leave.state != 'validate1':
                    raise UserError(_('Team Manager must approve first before HR/Admin approval.'))

                # Check if user is HR Manager or Admin Manager
                is_hr_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
                is_admin_manager = self.env.user.has_group('three_layer_timeoff_approval.group_timeoff_administrator')

                if not is_hr_manager and not is_admin_manager:
                    raise UserError(_(
                        'You cannot validate this time off request. '
                        'You must be an HR Manager or Administration Manager.'
                    ))

                # Determine approver type
                approver_type = 'admin' if is_admin_manager else 'hr'

                # Second layer approval - final validation
                leave.write({
                    'hr_or_admin_approver_id': current_employee.id,
                    'second_approver_type': approver_type,
                })

                # Call the internal validation method
                leave._action_validate_three_layer()

                approver_label = 'Administration Manager' if approver_type == 'admin' else 'HR Manager'
                leave.message_post(
                    body=_('Final Approval (%s): %s') % (approver_label, current_employee.name),
                    subtype_xmlid='mail.mt_comment'
                )

            if not self.env.context.get('leave_fast_create'):
                three_layer_leaves.filtered(lambda h: h.validation_type != 'no_validation').activity_update()

        return True

    def _action_validate_three_layer(self):
        """Internal method to finalize three-layer approval"""
        self.ensure_one()

        # Check for public holidays
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            raise ValidationError(_(
                'The following employees are not supposed to work during that period:\n %s'
            ) % ','.join(leaves.mapped('employee_id.name')))

        # Set to final approved state
        self.write({'state': 'validate'})

        # Validate leave request (allocation, etc.)
        self._validate_leave_request()

    def _check_approval_update(self, state, raise_if_not_possible=True):
        """Override to handle three-layer approval state transitions"""
        three_layer_leaves = self.filtered(lambda l: l.validation_type == 'three_layer')
        other_leaves = self - three_layer_leaves

        # Handle standard leaves
        if other_leaves:
            result = super(HrLeave, other_leaves)._check_approval_update(state, raise_if_not_possible)
            if not result:
                return False

        # Handle three-layer leaves
        if three_layer_leaves:
            if self.env.is_superuser():
                return True

            is_hr_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
            is_admin = self.env.user.has_group('three_layer_timeoff_approval.group_timeoff_administrator')

            for holiday in three_layer_leaves:
                is_time_off_manager = holiday.employee_id.leave_manager_id == self.env.user
                error_message = ""

                # Standard checks
                if holiday.state == state:
                    error_message = _('You can\'t do the same action twice.')
                elif state == 'validate1' and holiday.state != 'confirm':
                    error_message = _('Not possible. Team Manager must approve from "To Approve" state.')
                elif state == 'validate' and holiday.state != 'validate1':
                    error_message = _('Not possible. HR/Admin must approve from "Second Approval" state.')
                elif holiday.state == 'cancel':
                    error_message = _('A cancelled leave cannot be modified.')
                elif state == 'validate1':
                    if not is_time_off_manager and not is_hr_officer and not is_admin:
                        error_message = _('Only the Time Off Manager can give first approval.')
                elif state == 'validate':
                    if not is_hr_officer and not is_admin:
                        error_message = _('Only HR Manager or Administration Manager can give final approval.')
                elif state == 'refuse':
                    if not is_time_off_manager and not is_hr_officer and not is_admin:
                        error_message = _('You do not have permission to refuse this leave.')

                if error_message:
                    if raise_if_not_possible:
                        raise UserError(error_message)
                    return False

        return True

    def _get_next_states_by_state(self):
        """Override to define state transitions for three-layer approval"""
        self.ensure_one()

        # Default behavior for non three-layer
        if self.validation_type != 'three_layer':
            return super(HrLeave, self)._get_next_states_by_state()

        # Three-layer state transitions
        state_result = {
            'confirm': set(),
            'validate1': set(),
            'validate': set(),
            'refuse': set(),
            'cancel': set()
        }

        user_employees = self.env.user.employee_ids
        is_own_leave = self.employee_id in user_employees
        is_in_past = self.date_from.date() < fields.Date.today()

        is_hr_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_admin = self.env.user.has_group('three_layer_timeoff_approval.group_timeoff_administrator')
        is_time_off_manager = self.employee_id.leave_manager_id == self.env.user
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')

        # Own leave cancellation rights
        if is_own_leave and (not is_in_past or is_hr_officer or is_admin):
            state_result['validate1'].add('cancel')
            state_result['validate'].add('cancel')
            state_result['refuse'].add('cancel')

        # Manager/Admin full rights
        if is_manager or is_admin:
            state_result['confirm'].add('validate1')
            state_result['validate1'].add('validate')
            state_result['confirm'].update({'refuse'})
            state_result['validate1'].update({'refuse', 'confirm'})
            state_result['validate'].update({'refuse', 'confirm'})
            state_result['refuse'].update({'confirm', 'validate1', 'validate'})
            state_result['cancel'].update({'confirm', 'validate1', 'validate'})

        # Team Manager rights (first approval only)
        elif is_time_off_manager:
            state_result['confirm'].add('validate1')
            state_result['confirm'].add('refuse')
            state_result['validate1'].add('refuse')

        # HR Officer rights (second approval)
        elif is_hr_officer:
            state_result['validate1'].add('validate')
            state_result['validate1'].add('refuse')

        return state_result

    def action_refuse(self):
        """Override to handle three-layer approval refusal"""
        three_layer_leaves = self.filtered(lambda l: l.validation_type == 'three_layer')
        other_leaves = self - three_layer_leaves

        # Handle standard leaves
        if other_leaves:
            super(HrLeave, other_leaves).action_refuse()

        # Handle three-layer leaves
        if three_layer_leaves:
            for leave in three_layer_leaves:
                is_time_off_manager = leave.employee_id.leave_manager_id == self.env.user
                is_hr_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
                is_admin = self.env.user.has_group('three_layer_timeoff_approval.group_timeoff_administrator')

                if not is_time_off_manager and not is_hr_officer and not is_admin:
                    raise UserError(_(
                        'You do not have permission to refuse this time off request.'
                    ))

                leave.message_post(
                    body=_('Time off request refused by: %s') % self.env.user.name,
                    subtype_xmlid='mail.mt_comment'
                )

            three_layer_leaves.write({
                'state': 'refuse',
                'first_approver_id': False,
                'second_approver_id': False,
            })

            three_layer_leaves.activity_update()

        return True