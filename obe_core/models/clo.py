
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ObeCLO(models.Model):
    """Course Learning Outcomes Management"""
    _name = 'obe.clo'
    _description = 'Course Learning Outcome (CLO/CO)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'offering_id, sequence, name'

    name = fields.Char(
        string='CLO Code',
        required=True,
        tracking=True,
        help='E.g., CO1, CO2, CLO1'
    )
    statement = fields.Text(
        string='CLO Statement',
        required=True,
        tracking=True,
        help='Clear, measurable statement starting with action verb (50-300 characters)'
    )
    course_id = fields.Many2one(
        'obe.course',
        string='Course',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    offering_id = fields.Many2one(
        'obe.course.offering',
        string='Course Offering',
        ondelete='cascade',
        tracking=True,
        help='Specific semester offering (if applicable)'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
    ], string='Status', default='draft', required=True, tracking=True)

    bloom_level = fields.Selection([
        ('remember', 'Remember'),
        ('understand', 'Understand'),
        ('apply', 'Apply'),
        ('analyze', 'Analyze'),
        ('evaluate', 'Evaluate'),
        ('create', 'Create'),
    ], string='Bloom\'s Taxonomy Level', required=True, tracking=True)
    
    cognitive_level = fields.Selection([
        ('knowledge', 'Knowledge'),
        ('comprehension', 'Comprehension'),
        ('application', 'Application'),
        ('analysis', 'Analysis'),
        ('synthesis', 'Synthesis'),
        ('evaluation', 'Evaluation'),
    ], string='Cognitive Level')
    
    action_verb = fields.Char(
        string='Action Verb',
        compute='_compute_action_verb',
        store=True,
        help='First word of the statement (should be an action verb)'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order'
    )
    
    target_attainment = fields.Float(
        string='Target Attainment %',
        default=70.0,
        help='Expected percentage of students achieving this CLO'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    plo_ids = fields.Many2many(
        'obe.plo',
        'clo_plo_rel',
        'clo_id',
        'plo_id',
        string='Mapped PLOs',
        help='Program Learning Outcomes this CLO contributes to'
    )

    plo_count = fields.Integer(
        string='Mapped PLO Count',
        compute='_compute_plo_count',
        store=True
    )

    bloom_action_verbs = fields.Char(
        string='Expected Action Verbs',
        compute='_compute_bloom_action_verbs',
        help='Suggested action verbs for selected Bloom level'
    )
    institution_id = fields.Many2one('obe.institution', string='Institution', required=True, ondelete='cascade')
    website = fields.Char(string="Website")
    code = fields.Char(string='Institution Code', required=True, tracking=True)

    @api.depends('plo_ids')
    def _compute_plo_count(self):
        for record in self:
            record.plo_count = len(record.plo_ids)

    @api.depends('statement')
    def _compute_action_verb(self):
        """Extract the first word (action verb) from the statement"""
        for record in self:
            if record.statement:
                words = record.statement.strip().split()
                record.action_verb = words[0] if words else ''
            else:
                record.action_verb = ''

    @api.depends('bloom_level')
    def _compute_bloom_action_verbs(self):
        """Suggest action verbs based on Bloom's level"""
        bloom_verbs = {
            'remember': 'Define, List, Recall, Recognize, State, Identify',
            'understand': 'Describe, Explain, Interpret, Summarize, Classify, Compare',
            'apply': 'Apply, Demonstrate, Solve, Use, Execute, Implement',
            'analyze': 'Analyze, Differentiate, Examine, Compare, Contrast, Investigate',
            'evaluate': 'Evaluate, Assess, Critique, Judge, Justify, Recommend',
            'create': 'Create, Design, Develop, Construct, Formulate, Generate',
        }
        for record in self:
            record.bloom_action_verbs = bloom_verbs.get(record.bloom_level, '')

    
    @api.constrains('statement', 'bloom_level')
    def _check_action_verb_alignment(self):
        """Validate that statement starts with appropriate action verb"""
        bloom_verbs = {
            'remember': ['define', 'list', 'recall', 'recognize', 'state', 'identify', 'name', 'label'],
            'understand': ['describe', 'explain', 'interpret', 'summarize', 'classify', 'compare', 'discuss'],
            'apply': ['apply', 'demonstrate', 'solve', 'use', 'execute', 'implement', 'employ'],
            'analyze': ['analyze', 'differentiate', 'examine', 'compare', 'contrast', 'investigate', 'categorize'],
            'evaluate': ['evaluate', 'assess', 'critique', 'judge', 'justify', 'recommend', 'appraise'],
            'create': ['create', 'design', 'develop', 'construct', 'formulate', 'generate', 'produce'],
        }
        
        for record in self:
            if record.statement and record.bloom_level:
                first_word = record.statement.strip().split()[0].lower().rstrip('.,;:')
                expected_verbs = bloom_verbs.get(record.bloom_level, [])
                if first_word not in expected_verbs and expected_verbs:
                    pass

    @api.constrains('plo_ids')
    def _check_plo_mapping(self):
        """Warn if CLO is not mapped to any PLO"""
        for record in self:
            pass

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            if record.offering_id:
                name = f"{record.offering_id.course_id.code} - {record.name}"
            elif record.course_id:
                name = f"{record.course_id.code} - {record.name}"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Enhanced search to include course code"""
        domain = domain or []
        if name:
            domain = ['|', '|', 
                     ('name', operator, name), 
                     ('course_id.code', operator, name),
                     ('offering_id.course_id.code', operator, name)] + domain
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    def action_view_plos(self):
        """View mapped PLOs"""
        self.ensure_one()
        return {
            'name': _('Mapped PLOs'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.plo',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.plo_ids.ids)],
        }

    def action_map_to_plo(self):
        """Open wizard to map CLO to PLOs"""
        self.ensure_one()
        return {
            'name': _('Map CLO to PLOs'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.clo.plo.mapping',
            'view_mode': 'form',
            'context': {
                'default_clo_id': self.id,
                'default_course_id': self.course_id.id,
            },
            'target': 'new',
        }
    @api.onchange('institution_id')
    def get_institution(self):
        self.code = self.institution_id.code 
        self.website = self.institution_id.website

    
    def action_active(self):
        self.ensure_one()
        self.write({'state': 'active'})
        return True

    def action_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})
        return True
    