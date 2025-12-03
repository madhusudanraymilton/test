from odoo import models, fields, api


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    # Override validation_type to include three-layer option
    validation_type = fields.Selection(
        selection_add=[('three_layer', 'Three Layer (Manager + HR/Admin)')],
        ondelete={'three_layer': 'set default'},
        help="Three Layer: Team Manager → HR Manager OR Admin Manager → Approved"
    )