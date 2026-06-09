# from odoo import models, fields, api
# from odoo.exceptions import UserError, AccessError, ValidationError
# from markupsafe import Markup

# class ClmLimitChangeRequest(models.Model):
#     """
#     Per-Bucket Credit Limit Change Request — clm.limit.change.request

#     ── Design ───────────────────────────────────────────────────────────────
#     One request  = one bucket = one customer.
#     CCM selects the customer and the specific bucket they want to change,
#     enters the proposed limit and justification, then submits to Finance.
#     Finance reviews and approves or rejects from the form view.
#     Bulk approve / bulk reject are available from the list view (Finance only).

#     ── State Machine ─────────────────────────────────────────────────────────
#       draft  → pending_fm  : CCM submits
#       pending_fm → approved : Finance approves  → limit written to partner
#       pending_fm → rejected : Finance rejects   → no limit change (comment required)
#       draft  → cancelled   : CCM cancels before submission

#     ── SoD ──────────────────────────────────────────────────────────────────
#       Create / submit / cancel  : CCM only
#       Approve / reject          : Finance only

#     ── Constraint: one active request per partner+bucket ────────────────────
#     A second active (draft or pending_fm) request for the same customer AND
#     same bucket is blocked. Different buckets for the same customer are allowed
#     simultaneously.

#     ── Write Protection ─────────────────────────────────────────────────────
#     Records in terminal states (approved / rejected / cancelled) are immutable.
#     self.env.su bypasses this (used internally by sudo() calls).

#     ── Limit Write Guard ────────────────────────────────────────────────────
#     action_approve() writes via clm_bypass_limit_protection=True context to
#     pass res.partner.write() protection on limit fields.
#     """

#     _name = 'clm.limit.change.request'
#     _description = 'CLM Bucket Limit Change Request'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _order = 'create_date desc'
#     _rec_name = 'name'

#     # ── Bucket → partner field name maps ─────────────────────────────────────
#     # Class-level so res_partner_extended and other callers can reference them.

#     _LIMIT_FIELD_MAP = {
#         'proforma': 'clm_proforma_limit',
#         'bucket1':  'clm_bucket_1_limit',
#         'bucket2':  'clm_bucket_2_limit',
#         'bucket3':  'clm_bucket_3_limit',
#         'bucket4':  'clm_bucket_4_limit',
#     }

#     _BALANCE_FIELD_MAP = {
#         'proforma': 'clm_proforma_balance',
#         'bucket1':  'clm_bucket_1_balance',
#         'bucket2':  'clm_bucket_2_balance',
#         'bucket3':  'clm_bucket_3_balance',
#         'bucket4':  'clm_bucket_4_balance',
#     }

#     # ─────────────────────────────────────────────────────────────────────────
#     # IDENTIFICATION
#     # ─────────────────────────────────────────────────────────────────────────

#     name = fields.Char(
#         string='Reference',
#         readonly=True,
#         default='New',
#         copy=False,
#         index=True,
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # REQUEST DETAILS
#     # ─────────────────────────────────────────────────────────────────────────

#     partner_id = fields.Many2one(
#         'res.partner',
#         string='Customer',
#         required=True,
#         ondelete='restrict',
#         tracking=True,
#         index=True,
#     )
#     bucket = fields.Selection(
#         selection=[
#             ('proforma', 'Proforma Invoice'),
#             ('bucket1',  'Bucket 1'),
#             ('bucket2',  'Bucket 2'),
#             ('bucket3',  'Bucket 3'),
#             ('bucket4',  'Bucket 4'),
#         ],
#         string='Bucket',
#         required=True,
#         tracking=True,
#     )
#     currency_id = fields.Many2one(
#         'res.currency',
#         default=lambda self: self.env.company.currency_id,
#     )

#     # ── Live read-only info — always fresh from the partner ──────────────────

#     current_limit = fields.Monetary(
#         string='Current Limit',
#         compute='_compute_current_values',
#         currency_field='currency_id',
#         help='Live value from the partner. Always recomputed — never stale.',
#     )
#     current_exposure = fields.Monetary(
#         string='Current Exposure',
#         compute='_compute_current_values',
#         currency_field='currency_id',
#         help='Live exposure (sum of sale orders in this bucket stage).',
#     )
#     proposed_limit = fields.Monetary(
#         string='Proposed Limit',
#         required=True,
#         currency_field='currency_id',
#         tracking=True,
#         help='The new limit value the CCM is requesting.',
#     )
#     justification = fields.Text(
#         string='Justification',
#         required=True,
#         help='Business reason for this limit change.',
#     )

#     # ── Auto-classification ──────────────────────────────────────────────────

#     request_type = fields.Selection(
#         selection=[
#             ('freeze_resolution', 'Freeze Resolution'),
#             ('standard_increase', 'Standard Increase'),
#         ],
#         string='Request Type',
#         compute='_compute_request_type',
#         store=True,
#         tracking=True,
#         index=True,
#         help=(
#             'freeze_resolution: current exposure exceeds the configured limit.\n'
#             'standard_increase: no active breach — proactive increase.'
#         ),
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # WORKFLOW STATE
#     # ─────────────────────────────────────────────────────────────────────────

