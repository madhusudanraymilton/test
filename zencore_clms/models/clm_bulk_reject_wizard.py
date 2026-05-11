from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError
from markupsafe import Markup


class ClmBulkRejectWizard(models.TransientModel):
    """
    Transient wizard for bulk rejection of clm.limit.change.request records.

    Design:
    ────────
    - Finance selects N pending_fm records in the list view
    - Server action opens this wizard (target='new' dialog)
    - Finance enters ONE fm_comment that is applied to all selected records
    - action_confirm_reject() calls action_reject() on each record

    Why a wizard is required for reject but not approve:
      action_reject() enforces that fm_comment is non-empty.
      A bulk reject without a shared reason would violate SRS §9.3 (audit trail).
      The wizard collects the single shared comment before any writes occur.

    Why the comment is applied via wizard.sudo() write:
      action_reject() validates fm_comment IS present.
      We write fm_comment to each request first (still in pending_fm state,
      so write() guard does NOT block this), then call action_reject() which
      reads the now-populated fm_comment.
    """

    _name = 'clm.bulk.reject.wizard'
    _description = 'CLM Bulk Reject Wizard'

    # ── Populated by the server action before opening the wizard ─────────
    request_ids = fields.Many2many(
        'clm.limit.change.request',
        'clm_bulk_reject_wizard_request_rel',
        'wizard_id',
        'request_id',
        string='Requests to Reject',
        readonly=True,
    )

    # ── Computed stats for UX clarity ─────────────────────────────────────
    pending_count = fields.Integer(
        string='Pending Requests',
        compute='_compute_counts',
        help='Number of selected records actually in Pending FM state.',
    )
    skipped_count = fields.Integer(
        string='Skipped (not pending)',
        compute='_compute_counts',
        help='Records selected but NOT in Pending FM — will be ignored.',
    )

    # ── The shared rejection reason ───────────────────────────────────────
    fm_comment = fields.Text(
        string='Rejection Reason',
        required=True,
        help='This comment will be applied to ALL selected pending requests.',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('request_ids')
    def _compute_counts(self):
        for wizard in self:
            pending = wizard.request_ids.filtered(lambda r: r.state == 'pending_fm')
            wizard.pending_count = len(pending)
            wizard.skipped_count = len(wizard.request_ids) - len(pending)

    # ─────────────────────────────────────────────────────────────────────────
    # ACTION
    # ─────────────────────────────────────────────────────────────────────────

    def action_confirm_reject(self):
        """
        Applies fm_comment to each pending request and calls action_reject().

        Steps:
          1. SoD guard (Finance only).
          2. Filter to pending_fm records only — silently skip others.
          3. Write fm_comment on each (still in pending_fm → write() guard passes).
          4. Call action_reject() — it re-validates comment and transitions state.
          5. Return display_notification + close dialog.

        Transaction safety:
          All writes happen in the same ORM transaction.
          Any single failure rolls back the entire operation.
        """
        self.ensure_one()

        if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
            raise AccessError("Only Finance can bulk-reject limit change requests.")

        if not self.fm_comment or not self.fm_comment.strip():
            raise UserError("Rejection reason is required before rejecting.")

        pending = self.request_ids.filtered(lambda r: r.state == 'pending_fm')
        if not pending:
            raise UserError(
                "None of the selected records are in 'Pending FM Approval' state.\n"
                "Only pending requests can be rejected."
            )

        rejected_refs = []
        errors = []

        for req in pending:
            try:
                # Write comment first — record is still pending_fm, write() guard passes
                req.sudo().write({'fm_comment': self.fm_comment})
                # action_reject() re-reads fm_comment, validates, transitions to 'rejected'
                req.action_reject()
                rejected_refs.append(req.name)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{req.name}: {exc}")

        skipped = self.skipped_count

        if errors:
            raise UserError(
                f"Rejection failed for {len(errors)} request(s):\n\n"
                + "\n".join(errors)
                + (f"\n\n{len(rejected_refs)} request(s) were rejected before the failure." if rejected_refs else "")
            )

        # Build success notification message
        msg_parts = [f"❌ {len(rejected_refs)} request(s) rejected successfully."]
        if skipped:
            msg_parts.append(f"{skipped} record(s) skipped (not in Pending FM state).")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Rejection Complete',
                'message': ' '.join(msg_parts),
                'type': 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }