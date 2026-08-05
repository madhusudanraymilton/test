# -*- coding: utf-8 -*-
from odoo import models, fields, api


class VacSocialLeadStage(models.Model):
    _name = 'vac.social.lead.stage'
    _description = 'VAC Social Lead Stage'
    _order = 'sequence, id'

    name = fields.Char(
        string='Stage Name',
        required=True,
        translate=True,
        help='Name of the social lead stage (e.g., New, Contacted, Distributed, Closed)',
    )

    description = fields.Text(
        string='Description',
        translate=True,
    )

    sequence = fields.Integer(
        string='Sequence',
        default=lambda self: self._next_sequence(),
        help='Order of stages in the kanban view',
    )

    fold = fields.Boolean(
        string='Folded in Kanban',
        default=False,
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    color = fields.Integer(
        string='Color Index',
        default=0,
    )

    # Lead count in this stage
    lead_count = fields.Integer(
        string='Leads',
        compute='_compute_lead_count',
        help='Number of social leads in this stage',
    )

    @api.model
    def _next_sequence(self):
        last = self.search([], order='sequence desc', limit=1)
        return (last.sequence + 10) if last else 10

    def _compute_lead_count(self):
        for stage in self:
            stage.lead_count = self.env['vac.event.lead'].search_count([
                ('social_stage_id', '=', stage.id),
            ])
