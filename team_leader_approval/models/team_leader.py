from odoo import api, fields, models, exceptions

class TeamLeader(models.Model):
    _inherit = 'hr.employee'

