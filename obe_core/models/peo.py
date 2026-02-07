
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

class ObePEO(models.Model):

    _name = 'obe.peo'
    _description = 'Program Educational Objective (PEO)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'program_id, sequence, name'
    _rec_name = "ref_name"
    
    date= fields.Date(string='Created Date', default=lambda self: fields.Date.today())
    ref_name = fields.Char(string="Reference", default="New", readonly=True, copy=False)

    name = fields.Char(
        string='PEO Code',
        tracking=True,
        help='E.g., PEO1, PEO2, PEO3'
    )

    description = fields.Text(
        string='PEO Description',
        
        tracking=True,
        help='Detailed description of what graduates should achieve 3-5 years after graduation'
    )
    program_id = fields.Many2one(
        'obe.academic.program',
        string='Program',
        ondelete='cascade',
        index=True,
        tracking=True
    )
    timeline_years = fields.Integer(
        string='Timeline (Years)',
        default=5,
        help='Expected years after graduation for achievement (typically 3-5 years)'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    institution_id = fields.Many2one(
        'obe.institution',
        string='Institution',
        ondelete='cascade',
        index=True,
        tracking=True,
        help='Institution this PEO belongs to'
    )
    
    state = fields.Selection([
    ('draft', 'Draft'),
    ('confirm', 'Confirmed'),
    ], string='Status', default='draft', required=True)

    plo_ids = fields.Many2many(
        'obe.plo',
        'plo_peo_rel',
        'peo_id',
        'plo_id',
        string='Related PLOs',
        help='PLOs that contribute to this PEO'
    )

    evidence_ids = fields.Many2many(
        'ir.attachment',
        'peo_evidence_rel',
        'peo_id',
        'attachment_id',
        string='Evidence Documents',
        help='Supporting documents, surveys, stakeholder feedback'
    )
    stakeholder_input = fields.Text(
        string='Stakeholder Input',
        help='Summary of input from industry, alumni, faculty'
    )
    

    plo_count = fields.Integer(
        string='Related PLO Count',
        compute='_compute_plo_count',
        store=True
    )

    website = fields.Char(string='Website')
    code = fields.Char(string='Institution Code',  tracking=True)


    @api.model
    def create(self, vals):

        if vals.get('ref_name', 'New') == 'New':
            last_record = self.search(
                [('ref_name', 'like', 'PEO/%')],
                order='id desc',
                limit=1
            )
            
            if last_record and last_record.ref_name:
                try:
                    last_seq = int(last_record.ref_name.split('/')[-1])
                    next_seq = str(last_seq + 1).zfill(5)
                except:
                    next_seq = '00001'
            else:
                next_seq = '00001'

            vals['ref_name'] = f"PEO/{next_seq}"

        return super(ObePEO, self).create(vals)


    @api.onchange("institution_id")
    def get_institution(self):
        self.website = self.institution_id.website
        self.code = self.institution_id.code 

        
    
    @api.depends('plo_ids')
    def _compute_plo_count(self):
        for record in self:
            record.plo_count = len(record.plo_ids)

    @api.constrains('description')
    def _check_description_length(self):
        """Validate description length"""
        for record in self:
            if len(record.description) < 50:
                raise ValidationError(
                    _('PEO description must be at least 50 characters.')
                )
            if len(record.description) > 1000:
                raise ValidationError(
                    _('PEO description cannot exceed 1000 characters.')
                )

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.program_id.code} - {record.name}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Enhanced search to include program code"""
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('program_id.code', operator, name)] + domain
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    def action_submit_for_review(self):
        """Submit PEO for review"""
        self.ensure_one()
        if not self.description:
            raise ValidationError(_('Please provide a description before submitting for review.'))
        self.state = 'review'
        self.message_post(body=_('PEO submitted for review.'))
        
        # Notify program coordinator
        if self.program_id.coordinator_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.program_id.coordinator_id.id,
                summary=_('PEO Review Required'),
                note=_('Please review PEO: %s') % self.name
            )

    def action_approve(self):
        """Approve the PEO"""
        self.ensure_one()
        if self.state != 'review':
            raise ValidationError(_('Only PEOs under review can be approved.'))
        self.state = 'approved'
        self.message_post(body=_('PEO approved.'))

    def action_publish(self):
        """Publish the PEO"""
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_('Only approved PEOs can be published.'))
        self.state = 'published'
        self.message_post(body=_('PEO published.'))


    def action_view_plos(self):
        """View related PLOs"""
        self.ensure_one()
        return {
            'name': _('Related PLOs'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.plo',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.plo_ids.ids)],
        }
    
    def action_draft(self):
        self.ensure_one()
        if self.state != 'draft':
            self.state = 'draft'

    def action_confirm(self):
        self.ensure_one()
        if self.state != 'confirm':
            self.state = 'confirm'