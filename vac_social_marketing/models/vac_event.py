# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from odoo.exceptions import ValidationError
import pytz

def _tz_get(self):
    return [(tz, tz) for tz in sorted(pytz.all_timezones)]


class VacEvent(models.Model):
    _name = 'vac.event'
    _description = 'VAC Marketing Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'title_name'
    _order = 'date_begin desc, id desc'

    # ── Basic Information ─────────────────────────────────────────────────────

    title_name = fields.Char(
        string='Event Title',
        required=True,
        tracking=True,
        help='Name of the marketing event'
    )

    organizer_id = fields.Many2one(
        'res.company',
        string='Organizer',
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
        ondelete='restrict',
        help='Company organizing the event'
    )

    company_display_name = fields.Char(
        string='Company',
        compute='_compute_company_display_name',
        store=False,
    )

    @api.depends('organizer_id')
    def _compute_company_display_name(self):
        for rec in self:
            rec.company_display_name = rec.organizer_id.name or ''

    # ── Planned Date (start → end) ────────────────────────────────────────────

    date_begin = fields.Datetime(
        string='Planned Date',
        required=True,
        tracking=True,
        help='Planned start date & time of the event',
    )

    date_end = fields.Datetime(
        string='End Date',
        required=True,
        tracking=True,
        help='Planned end date & time of the event',
    )

    # Convenience date kept for any code/views that still reference `date`
    date = fields.Date(
        string='Event Date',
        compute='_compute_date',
        store=True,
        help='Calendar date derived from Start Date',
    )

    # ── Registration Fields ───────────────────────────────────────────────────

    registration_field_ids = fields.One2many(
        'vac.event.registration.field',
        'event_id',
        string='Custom Registration Fields',
        help='Extra fields shown on the public event registration form',
    )

    # ── Badge background ──────────────────────────────────────────────────────

    badge_background = fields.Binary(
        string='Badge Background',
        attachment=True,
        help='Upload an image to use as the badge background for this event'
    )
    badge_background_filename = fields.Char(string='Badge Background Filename')

    # ── Cover Photo ───────────────────────────────────────────────────────────

    cover_photo = fields.Image(
        string='Cover Photo',
        attachment=True,
        max_width=1920,
        max_height=1080,
        help='Upload a cover/banner image for this event. '
             'Recommended size: 1200 × 400 px.'
    )

    # ── Other Fields ──────────────────────────────────────────────────────────

    timezone_id = fields.Selection(
        _tz_get,
        string='Timezone',
        default=lambda self: self.env.user.tz or 'UTC',
        required=True,
        help='Timezone for the event'
    )

    venue = fields.Text(
        string='Venue',
        tracking=True,
        help='Physical or virtual location of the event'
    )

    description = fields.Text(
        string='Description',
        help='Detailed description of the event'
    )

    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template (legacy)',
        ondelete='set null',
        tracking=True,
        domain="[('model', '=', 'vac.event.lead')]",
        help='Legacy: select a raw mail.template. Prefer "Email Template Builder" below.',
    )

    email_config_id = fields.Many2one(
        'vac.mail.template.config',
        string='Event Confirmation Email template',
        ondelete='set null',
        tracking=True,
        help=(
            'Choose a template built in Configuration → Email Templates. '
            'The registration confirmation email will use that template\'s '
            'header, body and footer exactly. Leave empty to use the default email.'
        ),
    )

    responsible_user_ids = fields.Many2many(
        'res.users',
        'vac_event_user_rel',
        'event_id',
        'user_id',
        string='Responsible Users',
        tracking=True,
        help='Team members responsible for this event'
    )

    sponsor_id = fields.Many2one(
        'vac.sponsor',
        string='Sponsor',
        tracking=True,
        help='Sponsor for this event',
    )

    stage_id = fields.Many2one(
        'vac.event.stage',
        string='Stage',
        required=True,
        tracking=True,
        group_expand='_read_group_stage_ids',
        ondelete='restrict',
        help='Current stage of the event',
        index=True,
        copy=False
    )

    published = fields.Boolean(
        string='Published',
        default=False,
        tracking=True,
        help='Event is published and visible to public'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Archive events instead of deleting them'
    )

    lead_ids = fields.One2many(
        'vac.event.lead',
        'event_id',
        string='Leads',
        context={'active_test': False},
        help='All leads registered for this event'
    )

    assignment_ids = fields.One2many(
        'vac.event.lead.assignment',
        'event_id',
        string='Lead Assignments',
        context={'active_test': False},
        help='BAM user assignments for this event'
    )

    event_link = fields.Char(
        string='Event Link',
        compute='_compute_event_link',
        help='Auto-generated shareable URL for event registration'
    )

    qr_code = fields.Binary(
        string='QR Code',
        compute='_compute_qr_code',
        store=True,
        help='Auto-generated QR code encoding the event registration link'
    )

    # ── Smart Button Fields ───────────────────────────────────────────────────

    total_lead_count = fields.Integer(
        string='Total Leads',
        compute='_compute_total_lead_count',
        help='Total number of leads for this event (all stages, including archived)'
    )

    signed_lead_count = fields.Integer(
        string='Signed Leads',
        compute='_compute_signed_lead_count',
        help='Number of leads in the signed stage'
    )

    show_lead_generation = fields.Boolean(
        string='Show Lead Generation',
        compute='_compute_signed_lead_count',
        help='Show Lead Generation button only when signed stage has at least one lead'
    )

    assigned_lead_count = fields.Integer(
        string='Assigned Leads',
        compute='_compute_assigned_lead_count',
        help='Total number of leads assigned to BAM users'
    )

    show_assigned_leads = fields.Boolean(
        string='Show Assigned Leads',
        compute='_compute_assigned_lead_count',
        help='Show Assigned Leads button only when at least one lead is assigned'
    )

    crm_sent_lead_count = fields.Integer(
        string='Sent to CRM',
        compute='_compute_crm_sent_lead_count',
        help='Total number of leads from this event that have a CRM opportunity created'
    )

    show_crm_sent_leads = fields.Boolean(
        string='Show Sent to CRM',
        compute='_compute_crm_sent_lead_count',
        help='Show the "Sent to CRM" button only when at least one lead has been sent to CRM'
    )

    # ── Computed ──────────────────────────────────────────────────────────────

    @api.depends('date_begin')
    def _compute_date(self):
        for event in self:
            event.date = event.date_begin.date() if event.date_begin else False

    def _compute_event_link(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        for event in self:
            if event.id and event.title_name:
                import re
                slug = re.sub(r'[^a-z0-9]+', '-', (event.title_name or '').lower()).strip('-')
                event.event_link = f"{base_url}/event/invite/{slug}"
            elif event.id:
                event.event_link = f"{base_url}/event/invite/{event.id}"
            else:
                event.event_link = False

    @api.depends('event_link', 'title_name', 'date_begin', 'venue')
    def _compute_qr_code(self):
        try:
            import qrcode
            from io import BytesIO
            import base64
            has_qrcode = True
        except ImportError:
            has_qrcode = False

        for event in self:
            if not has_qrcode or not event.id:
                event.qr_code = False
                continue

            # Build the data string for the QR
            link = event.event_link or ''
            title = event.title_name or ''
            date = str(event.date_begin.date()) if event.date_begin else ''
            venue = event.venue or ''

            qr_data = link if link else (
                f"Event: {title} | Date: {date} | Venue: {venue}"
            )

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color='black', back_color='white')
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            event.qr_code = base64.b64encode(buffer.getvalue())

    def action_copy_qr_with_name(self):
        """Return a client action to copy the QR code (with event name) to clipboard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'vac_social_marketing.copy_qr_with_name',
            'params': {
                'qr_code': self.qr_code.decode() if self.qr_code else '',
                'record_name': self.title_name or '',
            },
        }

    @api.depends('lead_ids', 'lead_ids.active')
    def _compute_total_lead_count(self):
        for event in self:
            if not event.id:
                event.total_lead_count = 0
                continue
            event.total_lead_count = self.env['vac.event.lead'].with_context(
                active_test=False
            ).search_count([('event_id', '=', event.id)])

    @api.depends('lead_ids', 'lead_ids.stage_id', 'lead_ids.stage_id.is_signed', 'lead_ids.active')
    def _compute_signed_lead_count(self):
        for event in self:
            if not event.id:
                event.signed_lead_count = 0
                event.show_lead_generation = False
                continue
            signed_stage = self.env['vac.event.lead.stage'].search(
                [('is_signed', '=', True)], limit=1
            )
            if signed_stage:
                count = self.env['vac.event.lead'].search_count([
                    ('event_id', '=', event.id),
                    ('stage_id', '=', signed_stage.id),
                    ('active',   '=', True),
                ])
                event.signed_lead_count = count
                event.show_lead_generation = count > 0
            else:
                event.signed_lead_count = 0
                event.show_lead_generation = False

    @api.depends('assignment_ids', 'assignment_ids.lead_ids',
                 'assignment_ids.lead_ids.bam_user_id', 'assignment_ids.count',
                 'assignment_ids.lead_ids.crm_lead_id')
    def _compute_assigned_lead_count(self):
        for event in self:
            if not event.id:
                event.assigned_lead_count = 0
                event.show_assigned_leads = False
                continue
            total = sum(event.assignment_ids.mapped('count'))
            event.assigned_lead_count = total
            # Tab visible when at least one lead has a BAM user assigned
            # AND has been distributed to CRM (crm_lead_id is set)
            all_leads = event.assignment_ids.mapped('lead_ids')
            event.show_assigned_leads = any(
                lead.bam_user_id and lead.crm_lead_id
                for lead in all_leads
            )

    @api.depends('lead_ids.crm_lead_id', 'lead_ids.active')
    def _compute_crm_sent_lead_count(self):
        for event in self:
            if not event.id:
                event.crm_sent_lead_count = 0
                event.show_crm_sent_leads = False
                continue
            count = self.env['vac.event.lead'].with_context(
                active_test=False
            ).search_count([
                ('event_id', '=', event.id),
                ('crm_lead_id', '!=', False),
            ])
            event.crm_sent_lead_count = count
            event.show_crm_sent_leads = count > 0

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains('date_begin', 'date_end')
    def _check_event_dates(self):
        for event in self:
            if event.date_begin and event.date_end:
                if event.date_end <= event.date_begin:
                    raise ValidationError('End Date must be after Start Date!')
            if event.date_begin and event.date_begin.date() < fields.Date.today():
                raise ValidationError('Start date cannot be in the past!')

    # ── Sponsor lock ─────────────────────────────────────────────────────────

    @api.onchange('sponsor_id')
    def _onchange_sponsor_id(self):
        """Warn and revert if user tries to set a different sponsor than the
        one this menu/action was opened for."""
        expected_name = self.env.context.get('default_sponsor_name')
        if not expected_name:
            return  # opened from All Events — no restriction
        if self.sponsor_id and self.sponsor_id.name != expected_name:
            # Revert to the correct sponsor
            correct = self.env['vac.sponsor'].search(
                [('name', '=', expected_name)], limit=1)
            self.sponsor_id = correct
            return {
                'warning': {
                    'title': 'Sponsor cannot be changed',
                    'message': (
                        f'This event is under "{expected_name}".\n'
                        f'You cannot assign a different sponsor here.\n'
                        f"To use a different sponsor, open that sponsor's menu."
                    ),
                }
            }

    # ── Default / Group expand ────────────────────────────────────────────────

    @api.model
    def default_get(self, fields_list):
        res = super(VacEvent, self).default_get(fields_list)

        # ── Auto-set Draft stage ──────────────────────────────────────────────
        if 'stage_id' in fields_list and 'stage_id' not in res:
            stage = self.env['vac.event.stage'].search(
                [('name', '=', 'Draft')], limit=1)
            if not stage:
                stage = self.env['vac.event.stage'].search(
                    [], order='sequence, name', limit=1)
            if stage:
                res['stage_id'] = stage.id

        # ── Auto-populate standard registration fields ────────────────────────
        # Fetches live branch/service names so the dropdown is always current.
        if 'registration_field_ids' in fields_list and 'registration_field_ids' not in res:
            services = self.env['branch.service'].search([], order='name')
            branch_options = '\n'.join(s.name for s in services if s.name)

            DEFAULT_FIELDS = [
                # (seq, label,                                  type,      maps_to,         required, select_options)
                (5,   'Are you a current client of VAC?',       'checkbox', 'none',          False, False),
                (8,   'Are you a veteran?',                     'checkbox', 'none',          False, False),
                (10,  'First Name',                             'text',     'name',          False, False),
                (20,  'Last Name',                              'text',     'name',          False, False),
                (30,  'Phone Number',                           'number',   'mobile',        False, False),
                (40,  'WhatsApp Number',                        'number',   'none',          False, False),
                (50,  'Email Address',                          'email',    'email',         False, False),
                (60,  'Date of Birth',                          'date',     'birthday',      False, False),
                (70,  'Current Physical Address',               'textarea', 'none',          False, False),
                (80,  'Are you bringing a plus one?',           'checkbox', 'none',          False, False),
                (90,  'Branch of Service',                      'select',   'branch_service', True, branch_options),
                (100, 'Current VA Disability Rating',           'number',   'none',          False, False),
                (110, 'Do you have a copy of your DD214?',      'checkbox', 'none',          False, False),
                (120, 'Do you have access to your DD214?',      'checkbox', 'none',          False, False),
            ]

            res['registration_field_ids'] = [
                Command.create({
                    'sequence':       seq,
                    'label':          label,
                    'field_type':     ftype,
                    'maps_to':        maps_to,
                    'is_required':    required,
                    'select_options': options or False,
                })
                for seq, label, ftype, maps_to, required, options in DEFAULT_FIELDS
            ]

        # ── Auto-set sponsor from menu context ──────────────────────────────
        sponsor_name = self.env.context.get('default_sponsor_name')
        if sponsor_name and 'sponsor_id' in fields_list and 'sponsor_id' not in res:
            sponsor = self.env['vac.sponsor'].search(
                [('name', '=', sponsor_name)], limit=1)
            if sponsor:
                res['sponsor_id'] = sponsor.id

        return res

    def create(self, vals_list):
        # Normalize input: some callers may still pass a single dict
        # instead of a list of dicts (old single-record calling style).
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        # ── Ensure sponsor_id is set from menu context if not already provided ─
        for vals in vals_list:
            if not vals.get('sponsor_id'):
                sponsor_name = self.env.context.get('default_sponsor_name')
                if sponsor_name:
                    sponsor = self.env['vac.sponsor'].search(
                        [('name', '=', sponsor_name)], limit=1)
                    if sponsor:
                        vals['sponsor_id'] = sponsor.id
        return super().create(vals_list)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['vac.event.stage'].search([], order='sequence, name')

    # ── Frontend 10-second poll endpoint ─────────────────────────────────────

    @api.model
    def action_auto_stage_poll(self):
        """Called by the JS polling service every 10 seconds.
        Checks ALL active events and moves any whose dates now place them
        in Ongoing or Completed.
        Returns True when at least one record was actually changed so the
        frontend knows to refresh the view; False means nothing to redraw.
        """
        now = fields.Datetime.now()
        ongoing_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Ongoing')], limit=1)
        completed_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Completed')], limit=1)

        active_recs = self.with_context(_vac_stage_updating=True).search(
            [('active', '=', True)])
        changed = False

        to_ongoing = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and r.stage_id != ongoing_stage
        )
        if to_ongoing and ongoing_stage:
            to_ongoing.write({'published': True, 'stage_id': ongoing_stage.id})
            changed = True

        to_complete = active_recs.filtered(
            lambda r: r.date_end and r.date_end <= now
            and r.stage_id != completed_stage
        )
        if to_complete and completed_stage:
            to_complete.write({'published': False, 'stage_id': completed_stage.id})
            changed = True

        return changed

    # ── Instant stage update on read ──────────────────────────────────────────

    def _auto_update_stage(self):
        """Check dates vs now and immediately correct stage for self.
        Called on every read so users always see the correct stage without
        waiting for the cron to run.
        """
        now = fields.Datetime.now()
        ongoing_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Ongoing')], limit=1)
        completed_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Completed')], limit=1)

        active_recs = self.filtered('active')

        # Records whose start has passed but end hasn't → Ongoing
        to_ongoing = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and r.stage_id != ongoing_stage
        )
        if to_ongoing and ongoing_stage:
            to_ongoing.with_context(_vac_stage_updating=True).write(
                {'published': True, 'stage_id': ongoing_stage.id})

        # Records whose end has passed → Completed
        to_complete = active_recs.filtered(
            lambda r: r.date_end and r.date_end <= now
            and r.stage_id != completed_stage
        )
        if to_complete and completed_stage:
            to_complete.with_context(_vac_stage_updating=True).write(
                {'published': False, 'stage_id': completed_stage.id})

    def read(self, fields=None, load='_classic_read'):
        """Auto-correct stage before returning record data to the UI."""
        if not self.env.context.get('_vac_stage_updating'):
            self._auto_update_stage()
        return super().read(fields=fields, load=load)

    # ── Auto-publish cron ─────────────────────────────────────────────────────

    @api.model
    def _cron_auto_publish(self):
        now = fields.Datetime.now()

        # Fetch stages once
        published_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Published')], limit=1)
        ongoing_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Ongoing')], limit=1)
        completed_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Completed')], limit=1)

        # ── Ongoing: today falls between date_begin and date_end ─────────────
        to_ongoing = self.search([
            ('active',     '=', True),
            ('date_begin', '<=', now),
            ('date_end',   '>',  now),
        ])
        if to_ongoing and ongoing_stage:
            to_ongoing.write({'published': True, 'stage_id': ongoing_stage.id})

        # ── Completed: date_end has passed ───────────────────────────────────
        to_complete = self.search([
            ('active',   '=', True),
            ('date_end', '<=', now),
        ])
        if to_complete and completed_stage:
            to_complete.write({'published': False, 'stage_id': completed_stage.id})

        # ── Published: future events that are manually published ─────────────
        to_publish = self.search([
            ('active',     '=', True),
            ('published',  '=', True),
            ('date_begin', '>',  now),
        ])
        if to_publish and published_stage:
            # Only move to Published stage if not already in a further stage
            for ev in to_publish:
                if ev.stage_id not in (ongoing_stage, completed_stage):
                    ev.write({'stage_id': published_stage.id})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_published(self):
        return True

    def website_publish_button(self):
        self.ensure_one()
        # ── Validate required fields before allowing publish ──────────────────
        if not self.published:  # Only validate when trying to publish
            missing = []
            if not self.title_name:
                missing.append('Event Title')
            if not self.date_begin:
                missing.append('Planned Date')
            if not self.date_end:
                missing.append('End Date')
            if missing:
                raise ValidationError(
                    'Please fill in the following required fields before publishing:\n\u2022 '
                    + '\n\u2022 '.join(missing)
                )
        new_published = not self.published
        stage_name = 'Published' if new_published else 'Draft'
        stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', stage_name)], limit=1)
        vals = {'published': new_published}
        if stage:
            vals['stage_id'] = stage.id
        self.write(vals)
        return False

    def write(self, vals):
        # ── 0. Validate required fields before allowing publish ───────────────
        if vals.get('published') is True and not self.env.context.get('_vac_stage_updating'):
            for rec in self:
                missing = []
                title_name = vals.get('title_name', rec.title_name)
                date_begin = vals.get('date_begin', rec.date_begin)
                date_end = vals.get('date_end', rec.date_end)
                if not title_name:
                    missing.append('Event Title')
                if not date_begin:
                    missing.append('Planned Date')
                if not date_end:
                    missing.append('End Date')
                if missing:
                    raise ValidationError(
                        'Please fill in the following required fields before publishing:\n\u2022 '
                        + '\n\u2022 '.join(missing)
                    )

        # ── 1. Sync published → stage_id (button click / toggle) ─────────────
        #    If only `published` is being changed, auto-move to the matching stage.
        if 'published' in vals and 'stage_id' not in vals:
            is_published = vals['published']
            if is_published:
                stage_to_set = self.env['vac.event.stage'].search(
                    [('name', 'ilike', 'Published')], limit=1
                )
            else:
                stage_to_set = self.env['vac.event.stage'].search(
                    [('name', 'ilike', 'Draft')], limit=1
                )
            if stage_to_set:
                vals['stage_id'] = stage_to_set.id

        # ── 2. Sync stage_id → published (statusbar click) ───────────────────
        #    If only `stage_id` is being changed, auto-update `published` based
        #    on the stage name — consistent with how website_publish_button()
        #    and the cron already look up stages by name.
        #    Published / Ongoing → True  |  Draft / Completed / Cancelled → False
        if 'stage_id' in vals and 'published' not in vals:
            stage = self.env['vac.event.stage'].browse(vals['stage_id'])
            if stage.exists():
                stage_name_lower = (stage.name or '').lower().strip()
                vals['published'] = (
                    'published' in stage_name_lower
                    or 'ongoing' in stage_name_lower
                )

        return super().write(vals)

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_view_all_leads(self):
        self.ensure_one()
        return {
            'name':      f'Leads — {self.title_name}',
            'type':      'ir.actions.act_window',
            'res_model': 'vac.event.lead',
            'view_mode': 'list,kanban,form',
            'domain':    [('event_id', '=', self.id)],
            'context':   {
                'default_event_id': self.id,
                'active_test':      False,
                'group_by':         ['stage_id'],
            },
        }

    def action_lead_generation(self):
        self.ensure_one()
        signed_stage = self.env['vac.event.lead.stage'].search(
            [('is_signed', '=', True)], limit=1)
        if not signed_stage:
            return {
                'type': 'ir.actions.client',
                'tag':  'display_notification',
                'params': {
                    'title':   'No Signed Stage',
                    'message': 'Please configure a signed stage first.',
                    'type':    'warning',
                },
            }
        if self.signed_lead_count == 0:
            return {
                'type': 'ir.actions.client',
                'tag':  'display_notification',
                'params': {
                    'title':   'No Signed Leads',
                    'message': 'There are no leads in the signed stage.',
                    'type':    'warning',
                },
            }
        return {
            'name':      'Lead Generation',
            'type':      'ir.actions.act_window',
            'res_model': 'vac.event.lead.generation.wizard',
            'view_mode': 'form',
            'target':    'new',
            'context': {
                'default_event_id':           self.id,
                'default_total_signed_leads': self.signed_lead_count,
            },
        }

    def action_view_assigned_leads(self):
        self.ensure_one()
        lead_ids = []
        for assignment in self.assignment_ids:
            lead_ids.extend(assignment.lead_ids.ids)
        lead_ids = list(set(lead_ids))
        if not lead_ids:
            return {
                'type': 'ir.actions.client',
                'tag':  'display_notification',
                'params': {
                    'title':   'No Assigned Leads',
                    'message': 'There are no leads assigned to BAM users yet.',
                    'type':    'warning',
                },
            }
        return {
            'name':      f'Assigned Leads — {self.title_name}',
            'type':      'ir.actions.act_window',
            'res_model': 'vac.event.lead',
            'view_mode': 'kanban,list,form',
            'domain':    [('id', 'in', lead_ids)],
            'context':   {
                'default_event_id': self.id,
                'active_test':      False,
                'group_by':         ['stage_id'],
            },
        }

    def action_view_crm_sent_leads(self):
        self.ensure_one()
        lead_ids = self.env['vac.event.lead'].with_context(
            active_test=False
        ).search([
            ('event_id', '=', self.id),
            ('crm_lead_id', '!=', False),
        ]).ids
        if not lead_ids:
            return {
                'type': 'ir.actions.client',
                'tag':  'display_notification',
                'params': {
                    'title':   'No Leads Sent to CRM',
                    'message': 'No leads from this event have been sent to CRM yet.',
                    'type':    'warning',
                },
            }
        return {
            'name':      f'Sent to CRM — {self.title_name}',
            'type':      'ir.actions.act_window',
            'res_model': 'vac.event.lead',
            'view_mode': 'list,kanban,form',
            'domain':    [('id', 'in', lead_ids)],
            'context':   {
                'default_event_id': self.id,
                'active_test':      False,
                'group_by':         ['bam_user_id'],
            },
        }

    def action_preview(self):
        """Open a preview wizard showing event details + registration form."""
        self.ensure_one()
        return {
            'name': 'Event Preview',
            'type': 'ir.actions.act_window',
            'res_model': 'vac.event.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_event_id': self.id,
                'dialog_size': 'extra-large',
            },
        }

    def action_invite(self):
        self.ensure_one()
        return {
            'name':      'Share Event Link',
            'type':      'ir.actions.act_window',
            'res_model': 'vac.event.invite.wizard',
            'view_mode': 'form',
            'target':    'new',
            'context': {
                'default_event_id': self.id,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────

class VacEventLeadAssignment(models.Model):
    _name = 'vac.event.lead.assignment'
    _description = 'Event Lead Assignment'
    _order = 'sequence, id'

    event_id = fields.Many2one(
        'vac.event', string='Event', required=True,
        ondelete='cascade', help='The event for which leads are assigned'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Many2one(
        'res.users', string='BAM User', required=True,
        domain=[('share', '=', False)], help='BAM user assigned to leads'
    )
    count = fields.Integer(
        string='Assigned Count', required=True, default=0,
        help='Number of leads assigned to this BAM user'
    )
    lead_ids = fields.Many2many(
        'vac.event.lead', 'vac_assignment_lead_rel',
        'assignment_id', 'lead_id',
        string='Leads', context={'active_test': False},
        help='Leads assigned to this BAM user'
    )

    @api.constrains('count')
    def _check_count(self):
        for record in self:
            if record.count < 0:
                raise ValidationError('Count cannot be negative!')


# ─────────────────────────────────────────────────────────────────────────────

class VacEventRegistrationField(models.Model):
    _name        = 'vac.event.registration.field'
    _description = 'Event Registration Field'
    _order       = 'sequence, id'

    sequence = fields.Integer(default=10)
    event_id = fields.Many2one(
        'vac.event', string='Event', required=True, ondelete='cascade')
    label = fields.Char(
        string='Field Label', required=True,
        help='Label shown to the registrant (e.g. "Full Name")',
    )
    field_type = fields.Selection(
        selection=[
            ('text',     'Short Text (single line)'),
            ('textarea', 'Long Text (multi-line)'),
            ('number',   'Number'),
            ('email',    'Email'),
            ('tel',      'Phone / Mobile'),
            ('date',     'Date'),
            ('select',   'Dropdown (options below)'),
            ('checkbox', 'Checkbox (yes/no)'),
        ],
        string='Field Type', required=True, default='text',
    )

    # ─── UPDATED: added branch_service option ────────────────────────────────
    maps_to = fields.Selection(
        selection=[
            ('none',           'Custom (stored as extra data)'),
            ('name',           'Lead → Full Name'),
            ('first_name',     'Lead → First Name'),
            ('last_name',      'Lead → Last Name'),
            ('email',          'Lead → Email'),
            ('mobile',         'Lead → Mobile'),
            ('birthday',       'Lead → Date of Birth'),
            ('ssn',            'Lead → SSN / ID Number'),
            ('notes',          'Lead → Notes'),
            ('branch_service', 'Lead → Branch / Service'),  # ← NEW
        ],
        string='Maps To', default='none', required=True,
    )

    placeholder    = fields.Char(string='Placeholder')
    is_required    = fields.Boolean(string='Required', default=False)
    select_options = fields.Text(string='Dropdown Options')
    select_options_count = fields.Integer(
        string='No. of Options', compute='_compute_select_options_count')
    active = fields.Boolean(default=True)

    # ── Computed ──────────────────────────────────────────────────────────────

    @api.depends('select_options')
    def _compute_select_options_count(self):
        for rec in self:
            rec.select_options_count = len(rec.get_select_options_list())

    # ── Onchange ──────────────────────────────────────────────────────────────

    # ─── NEW ─────────────────────────────────────────────────────────────────
    @api.onchange('maps_to')
    def _onchange_maps_to(self):
        """
        When the admin selects 'Lead → Branch / Service':
          • Force field_type → 'select' so a dropdown renders on the form.
          • Snapshot current branch.service names into select_options so the
            constraint is satisfied and an admin preview is available.
        When switching away, clear the auto-generated options.
        """
        if self.maps_to == 'branch_service':
            self.field_type = 'select'
            services = self.env['branch.service'].search([], order='name')
            self.select_options = '\n'.join(name for name in services.mapped('name') if name)
        else:
            if self.field_type == 'select':
                self.select_options = False

    @api.onchange('field_type')
    def _onchange_field_type(self):
        if self.field_type != 'select':
            self.select_options = False

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains('field_type', 'select_options')
    def _check_select_options(self):
        for rec in self:
            # branch_service fields always get their options from the DB at
            # render time — no stored options required.
            if rec.maps_to == 'branch_service':
                continue
            if rec.field_type == 'select' and not rec.get_select_options_list():
                raise ValidationError(
                    f'Field "{rec.label}": '
                    'You must provide at least one dropdown option.'
                )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_select_options_list(self):
        """Return cleaned list of option strings (strips blank lines)."""
        self.ensure_one()
        if not self.select_options:
            return []
        return [o.strip() for o in self.select_options.splitlines() if o.strip()]

    # ─── NEW ─────────────────────────────────────────────────────────────────
    def get_branch_service_options(self):
        """
        Return the list of branch/service option strings for QWeb rendering.

        Reads directly from the stored select_options text (one per line) so
        that any additions or deletions made by the admin in the registration
        field config are immediately reflected in the event preview template.

        Template usage:

            <t t-foreach="field.get_branch_service_options()" t-as="opt">
                <option t-att-value="opt" t-esc="opt"/>
            </t>
        """
        self.ensure_one()
        if self.maps_to == 'branch_service':
            return self.get_select_options_list()
        return []
