# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>; )
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>;
#
#################################################################################
from odoo import models, fields, Command
import logging
_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):

    _inherit = "hr.employee"

    is_teacher = fields.Boolean(string="Is a teacher ?", groups="base.group_user")
    is_supervisor = fields.Boolean(string="Is a supervisor?", groups="base.group_user")
    current_leave_id = fields.Many2one('hr.leave.type', compute='_compute_current_leave', string="Current Time Off Type",
                                       groups="base.group_user")
    message_main_attachment_id = fields.Many2one(groups="base.group_user")
    subject_ids = fields.Many2many('wk.grade.subjects', string="Subjects")
    last_check_in = fields.Datetime(groups="base.group_user")
    activity_ids = fields.One2many(groups="base.group_user")
    activity_state = fields.Selection(groups="base.group_user")
    activity_user_id = fields.Many2one(groups="base.group_user")
    activity_type_id = fields.Many2one(groups="base.group_user")
    activity_type_icon = fields.Char(groups="base.group_user")
    activity_date_deadline = fields.Date(groups="base.group_user")
    my_activity_date_deadline = fields.Date(groups="base.group_user")
    activity_summary = fields.Char(groups="base.group_user")
    activity_exception_decoration = fields.Selection(groups="base.group_user")
    activity_exception_icon = fields.Char(groups="base.group_user")
    attendance_manager_id = fields.Many2one(groups="base.group_user")

    def action_create_user(self):
        self.ensure_one()
        res = super().action_create_user()
        if res.get('context', False).get('default_is_teacher', False):
            res.get('context', False)['default_groups_id'] = [
                Command.link(self.env.ref('base.group_user').id),
                Command.link(self.env.ref(
                    'hr_holidays.group_hr_holidays_responsible').id),
                Command.link(self.env.ref(
                    'hr_attendance.group_hr_attendance_officer').id),
                Command.link(self.env.ref(
                    'hr_attendance.group_hr_attendance_own_reader').id),
                Command.link(self.env.ref(
                    'wk_school_management.wk_school_management_staff_group').id),
            ]

        return res
