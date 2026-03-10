# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountAssetExtended(models.Model):
    _inherit = 'account.asset'
    # Reserved for future extensions to Odoo's native account.asset model.
