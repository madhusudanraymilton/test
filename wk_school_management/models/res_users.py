# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>; )
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>;
#
#################################################################################
from odoo import models, api
import logging
_logger = logging.getLogger(__name__)


class ResUser(models.Model):

    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if self._context.get('is_student', False) and self._context.get('active_id', False):
            student = self.env['student.student'].browse(
                self._context.get('active_id', False))
            student.user_id = res.id
            res.partner_id.is_student = True
        return res
