# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>; )
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>;
#
#################################################################################
from odoo import models, api, fields

import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_student = fields.Boolean(string="Is a student")
    is_parent = fields.Boolean(string="Is a parent")
    student_ids = fields.Many2many('student.student','student_student_res_partner_rel',
        'partner_id','student_id',string="Students")
    student_portal_active = fields.Boolean(string='Student Portal Active', compute='_compute_student_portal_active')

    @api.depends('student_ids.user_id')
    def _compute_student_portal_active(self):
        for parent in self:
            parent.student_portal_active = False
            for student in parent.student_ids:
                if student.user_id and student.user_id.has_group('base.group_portal'):
                    parent.student_portal_active = True
                    break

    def get_student_partner_id(self):
        self.ensure_one()
        student_id = self.env['student.student'].search([('partner_id', '=', self.id)])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'student.student',
            'view_mode': 'form',
            'res_id': student_id.id,
            'views': [[self.env.ref('wk_school_management.student_student_form').id, 'form']],
        }
    
    def get_child_id(self):
        self.ensure_one()
        return{
            'name': 'Children',
            'type': 'ir.actions.act_window',
            'res_model': 'student.student',
            'view_mode': 'tree,form',
            'domain': [('parent_ids', '=', self.id)],
            'views': [(False, 'list'), (False, 'form')],        
        }
