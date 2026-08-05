from odoo import models, fields, api
from odoo.exceptions import UserError


class VacEventLead(models.Model):
    _inherit = 'vac.event.lead'

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options=options)
        action_id = (options or {}).get('action_id')
        if action_id:
            self._filter_lead_distribution_actions(res, action_id)
        return res

    @api.model
    def _filter_lead_distribution_actions(self, views_result, action_id):
        action_id = int(action_id)
        event_action = self.env.ref(
            'vac_social_marketing.vac_event_lead_action_event_only',
            raise_if_not_found=False,
        )
        social_action = self.env.ref(
            'vac_social_marketing.vac_event_lead_action_social_only',
            raise_if_not_found=False,
        )
        if event_action and action_id == event_action.id:
            hidden_action = self.env.ref(
                'vac_social_marketing.action_server_social_lead_distribution',
                raise_if_not_found=False,
            )
        elif social_action and action_id == social_action.id:
            hidden_action = self.env.ref(
                'vac_social_marketing.action_server_lead_generation',
                raise_if_not_found=False,
            )
        else:
            return

        if not hidden_action:
            return

        for view in views_result.get('views', {}).values():
            toolbar = view.get('toolbar')
            if not toolbar:
                continue
            toolbar_actions = toolbar.get('action', [])
            toolbar['action'] = [
                action for action in toolbar_actions
                if action.get('id') != hidden_action.id
            ]

    # ── helpers ───────────────────────────────────────────────────────────────

    def _notify(self, title, message, ntype='warning', next_action=None, sticky=True):
        params = {
            'title': title,
            'message': message,
            'type': ntype,
            'sticky': sticky,
        }
        if next_action:
            params['next'] = next_action
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': params,
        }

    # ── Event Lead Distribution (bulk, from list) ──────────────────────────────

    def action_lead_generation_bulk(self):
        """
        Server action to open lead generation wizard from list view.
        Only valid for leads that belong to an Event.
        """
        if not self:
            return self._notify('No Selection', 'Please select at least one lead.')

        # Guard: must be event leads
        non_event = self.filtered(lambda l: not l.event_id)
        if non_event:
            return self._notify(
                'Invalid Selection',
                'Lead Distribution is only for Event Leads. '
                'Please select leads that belong to an event.',
            )

        event_ids = self.mapped('event_id')
        if len(event_ids) > 1:
            return self._notify(
                'Multiple Events',
                'Please select leads from only one event.',
            )

        event = event_ids[0]
        event_id = event.id

        signed_stage = self.env['vac.event.lead.stage'].search(
            [('is_signed', '=', True)], limit=1)
        if not signed_stage:
            return self._notify(
                'No Signed Stage',
                'Please configure a signed stage first.',
            )

        signed_leads_count = self.env['vac.event.lead'].search_count([
            ('event_id', '=', event_id),
            ('stage_id.is_signed', '=', True),
        ])
        if signed_leads_count == 0:
            return self._notify(
                'No Signed Leads',
                'There are no leads in the signed stage for this event.',
            )

        return {
            'name': 'Lead Generation',
            'type': 'ir.actions.act_window',
            'res_model': 'vac.event.lead.generation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_event_id': event_id,
                'default_total_signed_leads': signed_leads_count,
            },
        }

    # ── Social Lead Distribution (bulk, from list) ─────────────────────────────

    def action_social_lead_distribution_bulk(self):
        """
        Bulk-distribute selected Social Media Leads to the BAM Dashboard.
        Sets is_social_distributed = True and dashboard_state = 'pending'
        so they become visible in the BAM Dashboard queue.
        """
        if not self:
            return self._notify('No Selection', 'Please select at least one lead.')

        # Guard: must be social leads (linked to a campaign or manually marked
        # as Facebook / Instagram / Offices)
        non_social = self.filtered(
            lambda l: (
                not l.social_fb_id
                and not l.social_ig_id
                and not l.social_office_id
                and l.platform not in ('facebook', 'instagram', 'office')
            )
        )
        if non_social:
            return self._notify(
                'Invalid Selection',
                'Social Lead Distribution is only for Social Media Leads '
                '(Facebook / Instagram / Offices). Please select social media leads only.',
            )

        # Only distribute leads that have NOT already been distributed
        already_distributed = self.filtered(lambda l: l.is_social_distributed)
        to_distribute = self - already_distributed

        if not to_distribute:
            return self._notify(
                'Already Distributed',
                'All selected leads have already been sent to the BAM Dashboard.',
                'info',
            )

        to_distribute.write({
            'is_social_distributed': True,
            'dashboard_state': 'pending',
            'active': False,   # archive from Social Media Leads view
        })

        msg = (
            f'{len(to_distribute)} lead(s) sent to the BAM Dashboard.'
        )
        if already_distributed:
            msg += (
                f' ({len(already_distributed)} lead(s) were already distributed '
                f'and skipped.)'
            )

        return self._notify(
            'Success',
            msg,
            'success',
            {'type': 'ir.actions.client', 'tag': 'soft_reload'},
        )

    # ── Manual BAM Assignment — Confirm (list view Action menu) ────────────────
    # This is a separate, additional flow. It does NOT use round robin batches
    # like "Event Lead Distribution" above. The user manually sets "Assigned
    # BAM" inline for one or several Event Leads directly in the list (each
    # lead can have a different BAM), selects those row(s) with the checkbox,
    # then opens Actions ⚙ → "Confirm BAM Assignment" ONCE. Every selected
    # lead is sent to its own already-chosen BAM user, a CRM opportunity is
    # created for each, and it is recorded under the event's Lead Assignments
    # (so it shows up in the event's "Assigned Leads" / "Sent to CRM" smart
    # buttons exactly like the bulk-wizard-assigned leads do).

    def _confirm_bam_assignment_one(self, bam_user):
        """Send a single Event Lead to CRM under the given BAM user.
        Returns the created crm.lead record. Raises on failure (caller
        decides whether to let one failure stop the whole batch)."""
        self.ensure_one()

        # Reuse the exact CRM-building/tagging logic already used by the
        # "Event Lead Distribution" wizard, without touching that wizard's
        # code, so both flows always stay consistent.
        wizard = self.env['vac.event.lead.generation.wizard'].new({})

        savepoint = f'manual_bam_confirm_{self.id}'
        try:
            self.env.cr.execute(f'SAVEPOINT "{savepoint}"')
            crm_opp = wizard._create_crm_opportunity(self, bam_user)
            wizard._apply_crm_tags(crm_opp, self)
            self.env.cr.execute(f'RELEASE SAVEPOINT "{savepoint}"')
        except Exception as err:
            self.env.cr.execute(f'ROLLBACK TO SAVEPOINT "{savepoint}"')
            self.env['crm.lead'].invalidate_model()
            raise UserError(f'Could not create the CRM opportunity: {err}')

        self.sudo().write({
            'crm_lead_id': crm_opp.id,
            'active': False,   # archive from the Event Leads list, same as the bulk wizard
            'notes': (
                (self.notes or '') +
                f'\n\n[AUTO] Manually confirmed → BAM: {bam_user.name} → '
                f'CRM Opportunity: {crm_opp.name} (ID {crm_opp.id})'
            ),
        })

        # Record under this event's BAM assignments (feeds the event's
        # "Assigned Leads" tab, same place the bulk wizard writes to).
        assignment = self.env['vac.event.lead.assignment'].search([
            ('event_id', '=', self.event_id.id),
            ('name', '=', bam_user.id),
        ], limit=1)
        if assignment:
            assignment.write({
                'count': assignment.count + 1,
                'lead_ids': [(4, self.id)],
            })
        else:
            self.env['vac.event.lead.assignment'].create({
                'event_id': self.event_id.id,
                'name': bam_user.id,
                'count': 1,
                'lead_ids': [(6, 0, [self.id])],
            })

        return crm_opp

    def action_confirm_bam_assignment_bulk(self):
        """Confirm BAM assignment for every selected Event Lead at once.
        Each lead uses whatever BAM user was already picked for it inline
        in the list — this is manual, one-by-one assignment, NOT round robin."""
        try:
            return self._action_confirm_bam_assignment_bulk()
        except Exception as err:
            # Absolute last resort: never let this action fail with no
            # visible feedback at all — always show something.
            return self._notify(
                'Confirm Failed',
                f'Something went wrong while confirming: {err}',
                'danger',
            )

    def _action_confirm_bam_assignment_bulk(self):
        selected = self
        total_selected = len(selected)

        no_event   = selected.filtered(lambda l: not l.event_id)
        candidates = selected - no_event
        already_sent = candidates.filtered(lambda l: l.crm_lead_id)
        candidates = candidates - already_sent
        no_bam = candidates.filtered(lambda l: not l.bam_user_id)
        candidates = candidates - no_bam

        if not candidates:
            return self._notify(
                'Nothing to Confirm',
                f'{total_selected} lead(s) selected, but none are ready. '
                f'Make sure each lead has an "Assigned BAM" chosen, belongs '
                f'to an event, and has not already been sent to CRM.',
                'warning',
            )

        confirmed = self.env['vac.event.lead']
        failed = []
        for lead in candidates:
            try:
                lead._confirm_bam_assignment_one(lead.bam_user_id)
                confirmed |= lead
            except UserError as err:
                failed.append(f'{lead.name}: {err}')
            except Exception as err:
                # Catch-all so ONE bad lead can never silently kill the whole
                # batch and swallow the success notification for the rest.
                failed.append(f'{lead.name}: {err}')

        # Total leads sent to CRM for this event(s) so far (any BAM, any method).
        event_ids = candidates.mapped('event_id').ids
        total_sent_to_crm = self.env['vac.event.lead'].with_context(
            active_test=False
        ).search_count([
            ('event_id', 'in', event_ids),
            ('crm_lead_id', '!=', False),
        ])

        lines = [
            f'{total_selected} lead(s) selected.',
            f'{len(confirmed)} lead(s) confirmed and sent to CRM.',
        ]
        skipped = no_event | already_sent | no_bam
        if skipped:
            lines.append(
                f'{len(skipped)} lead(s) skipped '
                f'(no event, already sent, or no "Assigned BAM" chosen).'
            )
        if failed:
            lines.append(f'{len(failed)} lead(s) failed: ' + '; '.join(failed))
        lines.append(
            f'{total_sent_to_crm} lead(s) from the relevant event(s) have '
            f'now been sent to CRM in total.'
        )

        return self._notify(
            'Confirmed' if not failed else 'Confirmed (with issues)',
            '\n'.join(lines),
            'success' if not failed else 'warning',
            {'type': 'ir.actions.client', 'tag': 'soft_reload'},
        )