#     state = fields.Selection(
#         selection=[
#             ('draft',      'Draft'),
#             ('pending_fm', 'Pending FM Approval'),
#             ('approved',   'Approved'),
#             ('rejected',   'Rejected'),
#             ('cancelled',  'Cancelled'),
#         ],
#         string='Status',
#         default='draft',
#         readonly=True,
#         tracking=True,
#         index=True,
#         copy=False,
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # AUDIT TRAIL — All set by system, never editable by users
#     # ─────────────────────────────────────────────────────────────────────────

#     initiated_by = fields.Many2one(
#         'res.users',
#         string='Initiated By',
#         readonly=True,
#         copy=False,
#         index=True,
#     )
#     submitted_date = fields.Datetime(
#         string='Submitted On',
#         readonly=True,
#         copy=False,
#     )
#     reviewed_by = fields.Many2one(
#         'res.users',
#         string='Reviewed By',
#         readonly=True,
#         copy=False,
#         tracking=True,
#     )
#     reviewed_date = fields.Datetime(
#         string='Reviewed On',
#         readonly=True,
#         copy=False,
#     )
#     previous_limit = fields.Monetary(
#         string='Previous Limit (at Approval)',
#         readonly=True,
#         copy=False,
#         currency_field='currency_id',
#         help='Captured at the moment FM approves. Immutable audit snapshot.',
#     )
#     fm_comment = fields.Text(
#         string='Finance Manager Comment',
#         copy=False,
#         tracking=True,
#         help='Required for rejection. Optional for approval.',
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # COMPUTE
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.depends('partner_id', 'bucket')
#     def _compute_current_values(self):
#         for rec in self:
#             if rec.partner_id and rec.bucket:
#                 rec.current_limit = getattr(
#                     rec.partner_id, self._LIMIT_FIELD_MAP[rec.bucket], 0.0
#                 )
#                 rec.current_exposure = getattr(
#                     rec.partner_id, self._BALANCE_FIELD_MAP[rec.bucket], 0.0
#                 )
#             else:
#                 rec.current_limit = 0.0
#                 rec.current_exposure = 0.0

#     @api.depends('current_exposure', 'current_limit')
#     def _compute_request_type(self):
#         for rec in self:
#             rec.request_type = (
#                 'freeze_resolution'
#                 if rec.current_limit > 0.0 and rec.current_exposure > rec.current_limit
#                 else 'standard_increase'
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # CONSTRAINTS
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.constrains('proposed_limit')
#     def _check_proposed_limit_not_negative(self):
#         for rec in self:
#             if rec.proposed_limit < 0:
#                 bucket_label = dict(
#                     self._fields['bucket'].selection
#                 ).get(rec.bucket, rec.bucket or 'Unknown')
#                 raise ValidationError(
#                     f"Proposed limit cannot be negative — {bucket_label}."
#                 )

#     @api.constrains('partner_id', 'bucket', 'state')
#     def _check_unique_active_per_bucket(self):
#         """
#         Prevent two active (draft or pending_fm) requests for the
#         same customer + same bucket at the same time.

#         Different buckets for the same customer are allowed in parallel.
#         This constraint fires when a record is created or its state changes.
#         """
#         active_states = ('draft', 'pending_fm')
#         bucket_labels = dict(self._fields['bucket'].selection)

#         for rec in self:
#             if rec.state not in active_states:
#                 continue
#             if not rec.bucket:
#                 continue

#             duplicate = self.search([
#                 ('partner_id', '=', rec.partner_id.id),
#                 ('bucket',     '=', rec.bucket),
#                 ('state',      'in', active_states),
#                 ('id',         '!=', rec.id),
#             ], limit=1)

#             if duplicate:
#                 state_label = dict(self._fields['state'].selection).get(
#                     duplicate.state, duplicate.state
#                 )
#                 raise ValidationError(
#                     f"An active request already exists for this bucket.\n\n"
#                     f"Customer    : {rec.partner_id.name}\n"
#                     f"Bucket      : {bucket_labels.get(rec.bucket, rec.bucket)}\n"
#                     f"Request     : {duplicate.name}  ({state_label})\n\n"
#                     f"Resolve or cancel the existing request before creating a new one."
#                 )

#     # ─────────────────────────────────────────────────────────────────────────
#     # WRITE PROTECTION — Terminal states are immutable
#     # ─────────────────────────────────────────────────────────────────────────

#     def write(self, vals):
#         terminal = ('approved', 'rejected', 'cancelled')
#         for rec in self:
#             if rec.state in terminal and not self.env.su:
#                 raise AccessError(
#                     f"Request {rec.name} is in a terminal state "
#                     f"({rec.state}) and cannot be modified."
#                 )
#         return super().write(vals)

