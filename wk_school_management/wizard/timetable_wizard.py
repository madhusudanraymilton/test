# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>; )
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>;
#
#################################################################################
from odoo import models, fields, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class TimetableConfirmWizard(models.TransientModel):

    _name = 'wk.confirm.timetable'
    _inherit = 'wk.section.visibility.mixin'
    _description = 'A confirmation wizard for weekly slots'

    name = fields.Char(string='Title', readonly=True)
    weekly_schedule_ids = fields.Many2many(
        'wk.weekly.schedule', string="Weekly Schedule", readonly=True)
    grade_id = fields.Many2one(
        "wk.school.grade", string="Grade", readonly=True)
    section_id = fields.Many2one(
        "wk.grade.section", string="Section", readonly=True)
    start_date = fields.Date(string="Start From", readonly=True)
    end_date = fields.Date(string="End Till", readonly=True)
    subject_id = fields.Many2one(
        'wk.grade.subjects', string='Subject', readonly=True)

    def schedule_now(self):
        populate_class_id = self._context.get('active_id')
        populate_class = self.env['wk.school.class'].browse(populate_class_id)

        start_date = populate_class.start_date
        end_date = populate_class.end_date

        new_schedule = populate_class.weekly_schedule_ids.filtered(
            lambda e: e.state == 'new')
        if len(new_schedule) == 0:
            raise UserError(_("Classes already scheduled."))

        for schedule in populate_class.weekly_schedule_ids:

            current_date = start_date

            while current_date <= end_date:
                if schedule.state == 'new':
                    if schedule.weekday.capitalize() == current_date.strftime("%A"):

                        start_str, end_str = schedule.timeslot_id.name.split(
                            '-')
                        start_time_str = f'{current_date} {start_str}'
                        end_time_str = f'{current_date} {end_str}'
                        start_time = datetime.strptime(
                            start_time_str, '%Y-%m-%d %I:%M %p')
                        end_time = datetime.strptime(
                            end_time_str, '%Y-%m-%d %I:%M %p')

                        subject = populate_class.subject_id
                        grade = populate_class.grade_id
                        name = str(grade.name) + str(populate_class.title) + \
                            '-' + str(subject.name) + \
                            '(' + str(current_date) + ')'

                        timetable_enteries = {
                            'name': name,
                            'grade_id': populate_class.grade_id.id,
                            'subject_id': populate_class.subject_id.id,
                            'location_id': schedule.location_id.id,
                            'timeslot_id': schedule.timeslot_id.id,
                            'session_id': populate_class.session_id.id,
                            'term_id': populate_class.term_id.id,
                            'class_date': current_date,
                            'day': schedule.weekday,
                            'teacher_id': populate_class.teacher_id.id,
                            'populate_class_id': populate_class.id,
                            'start_time': start_time - timedelta(hours=5, minutes=30),
                            'end_time': end_time - timedelta(hours=5, minutes=30),
                        }
                        self.env['wk.class.timetable'].create(
                            timetable_enteries)
                current_date += timedelta(days=1)
            schedule.state = 'done'
