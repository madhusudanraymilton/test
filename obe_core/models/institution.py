from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re

class ObeInstitution(models.Model):
    _name = 'obe.institution'
    _description = 'OBE Institution'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Institution Name', required=True, tracking=True)
    code = fields.Char(string='Institution Code', required=True, tracking=True)
    vision = fields.Text(string='Vision Statement', tracking=True)
    mission = fields.Text(string='Mission Statement', tracking=True)
    core_values = fields.Html(string="Core Values")
    note = fields.Html(string="Notes")
    website = fields.Char(string='Website')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')

    founded_date = fields.Date(string="Founded Date")
    accreditation = fields.Char(string="Accreditation Status")
    institution_type = fields.Selection([('public','Public'), ('private','Private')], string='Type')
    accreditation_body = fields.Selection([
        ('baete', 'BAETE - Bangladesh'),
        ('abet', 'ABET - International'),
        ('nba', 'NBA - India'),
        ('washington', 'Washington Accord'),
        ('other', 'Other')
    ], string='Primary Accreditation Body', tracking=True)
    effective_date = fields.Date(string='Effective Date', default=fields.Date.context_today, required=True, tracking=True)

    contact_person = fields.Char(string="Primary Contact Person")
    contact_phone = fields.Char(string="Contact Phone")
    contact_email = fields.Char(string="Contact Email")
    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one('res.country.state', string='State')
    city = fields.Char(string='City')
    zip_code = fields.Char(string='ZIP Code')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    state = fields.Selection([('draft','Draft'),('confirm','Confirm')], string="Status", default='draft', tracking=True)
    program_ids = fields.One2many('obe.academic.program', 'institution_id', string='Academic Programs')
    program_count = fields.Integer(string='Program Count', compute='_compute_program_count', store=True)
    version = fields.Integer(string='Version', default=1, readonly=True)
    previous_version_id = fields.Many2one('obe.institution', string='Previous Version', readonly=True)
    
    ### Relational Model 
    
    mission_ids = fields.One2many('obe.mission', 'institution_id', string='Missions')
    vision_ids = fields.One2many('obe.vision', 'institution_id', string='Visions')
    @api.depends('program_ids')
    def _compute_program_count(self):
        for record in self:
            record.program_count = len(record.program_ids)

    @api.constrains('vision')
    def _check_vision_length(self):
        for record in self:
            if record.vision and len(record.vision) > 2000:
                raise ValidationError(_('Vision statement cannot exceed 2000 characters.'))

    @api.constrains('mission')
    def _check_mission_length(self):
        for record in self:
            if record.mission and len(record.mission) > 2000:
                raise ValidationError(_('Mission statement cannot exceed 2000 characters.'))

    @api.constrains('email')
    def _check_email_validity(self):
        for record in self:
            if record.email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', record.email):
                raise ValidationError(_('Please enter a valid email address.'))

    @api.constrains('active')
    def _check_single_active(self):
        for record in self:
            if record.active:
                active_count = self.search_count([('active', '=', True), ('id', '!=', record.id)])
                if active_count:
                    raise ValidationError(_('Only one institution can be active at a time.'))


    def action_draft(self):
        self.ensure_one()
        if self.state != 'draft':
            self.state = 'draft'

    def action_confirm(self):
        self.ensure_one()
        if self.state != 'confirm':
            self.state = 'confirm'

    def create_new_version(self):
        self.ensure_one()
        new_version = self.copy({
            'version': self.version + 1,
            'previous_version_id': self.id,
            'state': 'draft',
            'active': False,
        })
        self.active = False
        self.message_post(body=_('New version created: Version %s') % new_version.version)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'obe.institution',
            'res_id': new_version.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_programs(self):
        self.ensure_one()
        return {
            'name': _('Academic Programs'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.academic.program',
            'view_mode': 'tree,form',
            'domain': [('institution_id', '=', self.id)],
            'context': {'default_institution_id': self.id}
        }
    
class ObeMission(models.Model):
    _name = 'obe.mission'
    _description = 'Institution Mission'
    _order = 'sequence'

    name = fields.Char(string='Mission Title', required=True, tracking=True)
    description = fields.Html(string='Mission Description', required=True, tracking=True)
    institution_id = fields.Many2one('obe.institution', string='Institution', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('description')
    def _check_description_length(self):
        for record in self:
            if record.description and len(record.description) > 2000:
                raise ValidationError(_('Mission description cannot exceed 2000 characters.'))


class ObeVision(models.Model):
    _name = 'obe.vision'
    _description = 'Institution Vision'
    _order = 'sequence'

    name = fields.Char(string='Vision Title', required=True, tracking=True)
    description = fields.Html(string='Vision Description', required=True, tracking=True)
    institution_id = fields.Many2one('obe.institution', string='Institution', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('description')
    def _check_description_length(self):
        for record in self:
            if record.description and len(record.description) > 2000:
                raise ValidationError(_('Vision description cannot exceed 2000 characters.'))