#     # ─────────────────────────────────────────────────────────────────────────
#     # ORM OVERRIDES
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.model_create_multi
#     def create(self, vals_list):
#         """
#         SoD: Only CCM may create requests.
#         Sequence assigned on creation.
#         initiated_by set to current user for full audit trail.
#         """
#         self._assert_group(
#             'zencore_groups.group_zencore_clm_ccm',
#             'create limit change requests',
#         )
#         for vals in vals_list:
#             if vals.get('name', 'New') == 'New':
#                 vals['name'] = (
#                     self.env['ir.sequence'].next_by_code('clm.limit.change.request')
#                     or 'New'
#                 )
#             vals['initiated_by'] = self.env.uid
#         return super().create(vals_list)

#     # ─────────────────────────────────────────────────────────────────────────
#     # INDIVIDUAL WORKFLOW ACTIONS
#     # ─────────────────────────────────────────────────────────────────────────

#     def action_submit_to_fm(self):
#         """
#         CCM submits for FM review. draft → pending_fm.

#         Validates:
#           - proposed_limit differs from current_limit (no no-op submissions)
#           - record is still in draft state

#         Schedules a mail.activity on the first Finance Manager found.
#         """
#         self._assert_group(
#             'zencore_groups.group_zencore_clm_ccm',
#             'submit limit change requests',
#         )
#         for rec in self:
#             if rec.state != 'draft':
#                 raise UserError(
#                     f"Only draft requests can be submitted. "
#                     f"State: {rec.state} ({rec.name})"
#                 )
#             if abs(rec.proposed_limit - rec.current_limit) <= 0.001:
#                 raise UserError(
#                     "Cannot submit — the Proposed Limit is the same as the Current Limit.\n"
#                     "Edit the Proposed Limit before submitting."
#                 )

#             bucket_label = dict(
#                 self._fields['bucket'].selection
#             ).get(rec.bucket, rec.bucket or '?')

#             rec.write({
#                 'state': 'pending_fm',
#                 'submitted_date': fields.Datetime.now(),
#             })

#             rec.message_post(
#                 body=Markup(
#                     "<b>📋 Submitted for FM Approval</b><br/>"
#                     "Submitted by  : {user}<br/>"
#                     "Customer      : {customer}<br/>"
#                     "Bucket        : {bucket}<br/>"
#                     "Current Limit : {cur:,.2f}<br/>"
#                     "Proposed Limit: {prop:,.2f}<br/>"
#                     "Request Type  : {rtype}{freeze}"
#                 ).format(
#                     user=self.env.user.name,
#                     customer=rec.partner_id.name,
#                     bucket=bucket_label,
#                     cur=rec.current_limit,
#                     prop=rec.proposed_limit,
#                     rtype=dict(self._fields['request_type'].selection).get(
#                         rec.request_type, ''
#                     ),
#                     freeze=Markup(
#                         ' <span style="color:var(--color-text-danger)">⚠ Freeze</span>'
#                     ) if rec.request_type == 'freeze_resolution' else Markup(''),
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#             # Notify Finance Manager
#             finance_group = self.env.ref(
#                 'zencore_groups.group_zencore_clm_finance',
#                 raise_if_not_found=False,
#             )
#             if finance_group:
#                 fm_user = self.env['res.users'].search([
#                     ('group_ids', 'in', [finance_group.id]),  # Odoo 19: group_ids
#                     ('share', '=', False),
#                     ('active', '=', True),
#                 ], limit=1)
#                 if fm_user:
#                     rec.activity_schedule(
#                         'mail.mail_activity_data_todo',
#                         user_id=fm_user.id,
#                         note=(
#                             f"CLM request {rec.name} from {self.env.user.name} "
#                             f"for {rec.partner_id.name} — {bucket_label}. "
#                             f"Please review."
#                         ),
#                     )

#     def action_approve(self):
#         """
#         Finance Manager approves. pending_fm → approved.

#         Writes proposed_limit directly to the partner for the selected bucket.
#         Uses clm_bypass_limit_protection context to pass res.partner.write() guard.
#         Captures previous_limit for immutable audit trail.
#         Posts approval note on both the request and the partner chatter.
#         """
#         self._assert_group(
#             'zencore_groups.group_zencore_clm_finance',
#             'approve limit change requests',
#         )
#         for rec in self:
#             if rec.state != 'pending_fm':
#                 raise UserError(
#                     f"Only pending requests can be approved. "
#                     f"State: {rec.state} ({rec.name})"
#                 )

#             limit_field = self._LIMIT_FIELD_MAP[rec.bucket]
#             prev = getattr(rec.partner_id, limit_field, 0.0)

#             # Write new limit — bypass the res.partner write() protection
#             rec.partner_id.with_context(
#                 clm_bypass_limit_protection=True
#             ).write({limit_field: rec.proposed_limit})

#             rec.sudo().write({
#                 'state':          'approved',
#                 'previous_limit': prev,
#                 'reviewed_by':    self.env.uid,
#                 'reviewed_date':  fields.Datetime.now(),
#             })
#             rec.activity_ids.action_done()

