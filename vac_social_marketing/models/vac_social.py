from odoo import models, fields, api, Command
from odoo.exceptions import ValidationError
import pytz
import re
import unicodedata


def _make_slug(title):
    """Convert a campaign title to a URL-safe slug."""
    if not title:
        return ''
    text = unicodedata.normalize('NFKD', title)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def _tz_get(self):
    return [(tz, tz) for tz in sorted(pytz.all_timezones)]


class VacSocialMixin(models.AbstractModel):
    _name = 'vac.social.mixin'
    _description = 'VAC Social Mixin'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Basic Information ─────────────────────────────────────────────────────

    title = fields.Char(
        string='Title',
        required=True,
        tracking=True,
        help='Name of the social campaign'
    )

    organizer_id = fields.Many2one(
        'res.company',
        string='Organizer',
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
        ondelete='restrict',
        help='Company organizing the campaign'
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
        string='Campaign Start Date',
        required=True,
        tracking=True,
        help='Planned start date & time of the campaign',
    )

    date_end = fields.Datetime(
        string='Campaign End Date',
        required=True,
        tracking=True,
        help='Planned end date & time of the campaign',
    )

    # ── Badge background ──────────────────────────────────────────────────────

    badge_background = fields.Binary(
        string='Badge Background',
        attachment=True,
        help='Upload an image to use as the badge background for this campaign'
    )
    badge_background_filename = fields.Char(string='Badge Background Filename')

    # ── Cover Photo ───────────────────────────────────────────────────────────

    cover_photo = fields.Image(
        string='Cover Photo',
        attachment=True,
        max_width=1920,
        max_height=1080,
        help='Upload a cover/banner image for this campaign. '
             'Recommended size: 1200 × 400 px.'
    )

    # ── Other Fields ──────────────────────────────────────────────────────────

    timezone_id = fields.Selection(
        _tz_get,
        string='Timezone',
        default=lambda self: self.env.user.tz or 'UTC',
        required=True,
        help='Timezone for the campaign'
    )

    description = fields.Html(
        string='Description',
        help='Detailed description of the campaign'
    )

    published = fields.Boolean(
        string='Published',
        default=False,
        tracking=True,
        help='Campaign is published and visible to public'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Archive campaigns instead of deleting them'
    )

    stage_id = fields.Many2one(
        'vac.event.stage',
        string='Stage',
        ondelete='restrict',
        tracking=True,
        group_expand='_read_group_stage_ids',
        help='Current lifecycle stage of the campaign'
    )

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['vac.event.stage'].search([], order='sequence, name')

    def write(self, vals):
        # ── 0. Validate required fields before allowing publish ───────────────
        if vals.get('published') is True and not self.env.context.get('_vac_stage_updating'):
            for rec in self:
                missing = []
                title = vals.get('title', rec.title)
                date_begin = vals.get('date_begin', rec.date_begin)
                date_end = vals.get('date_end', rec.date_end)
                if not title:
                    missing.append('Title')
                if not date_begin:
                    missing.append('Campaign Start Date')
                if not date_end:
                    missing.append('Campaign End Date')
                if missing:
                    raise ValidationError(
                        'Please fill in the following required fields before publishing:\n\u2022 '
                        + '\n\u2022 '.join(missing)
                    )

        # ── 1. Sync published → stage_id (button click / toggle) ─────────────
        #    If only `published` is being changed, auto-move to the matching stage.
        if 'published' in vals and 'stage_id' not in vals:
            stage_name = 'Published' if vals['published'] else 'Draft'
            stage = self.env['vac.event.stage'].search(
                [('name', 'ilike', stage_name)], limit=1)
            if stage:
                vals['stage_id'] = stage.id

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

        res = super().write(vals)

        # ── 3. Mirror publish change onto linked vac.event records ──────────
        if 'published' in vals:
            is_published = vals['published']
            published_stage = self.env['vac.event.stage'].search(
                [('name', 'ilike', 'Published')], limit=1)
            draft_stage = self.env['vac.event.stage'].search(
                [('name', 'ilike', 'Draft')], limit=1)
            for record in self:
                events = self.env['vac.event'].sudo().search([
                    ('title_name', '=', record.title),
                    ('active', '=', True),
                ])
                if events:
                    if is_published and published_stage:
                        events.write({'published': True, 'stage_id': published_stage.id})
                    elif not is_published and draft_stage:
                        events.write({'published': False, 'stage_id': draft_stage.id})
        return res

    def website_publish_button(self):
        self.ensure_one()
        # ── Validate required fields before allowing publish ──────────────────
        if not self.published:  # Only validate when trying to publish
            missing = []
            if not self.title:
                missing.append('Title')
            if not self.date_begin:
                missing.append('Campaign Start Date')
            if not self.date_end:
                missing.append('Campaign End Date')
            if missing:
                raise ValidationError(
                    'Please fill in the following required fields before publishing:\n• '
                    + '\n• '.join(missing)
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

    social_link = fields.Char(
        string='Campaign Link',
        compute='_compute_social_link',
        help='Auto-generated shareable URL for campaign registration'
    )

    slug = fields.Char(
        string='URL Slug',
        compute='_compute_slug',
        store=True,
        readonly=False,
        help='URL-friendly name derived from the campaign title, used in the shareable link.'
    )

    qr_code = fields.Binary(
        string='QR Code',
        compute='_compute_qr_code',
        store=True,
        help='Auto-generated QR code encoding the campaign registration link'
    )

    # ── Computed ──────────────────────────────────────────────────────────────

    def _get_social_url_prefix(self):
        raise NotImplementedError

    @api.depends('title')
    def _compute_slug(self):
        for rec in self:
            rec.slug = _make_slug(rec.title) if rec.title else ''

    def _compute_social_link(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.id:
                url_key = rec.slug if rec.slug else str(rec.id)
                rec.social_link = f"{base_url}/{self._get_social_url_prefix()}/invite/{url_key}"
            else:
                rec.social_link = False

    @api.depends('social_link')
    def _compute_qr_code(self):
        try:
            import qrcode
            from io import BytesIO
            import base64
            has_qrcode = True
        except ImportError:
            has_qrcode = False

        for rec in self:
            if not has_qrcode or not rec.id:
                rec.qr_code = False
                continue

            qr_data = rec.social_link or ''
            if not qr_data:
                rec.qr_code = False
                continue

            # QR visitors should see the registration form immediately, while
            # shared campaign links should continue to open the landing page.
            separator = '&' if '?' in qr_data else '?'
            qr_data = f'{qr_data}{separator}register=1'

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
            rec.qr_code = base64.b64encode(buffer.getvalue())

    def action_copy_qr_with_name(self):
        """Return a client action to copy the QR code (with campaign name) to clipboard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'vac_social_marketing.copy_qr_with_name',
            'params': {
                'qr_code': self.qr_code.decode() if self.qr_code else '',
                'record_name': self.title or '',
            },
        }

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains('date_begin', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_begin and rec.date_end:
                if rec.date_end <= rec.date_begin:
                    raise ValidationError('End Date must be after Start Date!')
            if rec.date_begin and rec.date_begin.date() < fields.Date.today():
                raise ValidationError('Start date cannot be in the past!')

    # ── Frontend 10-second poll endpoint ─────────────────────────────────────

    @api.model
    def action_auto_stage_poll(self):
        """Called by the JS polling service every 10 seconds.
        Checks ALL active records and moves any whose dates place them in
        Published, Ongoing, or Completed.
        Returns True when at least one record was actually changed so the
        frontend knows to refresh the view; False means nothing to redraw.
        """
        now = fields.Datetime.now()
        published_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Published')], limit=1)
        ongoing_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Ongoing')], limit=1)
        completed_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Completed')], limit=1)

        active_recs = self.with_context(_vac_stage_updating=True).search(
            [('active', '=', True)])
        changed = False

        # ── Step 1: Completed ─────────────────────────────────────────────────
        to_complete = active_recs.filtered(
            lambda r: r.date_end and r.date_end <= now
            and r.stage_id != completed_stage
        )
        if to_complete and completed_stage:
            to_complete.write({'published': False, 'stage_id': completed_stage.id})
            changed = True

        # ── Step 2: Ongoing ───────────────────────────────────────────────────
        to_ongoing = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and r.stage_id != ongoing_stage
        )
        if to_ongoing and ongoing_stage:
            to_ongoing.write({'published': True, 'stage_id': ongoing_stage.id})
            changed = True

        # ── Step 3: Auto-publish Draft campaigns whose start date arrived ─────
        to_auto_publish = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and not r.published
            and r.stage_id not in (ongoing_stage, completed_stage)
        )
        if to_auto_publish and published_stage:
            to_auto_publish.write({'published': True, 'stage_id': published_stage.id})
            changed = True

        # ── Step 4: Future manually-published → Published stage ───────────────
        to_published_stage = active_recs.filtered(
            lambda r: r.date_begin and r.date_begin > now
            and r.published
            and r.stage_id not in (ongoing_stage, completed_stage, published_stage)
        )
        if to_published_stage and published_stage:
            to_published_stage.write({'stage_id': published_stage.id})
            changed = True

        return changed

    # ── Instant stage update on read ──────────────────────────────────────────

    def _auto_update_stage(self):
        """Check dates vs now and immediately correct stage for self.
        Called on every read so users always see the correct stage without
        waiting for the cron to run.

        Stage flow:  Draft → Published → Ongoing → Completed
        """
        if not self.ids:
            return

        now = fields.Datetime.now()
        published_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Published')], limit=1)
        ongoing_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Ongoing')], limit=1)
        completed_stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Completed')], limit=1)

        # Use a domain-based search restricted to self.ids to avoid
        # triggering a raw field-fetch on records whose stage_id column
        # may not exist yet (prevents UndefinedColumn during upgrades).
        active_recs = self.search([('id', 'in', self.ids), ('active', '=', True)])

        # ── Step 1: Completed — end date has passed ───────────────────────────
        to_complete = active_recs.filtered(
            lambda r: r.date_end and r.date_end <= now
            and r.stage_id != completed_stage
        )
        if to_complete and completed_stage:
            to_complete.with_context(_vac_stage_updating=True).write(
                {'published': False, 'stage_id': completed_stage.id})

        # ── Step 2: Ongoing — within the start/end window ────────────────────
        to_ongoing = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and r.stage_id != ongoing_stage
        )
        if to_ongoing and ongoing_stage:
            to_ongoing.with_context(_vac_stage_updating=True).write(
                {'published': True, 'stage_id': ongoing_stage.id})

        # ── Step 3: Published — start date reached for Draft campaigns ────────
        #    A campaign saved as Draft (published=False) whose start date is
        #    today or in the past but whose end is still future should auto-move
        #    to Published before going Ongoing on next tick.
        to_publish = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and not r.published
            and r.stage_id not in (ongoing_stage, completed_stage)
        )
        if to_publish and published_stage:
            to_publish.with_context(_vac_stage_updating=True).write(
                {'published': True, 'stage_id': published_stage.id})

        # ── Step 4: Manually published future campaigns → Published stage ─────
        to_published_stage = active_recs.filtered(
            lambda r: r.date_begin and r.date_begin > now
            and r.published
            and r.stage_id not in (ongoing_stage, completed_stage, published_stage)
        )
        if to_published_stage and published_stage:
            to_published_stage.with_context(_vac_stage_updating=True).write(
                {'stage_id': published_stage.id})

    def read(self, fields=None, load='_classic_read'):
        """Auto-correct stage before returning record data to the UI."""
        if not self.env.context.get('_vac_stage_updating'):
            self._auto_update_stage()
        return super().read(fields=fields, load=load)

    # ── Auto-publish cron ─────────────────────────────────────────────────────

    @api.model
    def _cron_auto_publish(self):
        now = fields.Datetime.now()

        to_publish = self.search([
            ('active',     '=', True),
            ('published',  '=', False),
            ('date_begin', '<=', now),
            ('date_end',   '>',  now),
        ])
        if to_publish:
            to_publish.write({'published': True})

        to_unpublish = self.search([
            ('active',    '=', True),
            ('published', '=', True),
            ('date_end',  '<=', now),
        ])
        if to_unpublish:
            to_unpublish.write({'published': False})

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_share_link(self):
        self.ensure_one()
        return {
            'name':      'Share Campaign Link',
            'type':      'ir.actions.act_window',
            'res_model': 'vac.social.invite.wizard',
            'view_mode': 'form',
            'target':    'new',
            'context': {
                'default_title':        self.title,
                'default_social_link':  self.social_link,
                'default_source_model': self._name,   # e.g. 'vac.social.fb'
                'default_source_id':    self.id,      # needed to build QR image URL
            },
        }


# ═══════════════════════════════════════════════════════════════════
#  FACEBOOK
# ═══════════════════════════════════════════════════════════════════
class VacSocialFb(models.Model):
    _name = 'vac.social.fb'
    _description = 'VAC Social – Facebook'
    _inherit = 'vac.social.mixin'
    _rec_name = 'title'
    _order = 'date_begin desc, id desc'


    registration_field_ids = fields.One2many(
        'vac.social.fb.fields',
        'social_fb_id',
        string='Custom Registration Fields',
        help='Extra fields shown on the public campaign registration form',
    )

    lead_ids = fields.One2many(
        'vac.event.lead',
        'social_fb_id',
        string='Leads',
        help='Leads generated from this Facebook campaign',
    )

    lead_count = fields.Integer(
        string='Leads',
        compute='_compute_lead_count',
        store=True,
        help='Total number of leads from this Facebook campaign',
    )

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for rec in self:
            rec.lead_count = len(rec.lead_ids)

    def action_view_leads(self):
        self.ensure_one()
        first_stage = self.env['vac.social.lead.stage'].search(
            [], order='sequence, id', limit=1)
        return {
            'name': f'Leads — {self.title}',
            'type': 'ir.actions.act_window',
            'res_model': 'vac.event.lead',
            'view_mode': 'list,kanban,form',
            'views': [
                (self.env.ref('vac_social_marketing.vac_event_lead_view_social_list').id, 'list'),
                (self.env.ref('vac_social_marketing.vac_event_lead_view_social_kanban').id, 'kanban'),
                (self.env.ref('vac_social_marketing.vac_event_lead_view_form').id, 'form'),
            ],
            'domain': [('social_fb_id', '=', self.id)],
            'context': {
                'default_social_fb_id': self.id,
                'default_platform': 'facebook',
                'default_social_stage_id': first_stage.id if first_stage else False,
                'group_by': ['social_stage_id'],
            },
        }

    def _get_social_url_prefix(self):
        return 'social/fb'

    def action_preview(self):
        """Open a preview wizard for this Facebook campaign."""
        self.ensure_one()
        wizard = self.env['vac.social.preview.wizard'].create({
            'source_model': self._name,
            'source_id': self.id,
            'title': self.title,
            'social_link': self.social_link,

            'published': self.published,
        })
        return {
            'name': 'Campaign Preview',
            'type': 'ir.actions.act_window',
            'res_model': 'vac.social.preview.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'dialog_size': 'extra-large'},
        }


    def _cron_auto_stage(self):
        """Cron: auto-move Facebook campaigns through Draft → Published → Ongoing → Completed."""
        now = fields.Datetime.now()
        draft_stage     = self.env['vac.event.stage'].search([('name', 'ilike', 'Draft')],     limit=1)
        published_stage = self.env['vac.event.stage'].search([('name', 'ilike', 'Published')], limit=1)
        ongoing_stage   = self.env['vac.event.stage'].search([('name', 'ilike', 'Ongoing')],   limit=1)
        completed_stage = self.env['vac.event.stage'].search([('name', 'ilike', 'Completed')], limit=1)

        active_recs = self.with_context(_vac_stage_updating=True).search([('active', '=', True)])

        # ── Step 1: Completed — end date passed ──────────────────────────────
        to_complete = active_recs.filtered(
            lambda r: r.date_end and r.date_end <= now
            and r.stage_id != completed_stage
        )
        if to_complete and completed_stage:
            to_complete.write({'published': False, 'stage_id': completed_stage.id})

        # ── Step 2: Ongoing — within start/end window ─────────────────────────
        to_ongoing = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and r.stage_id != ongoing_stage
        )
        if to_ongoing and ongoing_stage:
            to_ongoing.write({'published': True, 'stage_id': ongoing_stage.id})

        # ── Step 3: Published — start date reached, not yet ongoing/completed ─
        #    Covers both manually-published AND auto-publish (published=False in Draft)
        to_publish = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end  # same window as ongoing — ongoing handles these
            # future-date campaigns that were manually published → move to Published stage
            or (r.date_begin and r.date_begin > now and r.published
                and r.stage_id not in (ongoing_stage, completed_stage))
        )
        # Draft campaigns whose start date has arrived but are still unpublished → auto-publish
        to_auto_publish = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and not r.published
            and r.stage_id not in (ongoing_stage, completed_stage)
        )
        if to_auto_publish and published_stage:
            to_auto_publish.write({'published': True, 'stage_id': published_stage.id})

        # Future manually-published campaigns → Published stage
        to_published_stage = active_recs.filtered(
            lambda r: r.date_begin and r.date_begin > now
            and r.published
            and r.stage_id not in (ongoing_stage, completed_stage, published_stage)
        )
        if to_published_stage and published_stage:
            to_published_stage.write({'stage_id': published_stage.id})

    # ── Auto-populate standard registration fields on New ────────────────────
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Auto-set Draft stage
        if 'stage_id' in fields_list and 'stage_id' not in res:
            stage = self.env['vac.event.stage'].search([('name', '=', 'Draft')], limit=1)
            if not stage:
                stage = self.env['vac.event.stage'].search([], order='sequence, name', limit=1)
            if stage:
                res['stage_id'] = stage.id
        if 'registration_field_ids' in fields_list and 'registration_field_ids' not in res:
            services = self.env['branch.service'].search([], order='name')
            branch_options = '\n'.join(s.name for s in services if s.name)

            DEFAULT_FIELDS = [
                # (seq, label,                               type,       maps_to,          required, select_options)
                (10,  'Are you a US Veteran?',               'checkbox', 'none',           False, False),
                (20,  'First Name',                          'text',     'name',           False, False),
                (30,  'Last Name',                           'text',     'name',           False, False),
                (40,  'Branch of Service',                   'select',   'branch_service', True,  branch_options),
                (50,  'Current VA Disability Rating:',       'select',   'none',           False, '20%\n10%-\n50%'),
                (60,  'Phone Number:',                       'number',   'mobile',         False, False),
                (70,  'WhatsApp Number:',                    'number',   'none',           False, False),
                (80,  'Email Address:',                      'email',    'email',          False, False),
                (90,  'Do you have access to your DD214?:',  'checkbox', 'none',           False, False),
                (100, 'Birth',                               'date',     'birthday',       False, False),
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
        return res


class VacSocialFbFields(models.Model):
    _name        = 'vac.social.fb.fields'
    _description = 'Facebook Registration Field'
    _order       = 'sequence, id'

    sequence = fields.Integer(default=10)
    social_fb_id = fields.Many2one(
        'vac.social.fb', string='Facebook Campaign', required=True, ondelete='cascade')
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

    @api.depends('select_options')
    def _compute_select_options_count(self):
        for rec in self:
            rec.select_options_count = len(rec.get_select_options_list())

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

    @api.onchange('field_type')
    def _onchange_field_type(self):
        if self.field_type != 'select':
            self.select_options = False

    def get_select_options_list(self):
        self.ensure_one()
        if not self.select_options:
            return []
        return [o.strip() for o in self.select_options.splitlines() if o.strip()]

    # ─── NEW ─────────────────────────────────────────────────────────────────
    def get_branch_service_options(self):
        """
        Return a live branch.service recordset for QWeb rendering.

        Always queries the DB so the list reflects the latest services even if
        the admin added new ones after the field was saved.

        Template usage (option value = record id, not name string):

            <t t-foreach="field.get_branch_service_options()" t-as="svc">
                <option t-att-value="svc.id"
                        t-att-selected="'selected' if svc.is_default else None">
                    <t t-esc="svc.name"/>
                </option>
            </t>
        """
        self.ensure_one()
        if self.maps_to == 'branch_service':
            return self.env['branch.service'].search([], order='name')
        return self.env['branch.service'].browse()


# ═══════════════════════════════════════════════════════════════════
#  INSTAGRAM
# ═══════════════════════════════════════════════════════════════════
class VacSocialIng(models.Model):
    _name = 'vac.social.ing'
    _description = 'VAC Social – Instagram'
    _inherit = 'vac.social.mixin'
    _rec_name = 'title'
    _order = 'date_begin desc, id desc'


    registration_field_ids = fields.One2many(
        'vac.social.ing.fields',
        'social_ing_id',
        string='Custom Registration Fields',
        help='Extra fields shown on the public campaign registration form',
    )

    lead_ids = fields.One2many(
        'vac.event.lead',
        'social_ig_id',
        string='Leads',
        help='Leads generated from this Instagram campaign',
    )

    lead_count = fields.Integer(
        string='Leads',
        compute='_compute_lead_count',
        store=True,
        help='Total number of leads from this Instagram campaign',
    )

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for rec in self:
            rec.lead_count = len(rec.lead_ids)

    def action_view_leads(self):
        self.ensure_one()
        first_stage = self.env['vac.social.lead.stage'].search(
            [], order='sequence, id', limit=1)
        return {
            'name': f'Leads — {self.title}',
            'type': 'ir.actions.act_window',
            'res_model': 'vac.event.lead',
            'view_mode': 'list,kanban,form',
            'views': [
                (self.env.ref('vac_social_marketing.vac_event_lead_view_social_list').id, 'list'),
                (self.env.ref('vac_social_marketing.vac_event_lead_view_social_kanban').id, 'kanban'),
                (self.env.ref('vac_social_marketing.vac_event_lead_view_form').id, 'form'),
            ],
            'domain': [('social_ig_id', '=', self.id)],
            'context': {
                'default_social_ig_id': self.id,
                'default_platform': 'instagram',
                'default_social_stage_id': first_stage.id if first_stage else False,
                'group_by': ['social_stage_id'],
            },
        }

    def _get_social_url_prefix(self):
        return 'social/ing'

    def action_preview(self):
        """Open a preview wizard for this Instagram campaign."""
        self.ensure_one()
        wizard = self.env['vac.social.preview.wizard'].create({
            'source_model': self._name,
            'source_id': self.id,
            'title': self.title,
            'social_link': self.social_link,

            'published': self.published,
        })
        return {
            'name': 'Campaign Preview',
            'type': 'ir.actions.act_window',
            'res_model': 'vac.social.preview.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'dialog_size': 'extra-large'},
        }

    @api.model
    def _cron_auto_stage(self):
        """Cron: auto-move Instagram campaigns through Draft → Published → Ongoing → Completed."""
        now = fields.Datetime.now()
        draft_stage     = self.env['vac.event.stage'].search([('name', 'ilike', 'Draft')],     limit=1)
        published_stage = self.env['vac.event.stage'].search([('name', 'ilike', 'Published')], limit=1)
        ongoing_stage   = self.env['vac.event.stage'].search([('name', 'ilike', 'Ongoing')],   limit=1)
        completed_stage = self.env['vac.event.stage'].search([('name', 'ilike', 'Completed')], limit=1)

        active_recs = self.with_context(_vac_stage_updating=True).search([('active', '=', True)])

        # ── Step 1: Completed — end date passed ──────────────────────────────
        to_complete = active_recs.filtered(
            lambda r: r.date_end and r.date_end <= now
            and r.stage_id != completed_stage
        )
        if to_complete and completed_stage:
            to_complete.write({'published': False, 'stage_id': completed_stage.id})

        # ── Step 2: Ongoing — within start/end window ─────────────────────────
        to_ongoing = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and r.stage_id != ongoing_stage
        )
        if to_ongoing and ongoing_stage:
            to_ongoing.write({'published': True, 'stage_id': ongoing_stage.id})

        # ── Step 3: Auto-publish Draft campaigns whose start date has arrived ─
        to_auto_publish = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and not r.published
            and r.stage_id not in (ongoing_stage, completed_stage)
        )
        if to_auto_publish and published_stage:
            to_auto_publish.write({'published': True, 'stage_id': published_stage.id})

        # Future manually-published campaigns → Published stage
        to_published_stage = active_recs.filtered(
            lambda r: r.date_begin and r.date_begin > now
            and r.published
            and r.stage_id not in (ongoing_stage, completed_stage, published_stage)
        )
        if to_published_stage and published_stage:
            to_published_stage.write({'stage_id': published_stage.id})

    # ── Auto-populate standard registration fields on New ────────────────────
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Auto-set Draft stage
        if 'stage_id' in fields_list and 'stage_id' not in res:
            stage = self.env['vac.event.stage'].search([('name', '=', 'Draft')], limit=1)
            if not stage:
                stage = self.env['vac.event.stage'].search([], order='sequence, name', limit=1)
            if stage:
                res['stage_id'] = stage.id
        if 'registration_field_ids' in fields_list and 'registration_field_ids' not in res:
            services = self.env['branch.service'].search([], order='name')
            branch_options = '\n'.join(s.name for s in services if s.name)

            DEFAULT_FIELDS = [
                # (seq, label,                               type,       maps_to,          required, select_options)
                (10,  'Are you a US Veteran?',               'checkbox', 'none',           False, False),
                (20,  'First Name',                          'text',     'name',           False, False),
                (30,  'Last Name',                           'text',     'name',           False, False),
                (40,  'Branch of Service',                   'select',   'branch_service', True,  branch_options),
                (50,  'Current VA Disability Rating:',       'select',   'none',           False, '20%\n10%-\n50%'),
                (60,  'Phone Number:',                       'number',   'mobile',         False, False),
                (70,  'WhatsApp Number:',                    'number',   'none',           False, False),
                (80,  'Email Address:',                      'email',    'email',          False, False),
                (90,  'Do you have access to your DD214?:',  'checkbox', 'none',           False, False),
                (100, 'Birth',                               'date',     'birthday',       False, False),
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
        return res


class VacSocialIngFields(models.Model):
    _name        = 'vac.social.ing.fields'
    _description = 'Instagram Registration Field'
    _order       = 'sequence, id'

    sequence = fields.Integer(default=10)
    social_ing_id = fields.Many2one(
        'vac.social.ing', string='Instagram Campaign', required=True, ondelete='cascade')
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

    @api.depends('select_options')
    def _compute_select_options_count(self):
        for rec in self:
            rec.select_options_count = len(rec.get_select_options_list())

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

    @api.onchange('field_type')
    def _onchange_field_type(self):
        if self.field_type != 'select':
            self.select_options = False

    def get_select_options_list(self):
        self.ensure_one()
        if not self.select_options:
            return []
        return [o.strip() for o in self.select_options.splitlines() if o.strip()]

    # ─── NEW ─────────────────────────────────────────────────────────────────
    def get_branch_service_options(self):
        """
        Return a live branch.service recordset for QWeb rendering.

        Always queries the DB so the list reflects the latest services even if
        the admin added new ones after the field was saved.

        Template usage (option value = record id, not name string):

            <t t-foreach="field.get_branch_service_options()" t-as="svc">
                <option t-att-value="svc.id"
                        t-att-selected="'selected' if svc.is_default else None">
                    <t t-esc="svc.name"/>
                </option>
            </t>
        """
        self.ensure_one()
        if self.maps_to == 'branch_service':
            return self.env['branch.service'].search([], order='name')
        return self.env['branch.service'].browse()


# ═══════════════════════════════════════════════════════════════════
#  OFFICES
# ═══════════════════════════════════════════════════════════════════
class VacSocialOffice(models.Model):
    _name = 'vac.social.office'
    _description = 'VAC Social – Offices'
    _inherit = 'vac.social.mixin'
    _rec_name = 'title'
    _order = 'date_begin desc, id desc'


    registration_field_ids = fields.One2many(
        'vac.social.office.fields',
        'social_office_id',
        string='Custom Registration Fields',
        help='Extra fields shown on the public campaign registration form',
    )

    lead_ids = fields.One2many(
        'vac.event.lead',
        'social_office_id',
        string='Leads',
        help='Leads generated from this Offices campaign',
    )

    lead_count = fields.Integer(
        string='Leads',
        compute='_compute_lead_count',
        store=True,
        help='Total number of leads from this Offices campaign',
    )

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for rec in self:
            rec.lead_count = len(rec.lead_ids)

    def action_view_leads(self):
        self.ensure_one()
        first_stage = self.env['vac.social.lead.stage'].search(
            [], order='sequence, id', limit=1)
        return {
            'name': f'Leads — {self.title}',
            'type': 'ir.actions.act_window',
            'res_model': 'vac.event.lead',
            'view_mode': 'list,kanban,form',
            'views': [
                (self.env.ref('vac_social_marketing.vac_event_lead_view_social_list').id, 'list'),
                (self.env.ref('vac_social_marketing.vac_event_lead_view_social_kanban').id, 'kanban'),
                (self.env.ref('vac_social_marketing.vac_event_lead_view_form').id, 'form'),
            ],
            'domain': [('social_office_id', '=', self.id)],
            'context': {
                'default_social_office_id': self.id,
                'default_platform': 'office',
                'default_social_stage_id': first_stage.id if first_stage else False,
                'group_by': ['social_stage_id'],
            },
        }

    def _get_social_url_prefix(self):
        return 'social/office'

    def action_preview(self):
        """Open a preview wizard for this Offices campaign."""
        self.ensure_one()
        wizard = self.env['vac.social.preview.wizard'].create({
            'source_model': self._name,
            'source_id': self.id,
            'title': self.title,
            'social_link': self.social_link,

            'published': self.published,
        })
        return {
            'name': 'Campaign Preview',
            'type': 'ir.actions.act_window',
            'res_model': 'vac.social.preview.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'dialog_size': 'extra-large'},
        }

    @api.model
    def _cron_auto_stage(self):
        """Cron: auto-move Offices campaigns through Draft → Published → Ongoing → Completed."""
        now = fields.Datetime.now()
        draft_stage     = self.env['vac.event.stage'].search([('name', 'ilike', 'Draft')],     limit=1)
        published_stage = self.env['vac.event.stage'].search([('name', 'ilike', 'Published')], limit=1)
        ongoing_stage   = self.env['vac.event.stage'].search([('name', 'ilike', 'Ongoing')],   limit=1)
        completed_stage = self.env['vac.event.stage'].search([('name', 'ilike', 'Completed')], limit=1)

        active_recs = self.with_context(_vac_stage_updating=True).search([('active', '=', True)])

        # ── Step 1: Completed — end date passed ──────────────────────────────
        to_complete = active_recs.filtered(
            lambda r: r.date_end and r.date_end <= now
            and r.stage_id != completed_stage
        )
        if to_complete and completed_stage:
            to_complete.write({'published': False, 'stage_id': completed_stage.id})

        # ── Step 2: Ongoing — within start/end window ─────────────────────────
        to_ongoing = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and r.stage_id != ongoing_stage
        )
        if to_ongoing and ongoing_stage:
            to_ongoing.write({'published': True, 'stage_id': ongoing_stage.id})

        # ── Step 3: Auto-publish Draft campaigns whose start date has arrived ─
        to_auto_publish = active_recs.filtered(
            lambda r: r.date_begin and r.date_end
            and r.date_begin <= now < r.date_end
            and not r.published
            and r.stage_id not in (ongoing_stage, completed_stage)
        )
        if to_auto_publish and published_stage:
            to_auto_publish.write({'published': True, 'stage_id': published_stage.id})

        # Future manually-published campaigns → Published stage
        to_published_stage = active_recs.filtered(
            lambda r: r.date_begin and r.date_begin > now
            and r.published
            and r.stage_id not in (ongoing_stage, completed_stage, published_stage)
        )
        if to_published_stage and published_stage:
            to_published_stage.write({'stage_id': published_stage.id})

    # ── Auto-populate standard registration fields on New ────────────────────
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Auto-set Draft stage
        if 'stage_id' in fields_list and 'stage_id' not in res:
            stage = self.env['vac.event.stage'].search([('name', '=', 'Draft')], limit=1)
            if not stage:
                stage = self.env['vac.event.stage'].search([], order='sequence, name', limit=1)
            if stage:
                res['stage_id'] = stage.id
        if 'registration_field_ids' in fields_list and 'registration_field_ids' not in res:
            services = self.env['branch.service'].search([], order='name')
            branch_options = '\n'.join(s.name for s in services if s.name)

            DEFAULT_FIELDS = [
                # (seq, label,                               type,       maps_to,          required, select_options)
                (10,  'Are you a US Veteran?',               'checkbox', 'none',           False, False),
                (20,  'First Name',                          'text',     'name',           False, False),
                (30,  'Last Name',                           'text',     'name',           False, False),
                (40,  'Branch of Service',                   'select',   'branch_service', True,  branch_options),
                (50,  'Current VA Disability Rating:',       'select',   'none',           False, '20%\n10%-\n50%'),
                (60,  'Phone Number:',                       'number',   'mobile',         False, False),
                (70,  'WhatsApp Number:',                    'number',   'none',           False, False),
                (80,  'Email Address:',                      'email',    'email',          False, False),
                (90,  'Do you have access to your DD214?:',  'checkbox', 'none',           False, False),
                (100, 'Birth',                               'date',     'birthday',       False, False),
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
        return res


class VacSocialOfficeFields(models.Model):
    _name        = 'vac.social.office.fields'
    _description = 'Offices Registration Field'
    _order       = 'sequence, id'

    sequence = fields.Integer(default=10)
    social_office_id = fields.Many2one(
        'vac.social.office', string='Offices Campaign', required=True, ondelete='cascade')
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
            ('branch_service', 'Lead → Branch / Service'),
        ],
        string='Maps To', default='none', required=True,
    )
    placeholder    = fields.Char(string='Placeholder')
    is_required    = fields.Boolean(string='Required', default=False)
    select_options = fields.Text(string='Dropdown Options')
    select_options_count = fields.Integer(
        string='No. of Options', compute='_compute_select_options_count')
    active = fields.Boolean(default=True)

    @api.depends('select_options')
    def _compute_select_options_count(self):
        for rec in self:
            rec.select_options_count = len(rec.get_select_options_list())

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

    @api.constrains('field_type', 'select_options')
    def _check_select_options(self):
        for rec in self:
            if rec.maps_to == 'branch_service':
                continue
            if rec.field_type == 'select' and not rec.get_select_options_list():
                raise ValidationError(
                    f'Field "{rec.label}": '
                    'You must provide at least one dropdown option.'
                )

    @api.onchange('field_type')
    def _onchange_field_type(self):
        if self.field_type != 'select':
            self.select_options = False

    def get_select_options_list(self):
        self.ensure_one()
        if not self.select_options:
            return []
        return [o.strip() for o in self.select_options.splitlines() if o.strip()]

    def get_branch_service_options(self):
        """
        Return a live branch.service recordset for QWeb rendering.
        """
        self.ensure_one()
        if self.maps_to == 'branch_service':
            return self.env['branch.service'].search([], order='name')
        return self.env['branch.service'].browse()
