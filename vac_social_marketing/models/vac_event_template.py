from odoo import models, fields, api
from odoo.exceptions import ValidationError
import pytz

def _tz_get(self):
    return [(tz, tz) for tz in sorted(pytz.all_timezones)]


class VacEventTemplates(models.Model):
    _name = 'vac.event.templates'
    _description = 'VAC Event Templates'
    _order = 'name'

    name = fields.Char(
        string='Template Name',
        required=True,
        translate=True,
        help='Name of the event template (e.g., Health Fair, Webinar, Product Launch)'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of the template and its purpose'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, it will hide the template without removing it'
    )
    
    # Optional: Default values for events using this template
    default_venue = fields.Text(
        string='Default Venue',
        help='Suggested venue text for events using this template'
    )
    
    default_timezone_id = fields.Selection(
        _tz_get,
        string='Default Timezone',
        help='Default timezone for events using this template'
    )
    
    # Optional: Template content/instructions
    instructions = fields.Html(
        string='Instructions',
        help='Guidelines or instructions for organizing this type of event'
    )
    
    # Count of events using this template
    event_count = fields.Integer(
        string='Events',
        compute='_compute_event_count',
        help='Number of events using this template'
    )
    
    def _compute_event_count(self):
        """Count events using this template"""
        for template in self:
            template.event_count = self.env['vac.event'].search_count([
                ('template_id', '=', template.id)
            ])
    
    # Override unlink to prevent deletion if template is in use
    def unlink(self):
        """Prevent deletion of templates in use - suggest archiving instead"""
        for template in self:
            if template.event_count > 0:
                raise ValidationError(
                    f'Cannot delete template "{template.name}" because it is used by {template.event_count} event(s). '
                    'Please archive the template instead by setting Active to False.'
                )
        return super(VacEventTemplates, self).unlink()