#             bucket_label = dict(
#                 self._fields['bucket'].selection
#             ).get(rec.bucket, rec.bucket or '?')

#             approval_body = Markup(
#                 "<b>✅ Approved by {user}</b><br/>"
#                 "Customer      : {customer}<br/>"
#                 "Bucket        : {bucket}<br/>"
#                 "Previous Limit: {prev:,.2f}<br/>"
#                 "New Limit     : {new:,.2f}<br/>"
#                 "Comment       : {comment}"
#             ).format(
#                 user=self.env.user.name,
#                 customer=rec.partner_id.name,
#                 bucket=bucket_label,
#                 prev=prev,
#                 new=rec.proposed_limit,
#                 comment=rec.fm_comment or '—',
#             )

#             rec.message_post(body=approval_body, subtype_xmlid='mail.mt_note')

#             # Cross-object audit: post on partner too
#             rec.partner_id.message_post(
#                 body=Markup(
#                     "<b>💳 Credit Limit Updated</b><br/>"
#                     "Request : {ref}<br/>"
#                     "Approved by : {user}<br/>"
#                     "Bucket  : {bucket}<br/>"
#                     "{prev:,.2f} → {new:,.2f}"
#                 ).format(
#                     ref=rec.name,
#                     user=self.env.user.name,
#                     bucket=bucket_label,
#                     prev=prev,
#                     new=rec.proposed_limit,
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#     def action_reject(self):
#         """
#         Finance Manager rejects. pending_fm → rejected.

#         fm_comment is REQUIRED — enforced both here and in the bulk wizard.
#         Terminal state — the limit is NOT changed. Record cannot be reopened.
#         """
#         self._assert_group(
#             'zencore_groups.group_zencore_clm_finance',
#             'reject limit change requests',
#         )
#         for rec in self:
#             if rec.state != 'pending_fm':
#                 raise UserError(
#                     f"Only pending requests can be rejected. "
#                     f"State: {rec.state} ({rec.name})"
#                 )
#             if not rec.fm_comment or not rec.fm_comment.strip():
#                 raise UserError(
#                     "A Finance Manager comment is required before rejecting.\n"
#                     "Enter the rejection reason in the FM Comment field."
#                 )

#             bucket_label = dict(
#                 self._fields['bucket'].selection
#             ).get(rec.bucket, rec.bucket or '?')

#             rec.write({
#                 'state':         'rejected',
#                 'reviewed_by':   self.env.uid,
#                 'reviewed_date': fields.Datetime.now(),
#             })
#             rec.activity_ids.action_done()
#             rec.message_post(
#                 body=Markup(
#                     "<b>❌ Rejected by {user}</b><br/>"
#                     "Customer: {customer}<br/>"
#                     "Bucket  : {bucket}<br/>"
#                     "Reason  : {reason}"
#                 ).format(
#                     user=self.env.user.name,
#                     customer=rec.partner_id.name,
#                     bucket=bucket_label,
#                     reason=rec.fm_comment,
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#     def action_cancel(self):
#         """
#         CCM cancels a draft before submission. draft → cancelled.
#         Terminal state — cannot be reopened.
#         Releases the bucket slot immediately so a new request can be created.
#         """
#         self._assert_group(
#             'zencore_groups.group_zencore_clm_ccm',
#             'cancel limit change requests',
#         )
#         for rec in self:
#             if rec.state != 'draft':
#                 raise UserError(
#                     f"Only draft requests can be cancelled. "
#                     f"State: {rec.state} ({rec.name})"
#                 )
#             bucket_label = dict(
#                 self._fields['bucket'].selection
#             ).get(rec.bucket, rec.bucket or '?')

#             rec.write({'state': 'cancelled'})
#             rec.message_post(
#                 body=Markup(
#                     "<b>🚫 Cancelled by {user}</b><br/>"
#                     "Request {ref} ({bucket}) was cancelled before FM submission."
#                 ).format(
#                     user=self.env.user.name,
#                     ref=rec.name,
#                     bucket=bucket_label,
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # BULK WORKFLOW ACTIONS — Finance-only, bound to list view
#     # Appear in the Action dropdown when Finance selects multiple records.
#     # ─────────────────────────────────────────────────────────────────────────

#     def action_bulk_approve(self):
#         """
#         Finance: bulk-approve all selected pending_fm requests.

#         Calls action_approve() on each pending record — full per-record audit
#         trail and limit write happen exactly as in the single-approve flow.

#         Non-pending records in the selection are silently skipped.
#         Any failure on one record rolls back the entire transaction.
#         """
#         self._assert_group(
#             'zencore_groups.group_zencore_clm_finance',
#             'bulk approve limit change requests',
#         )
#         pending = self.filtered(lambda r: r.state == 'pending_fm')
#         if not pending:
#             raise UserError(
#                 "No 'Pending FM Approval' requests found in the selection.\n"
#                 "Only pending requests can be approved."
#             )

