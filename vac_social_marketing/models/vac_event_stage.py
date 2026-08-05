from odoo import models, fields, api


class VacEventStage(models.Model):
    _name = 'vac.event.stage'
    _description = 'VAC Event Stage'
    _order = 'sequence, name'

    name = fields.Char(
        string='Stage Name',
        required=True,
        translate=True,
        help='Name of the event stage (e.g., Draft, Published, Completed)'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of this stage'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of stages in the kanban view'
    )
    
    fold = fields.Boolean(
        string='Folded in Kanban',
        default=False,
        help='This stage is folded in the kanban view when there are no records'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, it will hide the stage without removing it'
    )
    
    # Optional: Color for UI
    color = fields.Integer(
        string='Color Index',
        default=0,
        help='Color for kanban view'
    )