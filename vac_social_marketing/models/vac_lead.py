# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class VacEventLead(models.Model):
    _name = 'vac.event.lead'
    _description = 'VAC Event Lead'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc, id desc'

    # Basic Information
    name = fields.Char(
        string='Lead Name',
        required=True,
        tracking=True,
        help='Full name of the lead'
    )

    email = fields.Char(
        string='Email',
        required=True,
        tracking=True,
        help='Email address of the lead'
    )

    first_name = fields.Char(
        string='First Name',
        tracking=True,
    )

    last_name = fields.Char(
        string='Last Name',
        tracking=True,
    )

    platform = fields.Selection(
        selection=[
            ('facebook',  'Facebook'),
            ('instagram', 'Instagram'),
            ('office',    'Offices'),
            ('event',     'Event'),
        ],
        string='Platform',
        tracking=True,
        help='Platform through which this lead was acquired'
    )

    mobile = fields.Char(
        string='Mobile',
        tracking=True,
        help='Contact phone number'
    )

    whatsapp_number = fields.Char(
        string='WhatsApp Number',
        tracking=True,
    )

    birthday = fields.Date(
        string='Date of Birth',
        tracking=True,
        help='Birth date of the lead'
    )

    crm_lead_id = fields.Many2one(
        'crm.lead',
        string='CRM Lead',
        tracking=True,
        ondelete='set null',
        help='Linked CRM Lead'
    )

    ssn = fields.Char(
        string='SSN / ID Number',
        tracking=True,
        help='Social Security Number or National ID'
    )

    is_current_client = fields.Boolean(
        string='Current VAC Client',
        tracking=True,
    )

    is_veteran = fields.Boolean(
        string='US Veteran',
        tracking=True,
    )

    physical_address = fields.Text(
        string='Current Physical Address',
        tracking=True,
    )

    is_bringing_plus_one = fields.Boolean(
        string='Bringing a Plus One',
        tracking=True,
    )

    current_va_disability_rating = fields.Float(
        string='Current VA Disability Rating',
        tracking=True,
    )

    has_dd214_copy = fields.Boolean(
        string='Has DD214 Copy / Access',
        tracking=True,
    )

    has_dd214_access = fields.Boolean(
        string='Has Access to DD214',
        tracking=True,
    )

    # Related Event
    event_id = fields.Many2one(
        'vac.event',
        string='Source Event',
        ondelete='set null',
        tracking=True,
        help='Marketing event that generated this lead'
    )

    sponsor_id = fields.Many2one(
        'vac.sponsor',
        string='Sponsor',
        tracking=True,
        ondelete='set null',
        index=True,
        help='Sponsor linked to the source event for this event lead'
    )

    # Related Social Campaigns
    social_fb_id = fields.Many2one(
        'vac.social.fb',
        string='Facebook Campaign',
        ondelete='set null',
        tracking=True,
        help='Facebook campaign that generated this lead'
    )

    social_ig_id = fields.Many2one(
        'vac.social.ing',
        string='Instagram Campaign',
        ondelete='set null',
        tracking=True,
        help='Instagram campaign that generated this lead'
    )

    social_office_id = fields.Many2one(
        'vac.social.office',
        string='Offices Campaign',
        ondelete='set null',
        tracking=True,
        help='Offices campaign that generated this lead'
    )

    # Branch and Service
    branch_service_id = fields.Many2one(
        'branch.service',
        string='Branch / Service',
        ondelete='restrict',
        tracking=True,
        help='Branch or service of interest'
    )

    # Assignment
    bam_user_id = fields.Many2one(
        'res.users',
        string='Assigned BAM',
        tracking=True,
        domain=[('share', '=', False)],
        help='Business Account Manager assigned to this lead'
    )

    # Social Lead Stage (only for social media leads)
    social_stage_id = fields.Many2one(
        'vac.social.lead.stage',
        string='Social Stage',
        tracking=True,
        ondelete='restrict',
        help='Current stage of this social media lead',
        index=True,
        copy=False,
        group_expand='_read_group_social_stage_ids',
    )

    # Flag: was this social lead explicitly distributed to BAM Dashboard?
    is_social_distributed = fields.Boolean(
        string='Sent to BAM Dashboard',
        default=False,
        tracking=True,
        help='Set to True when this social lead is bulk-distributed to the BAM Dashboard',
        copy=False,
    )

    # Stage and Status
    stage_id = fields.Many2one(
        'vac.event.lead.stage',
        string='Stage',
        required=True,
        tracking=True,
        group_expand='_read_group_stage_ids',
        ondelete='restrict',
        help='Current stage of the lead',
        index=True,
        copy=False
    )

    status_id = fields.Many2one(
        'vac.event.lead.status',
        string='Status',
        required=True,
        tracking=True,
        ondelete='restrict',
        help='Current status of the lead (Active, Inactive, Blacklisted)',
        index=True
    )

    # Additional Fields
    notes = fields.Text(
        string='Notes',
        help='Internal notes about the lead'
    )

    custom_field_answers = fields.Text(
        string='Custom Field Answers',
        help='JSON blob of extra registration fields that did not map to a lead field'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Archive leads instead of deleting them'
    )

    # Computed Fields
    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        store=False,
        help='Calculated age from birth date'
    )

    # ── Default values ────────────────────────────────────────────────────────

    def init(self):
        """Backfill sponsor on existing event leads after module updates."""
        self.env.cr.execute("""
            UPDATE vac_event_lead AS lead
               SET sponsor_id = event.sponsor_id
              FROM vac_event AS event
             WHERE lead.event_id = event.id
               AND lead.sponsor_id IS NULL
               AND event.sponsor_id IS NOT NULL
        """)

    @api.model
    def default_get(self, fields_list):
        """Override to set default stage, status, and branch service."""
        res = super(VacEventLead, self).default_get(fields_list)

        # Default stage → "New Lead"
        if 'stage_id' in fields_list and 'stage_id' not in res:
            stage = self.env['vac.event.lead.stage'].search(
                [('name', '=', 'New Lead')], limit=1)
            if not stage:
                stage = self.env['vac.event.lead.stage'].search(
                    [], order='sequence, id', limit=1)
            if stage:
                res['stage_id'] = stage.id

        # Default status → "Active"
        if 'status_id' in fields_list and 'status_id' not in res:
            status = self.env['vac.event.lead.status'].search(
                [('name', '=', 'Active')], limit=1)
            if not status:
                status = self.env['vac.event.lead.status'].search(
                    [], order='name', limit=1)
            if status:
                res['status_id'] = status.id

        # Default social_stage_id → first stage by sequence (dynamically created)
        if 'social_stage_id' in fields_list and 'social_stage_id' not in res:
            social_stage = self.env['vac.social.lead.stage'].search(
                [], order='sequence, id', limit=1)
            if social_stage:
                res['social_stage_id'] = social_stage.id

        # ─── NEW: Default branch_service → whichever is_default = True ───────
        if 'branch_service_id' in fields_list and 'branch_service_id' not in res:
            default_service = self.env['branch.service'].search(
                [('is_default', '=', True)], limit=1)
            if default_service:
                res['branch_service_id'] = default_service.id

        if 'sponsor_id' in fields_list and 'sponsor_id' not in res:
            sponsor_id = self.env.context.get('default_sponsor_id')
            sponsor_name = self.env.context.get('default_sponsor_name')
            if sponsor_id:
                res['sponsor_id'] = sponsor_id
            elif sponsor_name:
                sponsor = self.env['vac.sponsor'].search(
                    [('name', '=', sponsor_name)], limit=1)
                if sponsor:
                    res['sponsor_id'] = sponsor.id

        return res

    # ── Onchange ──────────────────────────────────────────────────────────────

    @api.onchange('event_id')
    def _onchange_event_id(self):
        """Keep the event lead sponsor aligned with the selected event."""
        expected_sponsor = self._context_sponsor()
        for lead in self:
            if (
                expected_sponsor
                and lead.event_id
                and lead.event_id.sponsor_id
                and lead.event_id.sponsor_id != expected_sponsor
            ):
                lead.event_id = False
                lead.sponsor_id = expected_sponsor
                return {
                    'warning': {
                        'title': _('Event cannot be selected'),
                        'message': _(
                            'You can only select events for %(sponsor)s here. '
                            'To use a different sponsor, open that sponsor lead menu.'
                        ) % {'sponsor': expected_sponsor.display_name},
                    }
                }
            if lead.event_id:
                lead.sponsor_id = lead.event_id.sponsor_id

    @api.onchange('sponsor_id')
    def _onchange_sponsor_id(self):
        """Lock sponsor when the lead is opened from a sponsor-specific menu."""
        expected_sponsor = self._context_sponsor()

        for lead in self:
            event_sponsor = lead.event_id.sponsor_id
            if (
                not expected_sponsor
                and event_sponsor
                and lead.sponsor_id
                and lead.sponsor_id != event_sponsor
            ):
                lead.sponsor_id = event_sponsor
                return {
                    'warning': {
                        'title': _('Sponsor cannot be changed'),
                        'message': _(
                            'This event lead belongs to %(sponsor)s because '
                            'that sponsor is set on the selected event.'
                        ) % {'sponsor': event_sponsor.display_name},
                    }
                }

            if (
                expected_sponsor
                and expected_sponsor.exists()
                and lead.sponsor_id
                and lead.sponsor_id != expected_sponsor
            ):
                lead.sponsor_id = expected_sponsor
                return {
                    'warning': {
                        'title': _('Sponsor cannot be changed'),
                        'message': _(
                            'This lead belongs to %(sponsor)s. '
                            'To use a different sponsor, open that sponsor lead menu.'
                        ) % {'sponsor': expected_sponsor.display_name},
                    }
                }

            # Guard for the "All Event Leads" view: no context sponsor, no event
            # sponsor, but the lead itself already has a sponsor assigned.
            # Changing it here would silently re-attribute a sponsored lead.
            original_sponsor = lead._origin.sponsor_id
            if (
                not expected_sponsor
                and not event_sponsor
                and original_sponsor
                and lead.sponsor_id
                and lead.sponsor_id != original_sponsor
            ):
                lead.sponsor_id = original_sponsor
                return {
                    'warning': {
                        'title': _('Sponsor cannot be changed'),
                        'message': _(
                            'This lead is linked to sponsor "%(sponsor)s". '
                            'Sponsor-based leads cannot be reassigned to a different sponsor — '
                            'they will not be charged to another sponsor. '
                            'To manage this lead under a different sponsor, '
                            "open that sponsor's lead menu."
                        ) % {'sponsor': original_sponsor.display_name},
                    }
                }

    @api.onchange('crm_lead_id')
    def _onchange_crm_lead_id(self):
        """Auto-fill name and email when a CRM lead is selected."""
        if self.crm_lead_id:
            self.name  = self.crm_lead_id.name
            self.email = self.crm_lead_id.client_email or self.crm_lead_id.email_from
        else:
            self.name  = False
            self.email = False

    # ── Computed ──────────────────────────────────────────────────────────────

    @api.depends('birthday')
    def _compute_age(self):
        """Calculate age from birthday."""
        today = fields.Date.today()
        for lead in self:
            if lead.birthday:
                lead.age = today.year - lead.birthday.year - (
                    (today.month, today.day) < (lead.birthday.month, lead.birthday.day)
                )
            else:
                lead.age = 0

    # ── Group Expand ──────────────────────────────────────────────────────────

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Show all event lead stages in kanban view."""
        return self.env['vac.event.lead.stage'].search([], order='sequence, name')

    @api.model
    def _read_group_social_stage_ids(self, stages, domain):
        """Show all social lead stages in the social kanban view."""
        return self.env['vac.social.lead.stage'].search([], order='sequence, id')

    # ── Helpers ───────────────────────────────────────────────────────────────

    @api.model
    def _first_social_stage(self):
        return self.env['vac.social.lead.stage'].search(
            [], order='sequence, id', limit=1)

    def _context_sponsor(self):
        sponsor_id = self.env.context.get('default_sponsor_id')
        sponsor_name = self.env.context.get('default_sponsor_name')
        if sponsor_id:
            return self.env['vac.sponsor'].browse(sponsor_id)
        if sponsor_name:
            return self.env['vac.sponsor'].search(
                [('name', '=', sponsor_name)], limit=1)
        return self.env['vac.sponsor']

    def _stage_is_before(self, current_stage, next_stage):
        if not current_stage or not next_stage:
            return False
        return (next_stage.sequence, next_stage.id) < (
            current_stage.sequence,
            current_stage.id,
        )

    def _check_stage_move_forward_only(self, vals):
        if vals.get('stage_id'):
            next_stage = self.env['vac.event.lead.stage'].browse(vals['stage_id'])
            for lead in self:
                if self._stage_is_before(lead.stage_id, next_stage):
                    raise ValidationError(_(
                        'You cannot move "%(lead)s" back from "%(current)s" '
                        'to "%(next)s". Previous event lead stages are read-only.'
                    ) % {
                        'lead': lead.display_name,
                        'current': lead.stage_id.display_name,
                        'next': next_stage.display_name,
                    })

        if vals.get('social_stage_id'):
            next_stage = self.env['vac.social.lead.stage'].browse(
                vals['social_stage_id']
            )
            for lead in self:
                if self._stage_is_before(lead.social_stage_id, next_stage):
                    raise ValidationError(_(
                        'You cannot move "%(lead)s" back from "%(current)s" '
                        'to "%(next)s". Previous social lead stages are read-only.'
                    ) % {
                        'lead': lead.display_name,
                        'current': lead.social_stage_id.display_name,
                        'next': next_stage.display_name,
                    })

    # ── Create / Write overrides ──────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        first_stage = self._first_social_stage()
        context_sponsor = self._context_sponsor()
        for vals in vals_list:
            if vals.get('event_id') and not vals.get('sponsor_id'):
                event = self.env['vac.event'].browse(vals['event_id'])
                if (
                    context_sponsor
                    and event.sponsor_id
                    and event.sponsor_id != context_sponsor
                ):
                    raise ValidationError(_(
                        'You can only select events for %(sponsor)s here. '
                        'To use a different sponsor, open that sponsor lead menu.'
                    ) % {'sponsor': context_sponsor.display_name})
                vals['sponsor_id'] = event.sponsor_id.id or False
            elif vals.get('event_id') and vals.get('sponsor_id'):
                event = self.env['vac.event'].browse(vals['event_id'])
                if event.sponsor_id and vals['sponsor_id'] != event.sponsor_id.id:
                    raise ValidationError(_(
                        'This event lead belongs to %(sponsor)s because '
                        'that sponsor is set on the selected event.'
                    ) % {'sponsor': event.sponsor_id.display_name})
            if context_sponsor:
                if vals.get('sponsor_id') and vals['sponsor_id'] != context_sponsor.id:
                    raise ValidationError(_(
                        'This lead belongs to %(sponsor)s. '
                        'To use a different sponsor, open that sponsor lead menu.'
                    ) % {'sponsor': context_sponsor.display_name})
                vals['sponsor_id'] = context_sponsor.id

            is_social_lead = (
                vals.get('social_fb_id')
                or vals.get('social_ig_id')
                or vals.get('social_office_id')
                or vals.get('platform') in ('facebook', 'instagram', 'office')
            )
            if first_stage and is_social_lead:
                vals['social_stage_id'] = first_stage.id
        return super().create(vals_list)

    def write(self, vals):
        self._check_stage_move_forward_only(vals)
        context_sponsor = self._context_sponsor()
        if context_sponsor and vals.get('sponsor_id') and vals['sponsor_id'] != context_sponsor.id:
            raise ValidationError(_(
                'This lead belongs to %(sponsor)s. '
                'To use a different sponsor, open that sponsor lead menu.'
            ) % {'sponsor': context_sponsor.display_name})

        if 'event_id' in vals and 'sponsor_id' not in vals:
            event = self.env['vac.event'].browse(vals['event_id'])
            if (
                context_sponsor
                and event.sponsor_id
                and event.sponsor_id != context_sponsor
            ):
                raise ValidationError(_(
                    'You can only select events for %(sponsor)s here. '
                    'To use a different sponsor, open that sponsor lead menu.'
                ) % {'sponsor': context_sponsor.display_name})
            vals['sponsor_id'] = event.sponsor_id.id if event else False
        elif vals.get('sponsor_id') and not context_sponsor:
            for lead in self:
                event_sponsor = lead.event_id.sponsor_id
                if event_sponsor and vals['sponsor_id'] != event_sponsor.id:
                    raise ValidationError(_(
                        'This event lead belongs to %(sponsor)s because '
                        'that sponsor is set on the selected event.'
                    ) % {'sponsor': event_sponsor.display_name})
                # Guard: if the lead already has a sponsor (but no event sponsor
                # constraint), warn that changing sponsor is not allowed.
                if (
                    not event_sponsor
                    and lead.sponsor_id
                    and vals['sponsor_id'] != lead.sponsor_id.id
                ):
                    raise ValidationError(_(
                        'This lead is linked to sponsor "%(current)s". '
                        'Sponsor-based leads cannot be reassigned to a different sponsor '
                        'and will not be charged to another sponsor. '
                        'To manage this lead under a different sponsor, '
                        'please open that sponsor\'s lead menu.'
                    ) % {'current': lead.sponsor_id.display_name})
        elif context_sponsor:
            vals['sponsor_id'] = context_sponsor.id

        is_becoming_social = (
            vals.get('social_fb_id')
            or vals.get('social_ig_id')
            or vals.get('social_office_id')
            or vals.get('platform') in ('facebook', 'instagram', 'office')
        )
        if is_becoming_social and not vals.get('social_stage_id'):
            needs_stage = self.filtered(lambda l: not l.social_stage_id)
            if needs_stage:
                first_stage = self._first_social_stage()
                if first_stage:
                    vals['social_stage_id'] = first_stage.id
        return super().write(vals)

    @api.model
    def _fix_null_social_stages(self):
        first_stage = self._first_social_stage()
        if not first_stage:
            return
        leads = self.search([
            '|', '|', '|',
                ('social_fb_id', '!=', False),
                ('social_ig_id', '!=', False),
                ('social_office_id', '!=', False),
                ('platform', 'in', ['facebook', 'instagram', 'office']),
            ('social_stage_id', '=', False),
        ])
        if leads:
            leads.write({'social_stage_id': first_stage.id})

    # ── Validation ────────────────────────────────────────────────────────────

    @api.constrains('email')
    def _check_email_format(self):
        """Validate email format."""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        for lead in self:
            if lead.email and not re.match(email_regex, lead.email):
                raise ValidationError(f'Invalid email format: {lead.email}')

    @api.constrains('mobile')
    def _check_mobile_format(self):
        """Mobile number validation removed — accept any format."""

    @api.constrains('birthday')
    def _check_birthday(self):
        """Ensure birthday is not in the future."""
        for lead in self:
            if lead.birthday and lead.birthday > fields.Date.today():
                raise ValidationError('Birth date cannot be in the future!')

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_assign_to_me(self):
        self.ensure_one()
        self.bam_user_id = self.env.user

    def action_mark_converted(self):
        self.ensure_one()
        converted_stage = self.env['vac.event.lead.stage'].search(
            [('name', '=', 'Converted')], limit=1)
        if converted_stage:
            self.stage_id = converted_stage.id

    def action_mark_lost(self):
        self.ensure_one()
        lost_stage = self.env['vac.event.lead.stage'].search(
            [('name', '=', 'Lost')], limit=1)
        if lost_stage:
            self.stage_id = lost_stage.id