#         approved = []
#         errors = []
#         for rec in pending:
#             try:
#                 rec.action_approve()
#                 approved.append(rec.name)
#             except Exception as exc:  # noqa: BLE001
#                 errors.append(f"  • {rec.name}: {exc}")

#         if errors:
#             raise UserError(
#                 f"Bulk approval failed for {len(errors)} request(s):\n\n"
#                 + "\n".join(errors)
#                 + (
#                     f"\n\n✅ {len(approved)} request(s) approved before the failure."
#                     if approved else ""
#                 )
#             )

#         skipped = len(self) - len(pending)
#         msg = f"✅ {len(approved)} request(s) approved successfully."
#         if skipped:
#             msg += f" {skipped} skipped (not in Pending FM state)."

#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': 'Bulk Approval Complete',
#                 'message': msg,
#                 'type': 'success',
#                 'sticky': False,
#             },
#         }

#     def action_open_bulk_reject_wizard(self):
#         """
#         Finance: open the bulk-reject wizard for all selected pending_fm requests.

#         A wizard is required because action_reject() enforces a non-empty
#         fm_comment. The wizard collects one shared comment before any writes occur.
#         Non-pending records are passed to the wizard but silently excluded by it.
#         """
#         self._assert_group(
#             'zencore_groups.group_zencore_clm_finance',
#             'bulk reject limit change requests',
#         )
#         pending = self.filtered(lambda r: r.state == 'pending_fm')
#         if not pending:
#             raise UserError(
#                 "No 'Pending FM Approval' requests found in the selection.\n"
#                 "Only pending requests can be rejected."
#             )

#         wizard = self.env['clm.bulk.reject.wizard'].create({
#             'request_ids': [fields.Command.set(pending.ids)],
#         })
#         return {
#             'type': 'ir.actions.act_window',
#             'res_model': 'clm.bulk.reject.wizard',
#             'res_id': wizard.id,
#             'view_mode': 'form',
#             'target': 'new',
#             'name': f'Reject {len(pending)} Request(s)',
#         }

#     # ─────────────────────────────────────────────────────────────────────────
#     # PRIVATE HELPERS
#     # ─────────────────────────────────────────────────────────────────────────

#     def _assert_group(self, group_xml_id, action_label):
#         """Raises AccessError if current user is missing the required group."""
#         if not self.env.user.has_group(group_xml_id):
#             group = self.env.ref(group_xml_id, raise_if_not_found=False)
#             raise AccessError(
#                 f"You do not have permission to {action_label}.\n"
#                 f"Required group: {group.full_name if group else group_xml_id}"
#             )

from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError, ValidationError
from markupsafe import Markup


