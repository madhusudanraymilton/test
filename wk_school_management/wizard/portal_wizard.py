# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>; )
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>;
#
#################################################################################

from odoo import models, fields
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class PortalWizardUserAccess(models.TransientModel):

    _name = 'wk.portal.wizard.user'
    _description = 'Portal Wizard User Access'

    access_choice = fields.Selection([
    ('single_access', 'Want to manage with single access?'),
    ('dual_access', 'Separate access for student and parent?'),
        ], string='Access', default="single_access", required=True, help="""
            Select 'Single Access' if you want both student and parent to share the same login.
            Select 'Dual Access' if you want to create separate logins for the student and the parent.
        """)
    parent_ids = fields.Many2many('res.partner', string='Parent',
                                  domain="[('is_parent', '=', True)]")
    student_ids = fields.Many2many('student.student', string='Students')

    def get_or_create_partner(self, name, email, student=None, mobile=None, image=None):
        partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
        if not partner and student:
            vals = {
                'name': name,
                'email': email,
                'street': student.street or False,
                'street2': student.street2 or False,
                'zip': student.zip or False,
                'city': student.city or False,
                'state_id': student.state_id.id if student.state_id else False,
                'country_id': student.country_id.id if student.country_id else False,
            }
            if mobile:
                vals['mobile'] = mobile
            if image:
                vals['image_1920'] = image
            partner = self.env['res.partner'].create(vals)
        return partner
    
    def grant_portal_access(self, partner):
        portal_wizard = self.env['portal.wizard'].with_context(default_partner_ids=[partner.id]).create({})
        wizard_user = self.env['portal.wizard.user'].create({
            'wizard_id': portal_wizard.id,
            'partner_id': partner.id,
            'email': partner.email,
        })
        if not (wizard_user.is_portal or wizard_user.is_internal):
            wizard_user.action_grant_access()

    def grant_now(self):
        if self.access_choice == 'single_access':
            for student in self.student_ids:
                _logger.info(f'Single access: Granting access for student {student.name}')

                partner = self.get_or_create_partner(
                    name=student.father_name,
                    email=student.parent_email,
                    mobile=student.fathers_contact,
                    student=student
                )
                self.grant_portal_access(partner)
                student.user_id = partner.user_ids[:1]
                student.parent_ids = [(4, partner.id)]
                partner.is_parent = True

        elif self.access_choice == 'dual_access':
            for student in self.student_ids:
                _logger.info(f'Dual access: Granting access for student {student.name}')

                student_partner = self.get_or_create_partner(
                    name=student.name,
                    email=student.email,
                    mobile=student.mobile,
                    image=student.student_image,
                    student=student
                )
                self.grant_portal_access(student_partner)
                student.user_id = student_partner.user_ids[:1]
                student_partner.is_student = True

                parent_ids_to_link = []
                for parent in student.parent_ids:
                    if parent.email == student.email:
                        _logger.info(f'Skipping self-link for {parent.name}')
                        continue
                    else:
                        parent_partner = self.get_or_create_partner(
                            name=parent.name,
                            email=parent.email,
                            student=student
                        )
                        self.grant_portal_access(parent_partner)
                        parent_partner.is_parent = True
                        if parent_partner.id not in parent_ids_to_link:
                            parent_ids_to_link.append(parent_partner.id)

                if parent_ids_to_link:
                    student.parent_ids = [(6, 0, parent_ids_to_link)]
