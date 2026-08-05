from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging
import traceback

_logger = logging.getLogger(__name__)


class VacEventLeadGenerationWizard(models.TransientModel):
    _name = 'vac.event.lead.generation.wizard'
    _description = 'Lead Generation Wizard'

    event_id = fields.Many2one(
        'vac.event', string='Event', required=True, readonly=True)

    total_signed_leads = fields.Integer(
        string='Total Signed Leads', readonly=True)

    @api.depends('event_id')
    def _compute_available_leads(self):
        signed_stage = self.env['vac.event.lead.stage'].search(
            [('is_signed', '=', True)], limit=1)
        for wizard in self:
            if not wizard.event_id or not signed_stage:
                wizard.available_leads = 0
                continue
            wizard.available_leads = self.env['vac.event.lead'].search_count([
                ('event_id',    '=', wizard.event_id.id),
                ('stage_id',    '=', signed_stage.id),
                ('bam_user_id', '=', False),
                ('active',      '=', True),
            ])

    available_leads = fields.Integer(
        string='Available to Assign',
        compute='_compute_available_leads',
    )

    assignment_line_ids = fields.One2many(
        'vac.event.lead.generation.line', 'wizard_id', string='Assign To')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        event_id = (self.env.context.get('default_event_id') or
                    self.env.context.get('active_id'))
        if event_id:
            event = self.env['vac.event'].browse(event_id)
            if event.exists():
                res['event_id']           = event_id
                res['total_signed_leads'] = event.signed_lead_count
        return res

    # ── Helpers ───────────────────────────────────────────────────────
    def _safe(self, record, fname, default=''):
        try:
            val = getattr(record, fname, None)
            return val if val else default
        except Exception:
            return default

    def _get_fallback_record(self, model, field_description):
        """Get first record of a model or raise clear error."""
        record = self.env[model].sudo().search([], limit=1)
        if not record:
            raise ValidationError(
                f"Cannot create CRM opportunity. Please create at least one "
                f"record for: {field_description} ({model})"
            )
        return record

    # ── Build CRM vals ────────────────────────────────────────────────
    def _build_crm_vals(self, lead, bam_user):
        """
        Build vals dict for crm.lead.create().
        Uses number format instead of stars to avoid yellow highlighting.
        """
        crm_fields = self.env['crm.lead']._fields

        event_title = lead.event_id.title_name if lead.event_id else 'Event'
        event_date  = str(lead.event_id.date) if lead.event_id else 'N/A'
        branch_name = lead.branch_service_id.name if lead.branch_service_id else 'N/A'

        # Get required fallback records (system configuration)
        fallback_client_status = self._get_fallback_record('client.status', 'Client Status')
        fallback_claim_stage = self._get_fallback_record('claim.stage', 'Claim Stage')
        fallback_claim_status = self._get_fallback_record('claim.status', 'Claim Status')
        fallback_crm_stage = self._get_fallback_record('crm.stage', 'CRM Stage')

        # Get VA disability rating from the actual field on the lead
        lead_rating = lead.current_va_disability_rating or 0
        
        # Get status letter (S, A, C) from lead
        lead_status_letter = getattr(lead, 'status_letter', '') or ''
        
        # Validate business-critical data
        if not lead.branch_service_id:
            raise ValidationError(
                f"Cannot create CRM opportunity for lead '{lead.name}'. "
                f"Branch of Service is required."
            )

        # Get contact info from lead
        lead_email = lead.email or ''
        lead_mobile = lead.mobile or ''
        lead_name = lead.name or 'Unknown'
        lead_birthday = lead.birthday if lead.birthday else None
        lead_ssn = lead.ssn if lead.ssn else 'N/A'
        lead_age = lead.age if hasattr(lead, 'age') and lead.age else None
        lead_notes = lead.notes if lead.notes else ''

        # Start building vals with ALL required fields
        vals = {
            # Basic Information
            'name': f"{lead_name}",  # Just the name, not prefixed
            'type': 'opportunity',
            'partner_name': lead_name,
            
            # User Assignments (all required)
            'user_id': bam_user.id,
            'processing_owner_id': bam_user.id,
            'processor_name_id': bam_user.id,
            'processing_co_owner_id': [(4, bam_user.id)],
            
            # Required System Fields
            'client_status': fallback_client_status.id,
            'claim_stage': fallback_claim_stage.id,
            'claim1_status': [(4, fallback_claim_status.id)],
            'stage_id': fallback_crm_stage.id,
            'branch_of_service': lead.branch_service_id.id,
            
            # Required numeric fields
            'current_va_rating': float(lead_rating) if lead_rating else 0.0,  # Store rating as number
            'claim1_percentage': 0.0,
            'claim2_percentage': 0.0,
            
            # Required personal information
            'birthday': lead_birthday or fields.Date.today(),
            'ssn': lead_ssn,
            
            # Required char fields - NO STARS HERE
            'referral_name': 'Facebook' if lead.platform == 'facebook' else 'Instagram' if lead.platform == 'instagram' else 'Offices' if lead.platform == 'office' else event_title,
            'answer_0845': 'N/A',
            'quick_notes': f"Auto-created from Event Lead ID {lead.id}\nRating: {lead_rating}/5\nStatus: {lead_status_letter}",
            'ets': 'N/A',
            
            # Contact Information
            'email_from': lead_email or 'noemail@placeholder.com',
            'client_email': lead_email or 'noemail@placeholder.com',
            'phone': lead_mobile or '0000000000',
            'client_phone': lead_mobile or '0000000000',
            'mobile': lead_mobile or '',
            
            # Store rating in a custom field if available
            'rating': float(lead_rating) if 'rating' in crm_fields else 0.0,
            
            # Description with all display information - NO STARS
            'description': self._build_plain_description(lead, lead_rating, lead_status_letter, event_title, event_date, branch_name),
        }
        
        # Add status letter to a custom field if available
        if 'status' in crm_fields:
            vals['status'] = lead_status_letter
        
        # Add optional fields only if they have data
        if lead_age:
            vals['age'] = lead_age
        
        # ── Sales team ────────────────────────────────────────────────
        if 'team_id' in crm_fields:
            try:
                team = self.env['crm.team'].search(
                    [('member_ids', 'in', [bam_user.id])], limit=1)
                if not team:
                    team = self.env['crm.team'].search([], limit=1)
                if team:
                    vals['team_id'] = team.id
            except Exception as te:
                _logger.warning(f"CRM team lookup failed (non-critical): {te}")

        # ── Strip any keys that don't exist ───────────────────────────
        vals = {k: v for k, v in vals.items() if k in crm_fields}

        _logger.info(
            f"CRM vals built for lead ID={lead.id} — keys: {list(vals.keys())}"
        )
        return vals
    
    def _build_plain_description(self, lead, rating, status_letter, event_title, event_date, branch_name):
        """Build a comprehensive description with plain text - NO STARS OR SYMBOLS."""
        parts = [
            f"Source: Event Lead (ID: {lead.id})",
            f"Name: {lead.name}",
            f"Rating: {rating}/5",
            f"Status: {status_letter}",
            f"Event: {event_title}",
            f"Date: {event_date}",
            f"Branch: {branch_name}",
        ]
        
        if lead.email:
            parts.append(f"Email: {lead.email}")
        
        if lead.mobile:
            parts.append(f"Mobile: {lead.mobile}")
        
        if lead.birthday:
            parts.append(f"Birthday: {lead.birthday}")
        
        if lead.ssn and lead.ssn != 'N/A':
            parts.append(f"SSN/ID: {lead.ssn}")
        
        if lead.notes:
            parts.append(f"Notes: {lead.notes}")
        
        return "\n".join(parts)

    # ── CRM opportunity creation ──────────────────────────────────────
    def _create_crm_opportunity(self, lead, bam_user):
        if 'crm.lead' not in self.env:
            raise UserError("CRM module is not installed.")

        vals = self._build_crm_vals(lead, bam_user)
        crm_opp = self.env['crm.lead'].sudo().create(vals)
        _logger.info(f"✅ CRM created: ID={crm_opp.id}  name={crm_opp.name}")

        return crm_opp

    def _apply_crm_tags(self, crm_opp, lead):
        """Apply tags with neutral colors - NO YELLOW."""
        try:
            if 'tag_ids' not in self.env['crm.lead']._fields:
                return
            CrmTag = self.env['crm.tag'].sudo()
            event_title = lead.event_id.title_name if lead.event_id else None
            
            # Get VA disability rating from the actual field on the lead
            lead_rating = lead.current_va_disability_rating or 0
            lead_status = getattr(lead, 'status_letter', '') or ''
            
            tag_names = ['Event Lead']
            if event_title:
                tag_names.append(event_title)
            
            # Add rating tag as number (not stars)
            if lead_rating:
                tag_names.append(f"Rating: {lead_rating}/5")  # NO STARS
            
            # Add status tag if available
            if lead_status:
                tag_names.append(f"Status: {lead_status}")
            
            tag_ids = []
            for tname in tag_names:
                tag = CrmTag.search([('name', '=', tname)], limit=1)
                if not tag:
                    # Create with neutral color (0 = no color/gray instead of yellow)
                    tag = CrmTag.create({'name': tname, 'color': 0})  # Changed from 3 to 0
                tag_ids.append(tag.id)
            crm_opp.sudo().write({'tag_ids': [(4, tid) for tid in tag_ids]})
        except Exception as te:
            _logger.warning(f"Tag application failed (non-critical): {te}")

    # ── Main action ───────────────────────────────────────────────────
    def action_assign_leads(self):
        self.ensure_one()

        if not self.assignment_line_ids:
            raise ValidationError('Please add at least one assignment line!')

        total_assigned = sum(l.count for l in self.assignment_line_ids)
        if total_assigned == 0:
            raise ValidationError('Total assigned count cannot be zero!')

        if total_assigned > self.total_signed_leads:
            raise ValidationError(
                f'Assigned ({total_assigned}) > total signed leads '
                f'({self.total_signed_leads})!')

        signed_stage = self.env['vac.event.lead.stage'].search(
            [('is_signed', '=', True)], limit=1)
        if not signed_stage:
            raise ValidationError('No signed stage configured!')

        # Pull from ALL signed leads
        all_signed_leads = self.env['vac.event.lead'].search([
            ('event_id', '=', self.event_id.id),
            ('stage_id', '=', signed_stage.id),
            ('active',   '=', True),
        ], order='id')

        if not all_signed_leads:
            raise ValidationError('No signed leads found!')

        if total_assigned > len(all_signed_leads):
            raise ValidationError(
                f'Only {len(all_signed_leads)} total signed leads available, '
                f'cannot assign {total_assigned}.')

        lead_index   = 0
        crm_ok       = 0
        crm_failed   = 0
        fail_details = []

        for line in self.assignment_line_ids:
            if line.count <= 0:
                continue

            batch = all_signed_leads[lead_index:lead_index + line.count]
            if not batch:
                raise ValidationError(
                    f'Not enough leads for {line.user_id.name}!')

            assigned_ids = []

            for lead in batch:
                # STEP 1 — assign bam_user
                lead.write({'bam_user_id': line.user_id.id})
                assigned_ids.append(lead.id)

                # STEP 2 — CRM opportunity
                sp = f'crm_lead_{lead.id}'
                try:
                    self.env.cr.execute(f'SAVEPOINT "{sp}"')
                    crm = self._create_crm_opportunity(lead, line.user_id)
                    self.env.cr.execute(f'RELEASE SAVEPOINT "{sp}"')
                    crm_ok += 1
                    try:
                        lead.sudo().write({
                            'crm_lead_id': crm.id,
                            'notes': (lead.notes or '') +
                                     f"\n\n[AUTO] CRM Opportunity: "
                                     f"{crm.name} (ID {crm.id})"
                        })
                    except Exception:
                        pass
                except Exception as err:
                    self.env.cr.execute(f'ROLLBACK TO SAVEPOINT "{sp}"')
                    self.env['crm.lead'].invalidate_model()
                    crm_failed += 1
                    short_err = str(err)
                    fail_details.append((lead.name or f'ID {lead.id}', short_err))
                    _logger.error(
                        "\n" + "=" * 70 + "\n"
                        f"CRM FAILED  lead={lead.name!r} (ID {lead.id})\n"
                        f"bam_user={line.user_id.name!r}\n"
                        f"Error: {short_err}\n"
                        f"{traceback.format_exc()}"
                        + "=" * 70
                    )

            # STEP 3 — assignment record
            existing = self.env['vac.event.lead.assignment'].search([
                ('event_id', '=', self.event_id.id),
                ('name',     '=', line.user_id.id),
            ], limit=1)

            if existing:
                existing.write({
                    'count'   : existing.count + line.count,
                    'lead_ids': [(4, lid) for lid in assigned_ids],
                })
            else:
                self.env['vac.event.lead.assignment'].create({
                    'event_id': self.event_id.id,
                    'name'    : line.user_id.id,
                    'count'   : line.count,
                    'lead_ids': [(6, 0, assigned_ids)],
                })

            # STEP 4 — archive batch
            self.env['vac.event.lead'].sudo().browse(assigned_ids).write(
                {'active': False}
            )

            lead_index += line.count

        # ── notification ──────────────────────────────────────────────
        if crm_failed:
            fail_summary = '\n'.join(
                f"  • {name}: {err}" for name, err in fail_details[:5]
            )
            if len(fail_details) > 5:
                fail_summary += f"\n  … and {len(fail_details) - 5} more."
            msg = (
                f'{total_assigned} lead(s) assigned.\n'
                f'{crm_ok} CRM opportunities created.\n'
                f'{crm_failed} CRM creation(s) FAILED:\n\n'
                f'{fail_summary}\n\n'
                f'Check the server log for full tracebacks.'
            )
            title, msg_type = 'Partially Completed', 'warning'
        else:
            msg = (
                f'{total_assigned} lead(s) assigned and '
                f'{crm_ok} CRM opportunities created successfully!'
            )
            title, msg_type = 'Completed!', 'success'

        return {
            'type'  : 'ir.actions.client',
            'tag'   : 'display_notification',
            'params': {
                'title'  : title,
                'message': msg,
                'type'   : msg_type,
                'sticky' : True,
                'next'   : {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_view_signed_leads(self):
        self.ensure_one()
        stage = self.env['vac.event.lead.stage'].search(
            [('is_signed', '=', True)], limit=1)
        if not stage:
            raise ValidationError('No signed stage configured!')
        return {
            'name'     : f'Signed Leads - {self.event_id.title_name}',
            'type'     : 'ir.actions.act_window',
            'res_model': 'vac.event.lead',
            'view_mode': 'list,kanban,form',
            'domain'   : [('event_id', '=', self.event_id.id),
                          ('stage_id', '=', stage.id)],
            'context'  : {'default_event_id': self.event_id.id},
        }


class VacEventLeadGenerationLine(models.TransientModel):
    _name = 'vac.event.lead.generation.line'
    _description = 'Lead Generation Assignment Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'vac.event.lead.generation.wizard', required=True, ondelete='cascade')
    sequence  = fields.Integer(default=10)
    user_id   = fields.Many2one(
        'res.users', string='BAM User', required=True,
        domain=lambda self: (
            [('share', '=', False), ('user_role_type', '=', 'bam')]
            if 'user_role_type' in self.env['res.users']._fields
            else [('share', '=', False)]
        ))
    count     = fields.Integer(string='Lead Count', default=1)

    @api.constrains('count')
    def _check_count(self):
        for line in self:
            if line.count <= 0:
                raise ValidationError('Count must be greater than zero!')