class ClmLimitChangeRequest(models.Model):
    """
    Per-Bucket Credit Limit Change Request — clm.limit.change.request

    ── Design ───────────────────────────────────────────────────────────────
    One request = one bucket = one customer.
    CCM selects the customer and the specific bucket, enters the proposed
    limit and justification, then submits to Finance for approval.

    ── State Machine ─────────────────────────────────────────────────────────
      draft → pending_fm  : CCM submits
      pending_fm → approved : Finance approves  → limit written to partner
      pending_fm → rejected : Finance rejects   → no limit change
      draft → cancelled    : CCM cancels before submission

    ── SoD ──────────────────────────────────────────────────────────────────
      Create / submit / cancel : CCM only
      Approve / reject         : Finance only

    ── Bucket 5 handling ────────────────────────────────────────────────────
    Bucket 5 (Overdue) is included as a requestable bucket.
    However, its request_type is ALWAYS 'standard_increase' — even when
    exposure exceeds the limit — because Bucket 5 does NOT trigger credit
    freeze (SRS §6.1). The limit exists for monitoring/reporting only.
    """

    _name = 'clm.limit.change.request'
    _description = 'CLM Bucket Limit Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # ── Bucket → partner field maps ───────────────────────────────────────────

    _LIMIT_FIELD_MAP = {
        'proforma': 'clm_proforma_limit',
        'bucket1':  'clm_bucket_1_limit',
        'bucket2':  'clm_bucket_2_limit',
        'bucket3':  'clm_bucket_3_limit',
        'bucket4':  'clm_bucket_4_limit',
        'bucket5':  'clm_bucket_5_limit',
    }

    _BALANCE_FIELD_MAP = {
        'proforma': 'clm_proforma_balance',
        'bucket1':  'clm_bucket_1_balance',
        'bucket2':  'clm_bucket_2_balance',
        'bucket3':  'clm_bucket_3_balance',
        'bucket4':  'clm_bucket_4_balance',
        'bucket5':  'clm_bucket_5_balance',
    }

    # ─────────────────────────────────────────────────────────────────────────
    # IDENTIFICATION
    # ─────────────────────────────────────────────────────────────────────────

    name = fields.Char(
        string='Reference',
        readonly=True,
        default='New',
        copy=False,
        index=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # REQUEST DETAILS
    # ─────────────────────────────────────────────────────────────────────────

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
    )
    bucket = fields.Selection(
        selection=[
            ('proforma', 'Proforma Invoice'),
            ('bucket1',  'Bucket 1 — Delivered, Not Invoiced'),
            ('bucket2',  'Bucket 2 — Invoiced, Awaiting Customer Acceptance'),
            ('bucket3',  'Bucket 3 — Customer Accepted, Awaiting Bank Acceptance'),
            ('bucket4',  'Bucket 4 — Bank Accepted, Payment Pending'),
            ('bucket5',  'Bucket 5 — Overdue (Monitoring Only)'),
        ],
        string='Bucket',
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ── Live read-only values from partner ───────────────────────────────────

    current_limit = fields.Monetary(
        string='Current Limit',
        compute='_compute_current_values',
        currency_field='currency_id',
        help='Live value from the partner. Always recomputed.',
    )
    current_exposure = fields.Monetary(
        string='Current Exposure',
        compute='_compute_current_values',
        currency_field='currency_id',
        help='Live exposure in the selected bucket.',
    )
    proposed_limit = fields.Monetary(
        string='Proposed Limit',
        required=True,
        currency_field='currency_id',
        tracking=True,
    )
    justification = fields.Text(
        string='Justification',
        required=True,
    )

    # ── Auto-classification ──────────────────────────────────────────────────

    request_type = fields.Selection(
        selection=[
            ('freeze_resolution', 'Freeze Resolution'),
            ('standard_increase', 'Standard Increase'),
        ],
        string='Request Type',
        compute='_compute_request_type',
        store=True,
        tracking=True,
        index=True,
        help=(
            'freeze_resolution: PI–Bucket 4 exposure exceeds the limit (causes freeze).\n'
            'standard_increase: no active freeze-triggering breach.\n'
            'NOTE: Bucket 5 requests are always standard_increase (no freeze per SRS §6.1).'
        ),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # WORKFLOW STATE
    # ─────────────────────────────────────────────────────────────────────────

    state = fields.Selection(
        selection=[
            ('draft',      'Draft'),
            ('pending_fm', 'Pending FM Approval'),
            ('approved',   'Approved'),
            ('rejected',   'Rejected'),
            ('cancelled',  'Cancelled'),
        ],
        string='Status',
        default='draft',
        readonly=True,
        tracking=True,
        index=True,
        copy=False,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # AUDIT TRAIL
    # ─────────────────────────────────────────────────────────────────────────

    initiated_by = fields.Many2one('res.users', string='Initiated By', readonly=True, copy=False, index=True)
    submitted_date = fields.Datetime(string='Submitted On', readonly=True, copy=False)
    reviewed_by = fields.Many2one('res.users', string='Reviewed By', readonly=True, copy=False, tracking=True)
    reviewed_date = fields.Datetime(string='Reviewed On', readonly=True, copy=False)
    previous_limit = fields.Monetary(
        string='Previous Limit (at Approval)',
        readonly=True,
        copy=False,
        currency_field='currency_id',
        help='Captured at moment of FM approval. Immutable audit snapshot.',
    )
    fm_comment = fields.Text(
        string='Finance Manager Comment',
        copy=False,
        tracking=True,
        help='Required for rejection. Optional for approval.',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('partner_id', 'bucket')
    def _compute_current_values(self):
        for rec in self:
            if rec.partner_id and rec.bucket:
                rec.current_limit = getattr(
                    rec.partner_id, self._LIMIT_FIELD_MAP[rec.bucket], 0.0
                )
                rec.current_exposure = getattr(
                    rec.partner_id, self._BALANCE_FIELD_MAP[rec.bucket], 0.0
                )
            else:
                rec.current_limit = 0.0
                rec.current_exposure = 0.0

    @api.depends('current_exposure', 'current_limit', 'bucket')
    def _compute_request_type(self):
        for rec in self:
            # Bucket 5 does NOT cause freeze (SRS §6.1) → always standard_increase
            if rec.bucket == 'bucket5':
                rec.request_type = 'standard_increase'
            else:
                rec.request_type = (
                    'freeze_resolution'
                    if rec.current_limit > 0.0 and rec.current_exposure > rec.current_limit
                    else 'standard_increase'
                )

    # ─────────────────────────────────────────────────────────────────────────
    # CONSTRAINTS
    # ─────────────────────────────────────────────────────────────────────────

    @api.constrains('proposed_limit')
    def _check_proposed_limit_not_negative(self):
        for rec in self:
            if rec.proposed_limit < 0:
                bucket_label = dict(
                    self._fields['bucket'].selection
                ).get(rec.bucket, rec.bucket or 'Unknown')
                raise ValidationError(
                    f"Proposed limit cannot be negative — {bucket_label}."
                )

    @api.constrains('partner_id', 'bucket', 'state')
    def _check_unique_active_per_bucket(self):
        """
        One active (draft or pending_fm) request per partner+bucket at a time.
        Different buckets for the same partner are allowed in parallel.
        """
        active_states = ('draft', 'pending_fm')
        bucket_labels = dict(self._fields['bucket'].selection)

        for rec in self:
            if rec.state not in active_states or not rec.bucket:
                continue

            duplicate = self.search([
                ('partner_id', '=', rec.partner_id.id),
                ('bucket',     '=', rec.bucket),
                ('state',      'in', active_states),
                ('id',         '!=', rec.id),
            ], limit=1)

            if duplicate:
                state_label = dict(self._fields['state'].selection).get(
                    duplicate.state, duplicate.state
                )
                raise ValidationError(
                    f"An active request already exists for this bucket.\n\n"
                    f"Customer    : {rec.partner_id.name}\n"
                    f"Bucket      : {bucket_labels.get(rec.bucket, rec.bucket)}\n"
                    f"Request     : {duplicate.name}  ({state_label})\n\n"
                    f"Resolve or cancel the existing request before creating a new one."
                )

    # ─────────────────────────────────────────────────────────────────────────
    # WRITE PROTECTION — Terminal states are immutable
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, vals):
        terminal = ('approved', 'rejected', 'cancelled')
        for rec in self:
            if rec.state in terminal and not self.env.su:
                raise AccessError(
                    f"Request {rec.name} is in terminal state "
                    f"({rec.state}) and cannot be modified."
                )
        return super().write(vals)

    # ─────────────────────────────────────────────────────────────────────────
    # ORM OVERRIDES
    # ─────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        self._assert_group('zencore_groups.group_zencore_clm_ccm', 'create limit change requests')
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('clm.limit.change.request') or 'New'
                )
            vals['initiated_by'] = self.env.uid
        return super().create(vals_list)

    # ─────────────────────────────────────────────────────────────────────────
    # INDIVIDUAL WORKFLOW ACTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def action_submit_to_fm(self):
        """CCM submits for FM review. draft → pending_fm."""
        self._assert_group('zencore_groups.group_zencore_clm_ccm', 'submit limit change requests')
        for rec in self:
            if rec.state != 'draft':
                raise UserError(f"Only draft requests can be submitted. State: {rec.state}")
            if abs(rec.proposed_limit - rec.current_limit) <= 0.001:
                raise UserError(
                    "Cannot submit — the Proposed Limit is the same as the Current Limit.\n"
                    "Edit the Proposed Limit before submitting."
                )

            bucket_label = dict(self._fields['bucket'].selection).get(rec.bucket, rec.bucket or '?')

            rec.write({'state': 'pending_fm', 'submitted_date': fields.Datetime.now()})

            rec.message_post(
                body=Markup(
                    "<b>📋 Submitted for FM Approval</b><br/>"
                    "Submitted by   : {user}<br/>"
                    "Customer       : {customer}<br/>"
                    "Bucket         : {bucket}<br/>"
                    "Current Limit  : {cur:,.2f}<br/>"
                    "Proposed Limit : {prop:,.2f}<br/>"
                    "Request Type   : {rtype}{freeze}"
                ).format(
                    user=self.env.user.name,
                    customer=rec.partner_id.name,
                    bucket=bucket_label,
                    cur=rec.current_limit,
                    prop=rec.proposed_limit,
                    rtype=dict(self._fields['request_type'].selection).get(rec.request_type, ''),
                    freeze=Markup(
                        ' <span style="color:var(--color-text-danger)">⚠ Freeze Active</span>'
                    ) if rec.request_type == 'freeze_resolution' else Markup(''),
                ),
                subtype_xmlid='mail.mt_note',
            )

            finance_group = self.env.ref('zencore_groups.group_zencore_clm_finance', raise_if_not_found=False)
            if finance_group:
                fm_user = self.env['res.users'].search([
                    ('group_ids', 'in', [finance_group.id]),
                    ('share', '=', False),
                    ('active', '=', True),
                ], limit=1)
                if fm_user:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=fm_user.id,
                        note=(
                            f"CLM request {rec.name} from {self.env.user.name} "
                            f"for {rec.partner_id.name} — {bucket_label}. Please review."
                        ),
                    )

    def action_approve(self):
        """Finance Manager approves. pending_fm → approved. Writes limit to partner."""
        self._assert_group('zencore_groups.group_zencore_clm_finance', 'approve limit change requests')
        for rec in self:
            if rec.state != 'pending_fm':
                raise UserError(f"Only pending requests can be approved. State: {rec.state}")

            limit_field = self._LIMIT_FIELD_MAP[rec.bucket]
            prev = getattr(rec.partner_id, limit_field, 0.0)

            rec.partner_id.with_context(clm_bypass_limit_protection=True).write(
                {limit_field: rec.proposed_limit}
            )
            rec.sudo().write({
                'state':          'approved',
                'previous_limit': prev,
                'reviewed_by':    self.env.uid,
                'reviewed_date':  fields.Datetime.now(),
            })
            rec.activity_ids.action_done()

            bucket_label = dict(self._fields['bucket'].selection).get(rec.bucket, rec.bucket or '?')
            approval_body = Markup(
                "<b>✅ Approved by {user}</b><br/>"
                "Customer       : {customer}<br/>"
                "Bucket         : {bucket}<br/>"
                "Previous Limit : {prev:,.2f}<br/>"
                "New Limit      : {new:,.2f}<br/>"
                "Comment        : {comment}"
            ).format(
                user=self.env.user.name,
                customer=rec.partner_id.name,
                bucket=bucket_label,
                prev=prev,
                new=rec.proposed_limit,
                comment=rec.fm_comment or '—',
            )
            rec.message_post(body=approval_body, subtype_xmlid='mail.mt_note')
            rec.partner_id.message_post(
                body=Markup(
                    "<b>💳 Credit Limit Updated</b><br/>"
                    "Request    : {ref}<br/>"
                    "Approved by: {user}<br/>"
                    "Bucket     : {bucket}<br/>"
                    "{prev:,.2f} → {new:,.2f}"
                ).format(
                    ref=rec.name,
                    user=self.env.user.name,
                    bucket=bucket_label,
                    prev=prev,
                    new=rec.proposed_limit,
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_reject(self):
        """Finance Manager rejects. pending_fm → rejected. fm_comment required."""
        self._assert_group('zencore_groups.group_zencore_clm_finance', 'reject limit change requests')
        for rec in self:
            if rec.state != 'pending_fm':
                raise UserError(f"Only pending requests can be rejected. State: {rec.state}")
            if not rec.fm_comment or not rec.fm_comment.strip():
                raise UserError(
                    "A Finance Manager comment is required before rejecting.\n"
                    "Enter the rejection reason in the FM Comment field."
                )
            bucket_label = dict(self._fields['bucket'].selection).get(rec.bucket, rec.bucket or '?')
            rec.write({'state': 'rejected', 'reviewed_by': self.env.uid, 'reviewed_date': fields.Datetime.now()})
            rec.activity_ids.action_done()
            rec.message_post(
                body=Markup(
                    "<b>❌ Rejected by {user}</b><br/>"
                    "Customer : {customer}<br/>"
                    "Bucket   : {bucket}<br/>"
                    "Reason   : {reason}"
                ).format(
                    user=self.env.user.name,
                    customer=rec.partner_id.name,
                    bucket=bucket_label,
                    reason=rec.fm_comment,
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_cancel(self):
        """CCM cancels a draft before submission. draft → cancelled."""
        self._assert_group('zencore_groups.group_zencore_clm_ccm', 'cancel limit change requests')
        for rec in self:
            if rec.state != 'draft':
                raise UserError(f"Only draft requests can be cancelled. State: {rec.state}")
            bucket_label = dict(self._fields['bucket'].selection).get(rec.bucket, rec.bucket or '?')
            rec.write({'state': 'cancelled'})
            rec.message_post(
                body=Markup(
                    "<b>🚫 Cancelled by {user}</b><br/>"
                    "Request {ref} ({bucket}) was cancelled before FM submission."
                ).format(user=self.env.user.name, ref=rec.name, bucket=bucket_label),
                subtype_xmlid='mail.mt_note',
            )

    # ─────────────────────────────────────────────────────────────────────────
    # BULK WORKFLOW ACTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def action_bulk_approve(self):
        """Finance: bulk-approve all selected pending_fm requests."""
        self._assert_group('zencore_groups.group_zencore_clm_finance', 'bulk approve limit change requests')
        pending = self.filtered(lambda r: r.state == 'pending_fm')
        if not pending:
            raise UserError("No 'Pending FM Approval' requests found in the selection.")

        approved, errors = [], []
        for rec in pending:
            try:
                rec.action_approve()
                approved.append(rec.name)
            except Exception as exc:
                errors.append(f"  • {rec.name}: {exc}")

        if errors:
            raise UserError(
                f"Bulk approval failed for {len(errors)} request(s):\n\n"
                + "\n".join(errors)
                + (f"\n\n✅ {len(approved)} approved before the failure." if approved else "")
            )

        skipped = len(self) - len(pending)
        msg = f"✅ {len(approved)} request(s) approved successfully."
        if skipped:
            msg += f" {skipped} skipped (not in Pending FM state)."

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Bulk Approval Complete', 'message': msg, 'type': 'success', 'sticky': False},
        }

    def action_open_bulk_reject_wizard(self):
        """Finance: open bulk-reject wizard for selected pending requests."""
        self._assert_group('zencore_groups.group_zencore_clm_finance', 'bulk reject limit change requests')
        pending = self.filtered(lambda r: r.state == 'pending_fm')
        if not pending:
            raise UserError("No 'Pending FM Approval' requests found in the selection.")

        wizard = self.env['clm.bulk.reject.wizard'].create({
            'request_ids': [fields.Command.set(pending.ids)],
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clm.bulk.reject.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'name': f'Reject {len(pending)} Request(s)',
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _assert_group(self, group_xml_id, action_label):
        if not self.env.user.has_group(group_xml_id):
            group = self.env.ref(group_xml_id, raise_if_not_found=False)
            raise AccessError(
                f"You do not have permission to {action_label}.\n"
                f"Required group: {group.full_name if group else group_xml_id}"
            )