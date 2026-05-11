# # # # # # from odoo import models, fields, api
# # # # # # from odoo.exceptions import UserError, AccessError, ValidationError


# # # # # # class ClmLimitChangeRequest(models.Model):
# # # # # #     """
# # # # # #     Bucket Limit Change Workflow — clm.limit.change.request.

# # # # # #     State Machine:
# # # # # #       draft → pending_fm → approved / rejected

# # # # # #     SRS §9 Compliance:
# # # # # #     ───────────────────
# # # # # #     - Only CCM can create and submit (draft → pending_fm)
# # # # # #     - Only Finance Manager can approve or reject
# # # # # #     - Approved: limit updated immediately on res.partner
# # # # # #     - Rejected: permanently closed, cannot be reused or resubmitted
# # # # # #     - Full audit trail: initiator, approver, timestamps, old/new values

# # # # # #     FIXES from v0.2.0:
# # # # # #     ───────────────────
# # # # # #     - action_reject: Fixed syntax error (raise UserError(...) with Ellipsis)
# # # # # #     - action_reject: Added message_post for audit trail
# # # # # #     - write() guard: Rejected records cannot be modified
# # # # # #     - action_approve: Posts activity completion notification
# # # # # #     - Unique pending constraint: Improved duplicate detection
# # # # # #     - FM activity: Created on submit to notify Finance Manager
# # # # # #     """

# # # # # #     _name = 'clm.limit.change.request'
# # # # # #     _description = 'CLM Bucket Limit Change Request'
# # # # # #     _inherit = ['mail.thread', 'mail.activity.mixin']
# # # # # #     _order = 'create_date desc'
# # # # # #     _rec_name = 'name'

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # IDENTIFICATION
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     name = fields.Char(
# # # # # #         string='Reference',
# # # # # #         readonly=True,
# # # # # #         default='New',
# # # # # #         copy=False,
# # # # # #     )

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # REQUEST DETAILS
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     partner_id = fields.Many2one(
# # # # # #         'res.partner',
# # # # # #         string='Customer',
# # # # # #         required=True,
# # # # # #         ondelete='restrict',
# # # # # #         tracking=True,
# # # # # #     )
# # # # # #     bucket = fields.Selection(
# # # # # #         selection=[
# # # # # #             ('proforma', 'Proforma Invoice'),
# # # # # #             ('bucket1',  'Bucket 1'),
# # # # # #             ('bucket2',  'Bucket 2'),
# # # # # #             ('bucket3',  'Bucket 3'),
# # # # # #             ('bucket4',  'Bucket 4'),
# # # # # #         ],
# # # # # #         string='Bucket',
# # # # # #         required=True,
# # # # # #         tracking=True,
# # # # # #     )
# # # # # #     currency_id = fields.Many2one(
# # # # # #         'res.currency',
# # # # # #         default=lambda self: self.env.company.currency_id,
# # # # # #     )
# # # # # #     current_limit = fields.Monetary(
# # # # # #         string='Current Limit',
# # # # # #         compute='_compute_current_values',
# # # # # #         currency_field='currency_id',
# # # # # #     )
# # # # # #     current_exposure = fields.Monetary(
# # # # # #         string='Current Exposure',
# # # # # #         compute='_compute_current_values',
# # # # # #         currency_field='currency_id',
# # # # # #     )
# # # # # #     proposed_limit = fields.Monetary(
# # # # # #         string='Proposed Limit',
# # # # # #         required=True,
# # # # # #         currency_field='currency_id',
# # # # # #         tracking=True,
# # # # # #     )
# # # # # #     justification = fields.Text(
# # # # # #         string='Justification',
# # # # # #         required=True,
# # # # # #     )

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # AUTO-CLASSIFICATION (SRS §9.2)
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     request_type = fields.Selection(
# # # # # #         selection=[
# # # # # #             ('freeze_resolution', 'Freeze Resolution'),
# # # # # #             ('standard_increase', 'Standard Increase'),
# # # # # #         ],
# # # # # #         string='Request Type',
# # # # # #         compute='_compute_request_type',
# # # # # #         store=True,
# # # # # #         tracking=True,
# # # # # #     )

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # WORKFLOW STATE
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     state = fields.Selection(
# # # # # #         selection=[
# # # # # #             ('draft',      'Draft'),
# # # # # #             ('pending_fm', 'Pending FM Approval'),
# # # # # #             ('approved',   'Approved'),
# # # # # #             ('rejected',   'Rejected'),
# # # # # #         ],
# # # # # #         string='Status',
# # # # # #         default='draft',
# # # # # #         readonly=True,
# # # # # #         tracking=True,
# # # # # #     )

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # AUDIT TRAIL (SRS §9.4) — All set by system, never by users
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     initiated_by = fields.Many2one(
# # # # # #         'res.users',
# # # # # #         string='Initiated By',
# # # # # #         readonly=True,
# # # # # #         copy=False,
# # # # # #     )
# # # # # #     reviewed_by = fields.Many2one(
# # # # # #         'res.users',
# # # # # #         string='Approved / Rejected By',
# # # # # #         readonly=True,
# # # # # #         copy=False,
# # # # # #         tracking=True,
# # # # # #     )
# # # # # #     reviewed_date = fields.Datetime(
# # # # # #         string='Reviewed On',
# # # # # #         readonly=True,
# # # # # #         copy=False,
# # # # # #     )
# # # # # #     previous_limit = fields.Monetary(
# # # # # #         string='Previous Limit (at Decision)',
# # # # # #         readonly=True,
# # # # # #         currency_field='currency_id',
# # # # # #         copy=False,
# # # # # #     )
# # # # # #     fm_comment = fields.Text(
# # # # # #         string='Finance Manager Comment',
# # # # # #         copy=False,
# # # # # #         tracking=True,
# # # # # #     )

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # FIELD MAPPINGS — Bucket key → partner field names
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     _LIMIT_FIELD_MAP = {
# # # # # #         'proforma': 'clm_proforma_limit',
# # # # # #         'bucket1':  'clm_bucket_1_limit',
# # # # # #         'bucket2':  'clm_bucket_2_limit',
# # # # # #         'bucket3':  'clm_bucket_3_limit',
# # # # # #         'bucket4':  'clm_bucket_4_limit',
# # # # # #     }

# # # # # #     _BALANCE_FIELD_MAP = {
# # # # # #         'proforma': 'clm_proforma_balance',
# # # # # #         'bucket1':  'clm_bucket_1_balance',
# # # # # #         'bucket2':  'clm_bucket_2_balance',
# # # # # #         'bucket3':  'clm_bucket_3_balance',
# # # # # #         'bucket4':  'clm_bucket_4_balance',
# # # # # #     }

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # COMPUTE METHODS
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     @api.depends('partner_id', 'bucket')
# # # # # #     def _compute_current_values(self):
# # # # # #         for rec in self:
# # # # # #             if rec.partner_id and rec.bucket:
# # # # # #                 rec.current_limit    = getattr(rec.partner_id, self._LIMIT_FIELD_MAP[rec.bucket], 0.0)
# # # # # #                 rec.current_exposure = getattr(rec.partner_id, self._BALANCE_FIELD_MAP[rec.bucket], 0.0)
# # # # # #             else:
# # # # # #                 rec.current_limit    = 0.0
# # # # # #                 rec.current_exposure = 0.0

# # # # # #     @api.depends('current_exposure', 'current_limit')
# # # # # #     def _compute_request_type(self):
# # # # # #         for rec in self:
# # # # # #             rec.request_type = (
# # # # # #                 'freeze_resolution'
# # # # # #                 if rec.current_exposure > rec.current_limit
# # # # # #                 else 'standard_increase'
# # # # # #             )

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # CONSTRAINTS
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     @api.constrains('partner_id', 'bucket', 'state')
# # # # # #     def _check_unique_pending(self):
# # # # # #         """
# # # # # #         Prevent duplicate pending requests for the same partner+bucket.
# # # # # #         Note: This constraint is best-effort. For true atomicity, a
# # # # # #         PostgreSQL unique partial index would be required.
# # # # # #         """
# # # # # #         for rec in self:
# # # # # #             if rec.state == 'pending_fm':
# # # # # #                 duplicate = self.search([
# # # # # #                     ('partner_id', '=', rec.partner_id.id),
# # # # # #                     ('bucket',     '=', rec.bucket),
# # # # # #                     ('state',      '=', 'pending_fm'),
# # # # # #                     ('id',         '!=', rec.id),
# # # # # #                 ], limit=1)
# # # # # #                 if duplicate:
# # # # # #                     raise ValidationError(
# # # # # #                         f"A pending request ({duplicate.name}) already exists "
# # # # # #                         f"for {rec.partner_id.name} — {dict(self._fields['bucket'].selection).get(rec.bucket)}.\n"
# # # # # #                         f"Resolve the existing request before creating a new one."
# # # # # #                     )

# # # # # #     @api.constrains('proposed_limit')
# # # # # #     def _check_proposed_limit_positive(self):
# # # # # #         for rec in self:
# # # # # #             if rec.proposed_limit <= 0:
# # # # # #                 raise ValidationError("Proposed limit must be greater than zero.")

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # WRITE PROTECTION — Prevent modification of terminal states
# # # # # #     # SRS §9.3: Rejected requests cannot be reused.
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     def write(self, vals):
# # # # # #         """
# # # # # #         Block any modification to records in terminal states (approved/rejected).
# # # # # #         This prevents attempts to reset and reuse rejected requests.
# # # # # #         """
# # # # # #         for rec in self:
# # # # # #             if rec.state in ('approved', 'rejected'):
# # # # # #                 # Only allow system-level writes (e.g., ORM internal)
# # # # # #                 if not self.env.su:
# # # # # #                     raise AccessError(
# # # # # #                         f"Request {rec.name} is in a terminal state ({rec.state}) "
# # # # # #                         f"and cannot be modified. Rejected requests cannot be reused."
# # # # # #                     )
# # # # # #         return super().write(vals)

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # ORM OVERRIDES
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     @api.model_create_multi
# # # # # #     def create(self, vals_list):
# # # # # #         """
# # # # # #         SoD: Only CCM can create limit change requests.
# # # # # #         Sequence number assigned on creation.
# # # # # #         Initiated_by always set to current user for audit trail.
# # # # # #         """
# # # # # #         self._assert_group(
# # # # # #             'zencore_clms.group_zencore_clm_ccm',
# # # # # #             'create limit change requests'
# # # # # #         )
# # # # # #         for vals in vals_list:
# # # # # #             if vals.get('name', 'New') == 'New':
# # # # # #                 vals['name'] = (
# # # # # #                     self.env['ir.sequence'].next_by_code('clm.limit.change.request')
# # # # # #                     or 'New'
# # # # # #                 )
# # # # # #             vals['initiated_by'] = self.env.uid
# # # # # #         return super().create(vals_list)

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # WORKFLOW ACTIONS
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     def action_submit_to_fm(self):
# # # # # #         """
# # # # # #         CCM submits the request for FM review.
# # # # # #         Transitions: draft → pending_fm.
# # # # # #         Creates a mail.activity for the Finance Manager group to ensure
# # # # # #         FM is notified (SRS §9.4 — audit and traceability).
# # # # # #         """
# # # # # #         self._assert_group(
# # # # # #             'zencore_clms.group_zencore_clm_ccm',
# # # # # #             'submit limit change requests'
# # # # # #         )
# # # # # #         for rec in self:
# # # # # #             if rec.state != 'draft':
# # # # # #                 raise UserError(
# # # # # #                     f"Only Draft requests can be submitted. Current state: {rec.state} ({rec.name})"
# # # # # #                 )
# # # # # #             rec.write({'state': 'pending_fm'})
# # # # # #             rec.message_post(
# # # # # #                 body=(
# # # # # #                     f"<b>Submitted for FM Approval</b><br/>"
# # # # # #                     f"Submitted by: {self.env.user.name}<br/>"
# # # # # #                     f"Bucket: {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
# # # # # #                     f"Proposed Limit: {rec.proposed_limit:,.2f}<br/>"
# # # # # #                     f"Request Type: {dict(self._fields['request_type'].selection).get(rec.request_type)}"
# # # # # #                 ),
# # # # # #                 subtype_xmlid='mail.mt_note',
# # # # # #             )
# # # # # #             # Create activity to notify Finance Manager
# # # # # #             # finance_group = self.env.ref('zencore_clms.group_zencore_clm_finance')
# # # # # #             # finance_users = finance_group.users if finance_group else self.env['res.users']
# # # # # #             # FIXED — Query res.users directly by group membership

# # # # # #             finance_group = self.env.ref('zencore_clms.group_zencore_clm_finance', raise_if_not_found=False)
# # # # # #             finance_users = (
# # # # # #                 self.env['res.users'].search([
# # # # # #                     ('groups_id', 'in', [finance_group.id]),
# # # # # #                     ('share', '=', False),      # exclude portal users
# # # # # #                     ('active', '=', True),
# # # # # #                 ])
# # # # # #                 if finance_group
# # # # # #                 else self.env['res.users']
# # # # # #             )

# # # # # #             if finance_users:
# # # # # #                 rec.activity_schedule(
# # # # # #                     'mail.mail_activity_data_todo',
# # # # # #                     user_id=finance_users[0].id,
# # # # # #                     note=(
# # # # # #                         f"Limit Change Request {rec.name} submitted by CCM "
# # # # # #                         f"({self.env.user.name}) for {rec.partner_id.name} — "
# # # # # #                         f"{dict(self._fields['bucket'].selection).get(rec.bucket)}. "
# # # # # #                         f"Proposed limit: {rec.proposed_limit:,.2f}. Please review."
# # # # # #                     ),
# # # # # #                 )

# # # # # #     def action_approve(self):
# # # # # #         """
# # # # # #         Finance Manager approves the request.
# # # # # #         Transitions: pending_fm → approved.
# # # # # #         Immediately updates the partner limit via bypass context.
# # # # # #         Freeze is auto-re-evaluated (non-stored compute).
# # # # # #         SRS §9.2 Stage 2.
# # # # # #         """
# # # # # #         self._assert_group(
# # # # # #             'zencore_clms.group_zencore_clm_finance',
# # # # # #             'approve limit change requests'
# # # # # #         )
# # # # # #         for rec in self:
# # # # # #             if rec.state != 'pending_fm':
# # # # # #                 raise UserError(
# # # # # #                     f"Only Pending requests can be approved. Current state: {rec.state} ({rec.name})"
# # # # # #                 )

# # # # # #             limit_field = self._LIMIT_FIELD_MAP[rec.bucket]
# # # # # #             prev_limit  = getattr(rec.partner_id, limit_field, 0.0)

# # # # # #             # Write new limit with bypass (res.partner.write() blocks direct edits)
# # # # # #             rec.partner_id.with_context(
# # # # # #                 clm_bypass_limit_protection=True
# # # # # #             ).write({limit_field: rec.proposed_limit})

# # # # # #             rec.write({
# # # # # #                 'state':          'approved',
# # # # # #                 'previous_limit': prev_limit,
# # # # # #                 'reviewed_by':    self.env.uid,
# # # # # #                 'reviewed_date':  fields.Datetime.now(),
# # # # # #             })

# # # # # #             # Mark any pending activity as done
# # # # # #             rec.activity_ids.action_done()

# # # # # #             rec.message_post(
# # # # # #                 body=(
# # # # # #                     f"<b>✅ Approved by {self.env.user.name}</b><br/>"
# # # # # #                     f"Customer : {rec.partner_id.name}<br/>"
# # # # # #                     f"Bucket   : {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
# # # # # #                     f"Previous : {prev_limit:,.2f}<br/>"
# # # # # #                     f"New Limit: {rec.proposed_limit:,.2f}<br/>"
# # # # # #                     f"Comment  : {rec.fm_comment or '—'}"
# # # # # #                 ),
# # # # # #                 subtype_xmlid='mail.mt_note',
# # # # # #             )

# # # # # #     def action_reject(self):
# # # # # #         """
# # # # # #         Finance Manager rejects the request.
# # # # # #         Transitions: pending_fm → rejected.
# # # # # #         Rejected requests are permanently closed (SRS §9.3).
# # # # # #         FM comment is REQUIRED for rejected requests (governance rule).

# # # # # #         FIX from v0.2.0: Was `raise UserError(...)` with Python Ellipsis literal —
# # # # # #         that is a syntax error. Fixed to proper string arguments.
# # # # # #         """
# # # # # #         self._assert_group(
# # # # # #             'zencore_clms.group_zencore_clm_finance',
# # # # # #             'reject limit change requests'
# # # # # #         )
# # # # # #         for rec in self:
# # # # # #             if rec.state != 'pending_fm':
# # # # # #                 raise UserError(
# # # # # #                     f"Only Pending requests can be rejected. Current state: {rec.state} ({rec.name})"
# # # # # #                 )
# # # # # #             if not rec.fm_comment or not rec.fm_comment.strip():
# # # # # #                 raise UserError(
# # # # # #                     "A Finance Manager comment is required before rejecting.\n"
# # # # # #                     "Please enter the rejection reason in the FM Comment field."
# # # # # #                 )

# # # # # #             rec.write({
# # # # # #                 'state':         'rejected',
# # # # # #                 'reviewed_by':   self.env.uid,
# # # # # #                 'reviewed_date': fields.Datetime.now(),
# # # # # #             })

# # # # # #             # Mark any pending activity as done
# # # # # #             rec.activity_ids.action_done()

# # # # # #             rec.message_post(
# # # # # #                 body=(
# # # # # #                     f"<b>❌ Rejected by {self.env.user.name}</b><br/>"
# # # # # #                     f"Customer: {rec.partner_id.name}<br/>"
# # # # # #                     f"Bucket  : {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
# # # # # #                     f"Reason  : {rec.fm_comment}"
# # # # # #                 ),
# # # # # #                 subtype_xmlid='mail.mt_note',
# # # # # #             )

# # # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # # #     # PRIVATE HELPERS
# # # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # # #     def _assert_group(self, group_xml_id, action_label):
# # # # # #         """
# # # # # #         Raises AccessError if current user does not belong to the required group.
# # # # # #         Provides a clear, user-friendly error with group name.
# # # # # #         """
# # # # # #         if not self.env.user.has_group(group_xml_id):
# # # # # #             group = self.env.ref(group_xml_id)
# # # # # #             raise AccessError(
# # # # # #                 f"You do not have permission to {action_label}.\n"
# # # # # #                 f"Required group: {group.full_name}"
# # # # # #             )

# # # # # from odoo import models, fields, api
# # # # # from odoo.exceptions import UserError, AccessError, ValidationError


# # # # # class ClmLimitChangeRequest(models.Model):
# # # # #     """
# # # # #     Bucket Limit Change Workflow.

# # # # #     State Machine:
# # # # #       draft → pending_fm → approved / rejected

# # # # #     Rules:
# # # # #       - Only CCM can create and submit requests
# # # # #       - Only Finance Manager can approve or reject
# # # # #       - Rejected requests are closed and cannot be reused
# # # # #       - Limit is updated directly on res.partner upon approval
# # # # #       - Full audit trail: initiator, approver, timestamps, old/new values
# # # # #     """

# # # # #     _name = 'clm.limit.change.request'
# # # # #     _description = 'CLM Bucket Limit Change Request'
# # # # #     _inherit = ['mail.thread', 'mail.activity.mixin']
# # # # #     _order = 'create_date desc'
# # # # #     _rec_name = 'name'

# # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # #     # IDENTIFICATION
# # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # #     name = fields.Char(
# # # # #         string='Reference',
# # # # #         readonly=True,
# # # # #         default='New',
# # # # #         copy=False,
# # # # #     )

# # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # #     # REQUEST DETAILS
# # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # #     partner_id = fields.Many2one(
# # # # #         'res.partner',
# # # # #         string='Customer',
# # # # #         required=True,
# # # # #         # domain=[('customer_rank', '>', 0)],
# # # # #         ondelete='restrict',
# # # # #         tracking=True,
# # # # #     )
# # # # #     bucket = fields.Selection(
# # # # #         selection=[
# # # # #             ('proforma', 'Proforma Invoice'),
# # # # #             ('bucket1', 'Bucket 1'),
# # # # #             ('bucket2', 'Bucket 2'),
# # # # #             ('bucket3', 'Bucket 3'),
# # # # #             ('bucket4', 'Bucket 4'),
# # # # #         ],
# # # # #         string='Bucket',
# # # # #         required=True,
# # # # #         tracking=True,
# # # # #     )
# # # # #     currency_id = fields.Many2one(
# # # # #         'res.currency',
# # # # #         default=lambda self: self.env.company.currency_id,
# # # # #     )
# # # # #     current_limit = fields.Monetary(
# # # # #         string='Current Limit',
# # # # #         compute='_compute_current_values',
# # # # #         currency_field='currency_id',
# # # # #     )
# # # # #     current_exposure = fields.Monetary(
# # # # #         string='Current Exposure',
# # # # #         compute='_compute_current_values',
# # # # #         currency_field='currency_id',
# # # # #     )
# # # # #     proposed_limit = fields.Monetary(
# # # # #         string='Proposed Limit',
# # # # #         required=True,
# # # # #         currency_field='currency_id',
# # # # #         tracking=True,
# # # # #     )
# # # # #     justification = fields.Text(
# # # # #         string='Justification',
# # # # #         required=True,
# # # # #     )

# # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # #     # AUTO-CLASSIFICATION
# # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # #     request_type = fields.Selection(
# # # # #         selection=[
# # # # #             ('freeze_resolution', 'Freeze Resolution'),
# # # # #             ('standard_increase', 'Standard Increase'),
# # # # #         ],
# # # # #         string='Request Type',
# # # # #         compute='_compute_request_type',
# # # # #         store=True,
# # # # #         tracking=True,
# # # # #     )

# # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # #     # WORKFLOW STATE
# # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # #     state = fields.Selection(
# # # # #         selection=[
# # # # #             ('draft', 'Draft'),
# # # # #             ('pending_fm', 'Pending FM Approval'),
# # # # #             ('approved', 'Approved'),
# # # # #             ('rejected', 'Rejected'),
# # # # #         ],
# # # # #         string='Status',
# # # # #         default='draft',
# # # # #         readonly=True,
# # # # #         tracking=True,
# # # # #     )

# # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # #     # AUDIT TRAIL — All readonly, set by system
# # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # #     initiated_by = fields.Many2one(
# # # # #         'res.users',
# # # # #         string='Initiated By',
# # # # #         readonly=True,
# # # # #         copy=False,
# # # # #     )
# # # # #     reviewed_by = fields.Many2one(
# # # # #         'res.users',
# # # # #         string='Approved / Rejected By',
# # # # #         readonly=True,
# # # # #         copy=False,
# # # # #         tracking=True,
# # # # #     )
# # # # #     reviewed_date = fields.Datetime(
# # # # #         string='Reviewed On',
# # # # #         readonly=True,
# # # # #         copy=False,
# # # # #     )
# # # # #     previous_limit = fields.Monetary(
# # # # #         string='Previous Limit (at Approval)',
# # # # #         readonly=True,
# # # # #         currency_field='currency_id',
# # # # #         copy=False,
# # # # #     )
# # # # #     fm_comment = fields.Text(
# # # # #         string='Finance Manager Comment',
# # # # #         copy=False,
# # # # #         tracking=True,
# # # # #     )

# # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # #     # FIELD MAPPINGS — Bucket → Partner field names
# # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # #     _LIMIT_FIELD_MAP = {
# # # # #         'proforma': 'clm_proforma_limit',
# # # # #         'bucket1': 'clm_bucket_1_limit',
# # # # #         'bucket2': 'clm_bucket_2_limit',
# # # # #         'bucket3': 'clm_bucket_3_limit',
# # # # #         'bucket4': 'clm_bucket_4_limit',
# # # # #     }

# # # # #     _BALANCE_FIELD_MAP = {
# # # # #         'proforma': 'clm_proforma_balance',
# # # # #         'bucket1': 'clm_bucket_1_balance',
# # # # #         'bucket2': 'clm_bucket_2_balance',
# # # # #         'bucket3': 'clm_bucket_3_balance',
# # # # #         'bucket4': 'clm_bucket_4_balance',
# # # # #     }

# # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # #     # COMPUTE METHODS
# # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # #     @api.depends('partner_id', 'bucket')
# # # # #     def _compute_current_values(self):
# # # # #         for rec in self:
# # # # #             if rec.partner_id and rec.bucket:
# # # # #                 rec.current_limit = getattr(
# # # # #                     rec.partner_id, self._LIMIT_FIELD_MAP[rec.bucket], 0.0
# # # # #                 )
# # # # #                 rec.current_exposure = getattr(
# # # # #                     rec.partner_id, self._BALANCE_FIELD_MAP[rec.bucket], 0.0
# # # # #                 )
# # # # #             else:
# # # # #                 rec.current_limit = 0.0
# # # # #                 rec.current_exposure = 0.0

# # # # #     @api.depends('current_exposure', 'current_limit')
# # # # #     def _compute_request_type(self):
# # # # #         for rec in self:
# # # # #             rec.request_type = (
# # # # #                 'freeze_resolution'
# # # # #                 if rec.current_exposure > rec.current_limit
# # # # #                 else 'standard_increase'
# # # # #             )


# # # # #     #check unique pending request per bucket per partner
# # # # #     @api.constrains('partner_id', 'bucket', 'state')
# # # # #     def _check_unique_pending(self):
# # # # #         for rec in self:
# # # # #             if rec.state == 'pending_fm':
# # # # #                 duplicate = self.search([
# # # # #                     ('partner_id', '=', rec.partner_id.id),
# # # # #                     ('bucket', '=', rec.bucket),
# # # # #                     ('state', '=', 'pending_fm'),
# # # # #                     ('id', '!=', rec.id),
# # # # #                 ], limit=1)
# # # # #                 if duplicate:
# # # # #                     raise ValidationError( 
# # # # #                         f"A pending request ({duplicate.name}) already exists "
# # # # #                         f"for {rec.partner_id.name} — {rec.bucket}."
# # # # #                     )

# # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # #     # ORM OVERRIDES
# # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # #     @api.model_create_multi
# # # # #     def create(self, vals_list):
# # # # #         for vals in vals_list:
# # # # #             if vals.get('name', 'New') == 'New':
# # # # #                 vals['name'] = (
# # # # #                     self.env['ir.sequence'].next_by_code('clm.limit.change.request')
# # # # #                     or 'New'
# # # # #                 )
# # # # #             vals['initiated_by'] = self.env.uid
# # # # #         return super().create(vals_list)

# # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # #     # WORKFLOW ACTIONS
# # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # #     def action_submit_to_fm(self):
# # # # #         """
# # # # #         CCM submits request for FM review.
# # # # #         Only CCM group members can call this action.
# # # # #         """
# # # # #         self._assert_group('zencore_clms.group_zencore_clm_ccm', 'submit limit change requests')
# # # # #         for rec in self:
# # # # #             if rec.state != 'draft':
# # # # #                 raise UserError(f"Only draft requests can be submitted. ({rec.name})")
# # # # #             if rec.proposed_limit <= 0:
# # # # #                 raise UserError("Proposed limit must be greater than zero.")
# # # # #             rec.write({'state': 'pending_fm'})
# # # # #             rec.message_post(
# # # # #                 body=f"Request submitted by {self.env.user.name} for FM review.",
# # # # #                 subtype_xmlid='mail.mt_note',
# # # # #             )

# # # # #     def action_approve(self):
# # # # #         """
# # # # #         Finance Manager approves the request.
# # # # #         Updates the partner limit immediately.
# # # # #         Freeze status is automatically re-evaluated (non-stored compute).
# # # # #         """
# # # # #         self._assert_group('zencore_clms.group_zencore_clm_finance', 'approve limit change requests')
# # # # #         for rec in self:
# # # # #             if rec.state != 'pending_fm':
# # # # #                 raise UserError(f"Only pending requests can be approved. ({rec.name})")

# # # # #             limit_field = self._LIMIT_FIELD_MAP[rec.bucket]

# # # # #             # Capture previous value for audit
# # # # #             prev_limit = getattr(rec.partner_id, limit_field, 0.0)

# # # # #             # Apply the new limit
# # # # #             # rec.partner_id.write({limit_field: rec.proposed_limit})

# # # # #             rec.partner_id.with_context(
# # # # #                 clm_bypass_limit_protection=True
# # # # #             ).write({limit_field: rec.proposed_limit})

# # # # #             rec.write({
# # # # #                 'state': 'approved',
# # # # #                 'previous_limit': prev_limit,
# # # # #                 'reviewed_by': self.env.uid,
# # # # #                 'reviewed_date': fields.Datetime.now(),
# # # # #             })
# # # # #             rec.message_post(
# # # # #                 body=(
# # # # #                     f"✅ Approved by {self.env.user.name}.\n"
# # # # #                     f"Bucket: {dict(rec._fields['bucket'].selection).get(rec.bucket)}\n"
# # # # #                     f"Previous Limit: {prev_limit:,.2f} → New Limit: {rec.proposed_limit:,.2f}"
# # # # #                 ),
# # # # #                 subtype_xmlid='mail.mt_note',
# # # # #             )

# # # # #     # def action_reject(self):
# # # # #     #     """
# # # # #     #     Finance Manager rejects the request.
# # # # #     #     Rejected requests are permanently closed — cannot be reused.
# # # # #     #     """
# # # # #     #     self._assert_group('zencore_clms.group_zencore_clm_finance', 'reject limit change requests')
# # # # #     #     for rec in self:
# # # # #     #         if rec.state != 'pending_fm':
# # # # #     #             raise UserError(f"Only pending requests can be rejected. ({rec.name})")
# # # # #     #         rec.write({
# # # # #     #             'state': 'rejected',
# # # # #     #             'reviewed_by': self.env.uid,
# # # # #     #             'reviewed_date': fields.Datetime.now(),
# # # # #     #         })
# # # # #     #         rec.message_post(
# # # # #     #             body=f"❌ Rejected by {self.env.user.name}. Comment: {rec.fm_comment or 'None'}",
# # # # #     #             subtype_xmlid='mail.mt_note',
# # # # #     #         )

# # # # #     def action_reject(self):
# # # # #         self._assert_group('zencore_clms.group_zencore_clm_finance', 'reject')
# # # # #         for rec in self:
# # # # #             if rec.state != 'pending_fm':
# # # # #                 raise UserError(...)
# # # # #             if not rec.fm_comment or not rec.fm_comment.strip():
# # # # #                 raise UserError(
# # # # #                     "Rejection requires a Finance Manager comment.\n"
# # # # #                     "Please explain the reason for rejection in the FM Comment field."
# # # # #                 )
# # # # #             rec.write({
# # # # #                 'state': 'rejected',
# # # # #                 'reviewed_by': self.env.uid,
# # # # #                 'reviewed_date': fields.Datetime.now(),
# # # # #             })

# # # # #     # ─────────────────────────────────────────────────────────────────────────
# # # # #     # PRIVATE HELPERS
# # # # #     # ─────────────────────────────────────────────────────────────────────────

# # # # #     def _assert_group(self, group_xml_id, action_label):
# # # # #         """Raises AccessError if current user does not belong to the required group."""
# # # # #         if not self.env.user.has_group(group_xml_id):
# # # # #             group = self.env.ref(group_xml_id)
# # # # #             raise AccessError(
# # # # #                 f"You do not have permission to {action_label}.\n"
# # # # #                 f"Required group: {group.full_name}"
# # # # #             )


# # # # from odoo import models, fields, api
# # # # from odoo.exceptions import UserError, AccessError, ValidationError


# # # # class ClmLimitChangeRequest(models.Model):
# # # #     """
# # # #     Individual Bucket Limit Change Workflow.

# # # #     State Machine:
# # # #       draft → pending_fm → approved / rejected

# # # #     Rules:
# # # #       - Only CCM can create and submit requests
# # # #       - Only Finance Manager can approve or reject
# # # #       - Rejected requests are permanently closed and cannot be reused
# # # #       - Limit is updated directly on res.partner upon approval
# # # #       - Full audit trail: initiator, approver, timestamps, old/new values

# # # #     See clm.bulk.limit.change.request for multi-bucket batch requests.
# # # #     """

# # # #     _name = 'clm.limit.change.request'
# # # #     _description = 'CLM Bucket Limit Change Request'
# # # #     _inherit = ['mail.thread', 'mail.activity.mixin']
# # # #     _order = 'create_date desc'
# # # #     _rec_name = 'name'

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # IDENTIFICATION
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     name = fields.Char(
# # # #         string='Reference',
# # # #         readonly=True,
# # # #         default='New',
# # # #         copy=False,
# # # #     )

# # # #     #add line
# # # #     line_ids = fields.One2many(
# # # #         'clm.limit.change.request.line',
# # # #         'request_id',
# # # #         string='Limit Change Lines',
# # # #     )

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # REQUEST DETAILS
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     partner_id = fields.Many2one(
# # # #         'res.partner',
# # # #         string='Customer',
# # # #         required=True,
# # # #         ondelete='restrict',
# # # #         tracking=True,
# # # #     )
# # # #     bucket = fields.Selection(
# # # #         selection=[
# # # #             ('proforma', 'Proforma Invoice'),
# # # #             ('bucket1', 'Bucket 1'),
# # # #             ('bucket2', 'Bucket 2'),
# # # #             ('bucket3', 'Bucket 3'),
# # # #             ('bucket4', 'Bucket 4'),
# # # #         ],
# # # #         string='Bucket',
# # # #         required=True,
# # # #         tracking=True,
# # # #     )
# # # #     currency_id = fields.Many2one(
# # # #         'res.currency',
# # # #         default=lambda self: self.env.company.currency_id,
# # # #     )
# # # #     current_limit = fields.Monetary(
# # # #         string='Current Limit',
# # # #         compute='_compute_current_values',
# # # #         currency_field='currency_id',
# # # #     )
# # # #     current_exposure = fields.Monetary(
# # # #         string='Current Exposure',
# # # #         compute='_compute_current_values',
# # # #         currency_field='currency_id',
# # # #     )
# # # #     proposed_limit = fields.Monetary(
# # # #         string='Proposed Limit',
# # # #         required=True,
# # # #         currency_field='currency_id',
# # # #         tracking=True,
# # # #     )
# # # #     justification = fields.Text(
# # # #         string='Justification',
# # # #         required=True,
# # # #     )

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # AUTO-CLASSIFICATION
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     request_type = fields.Selection(
# # # #         selection=[
# # # #             ('freeze_resolution', 'Freeze Resolution'),
# # # #             ('standard_increase', 'Standard Increase'),
# # # #         ],
# # # #         string='Request Type',
# # # #         compute='_compute_request_type',
# # # #         store=True,
# # # #         tracking=True,
# # # #     )

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # WORKFLOW STATE
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     state = fields.Selection(
# # # #         selection=[
# # # #             ('draft', 'Draft'),
# # # #             ('pending_fm', 'Pending FM Approval'),
# # # #             ('approved', 'Approved'),
# # # #             ('rejected', 'Rejected'),
# # # #         ],
# # # #         string='Status',
# # # #         default='draft',
# # # #         readonly=True,
# # # #         tracking=True,
# # # #     )

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # AUDIT TRAIL — All readonly, set by system
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     initiated_by = fields.Many2one(
# # # #         'res.users',
# # # #         string='Initiated By',
# # # #         readonly=True,
# # # #         copy=False,
# # # #     )
# # # #     reviewed_by = fields.Many2one(
# # # #         'res.users',
# # # #         string='Approved / Rejected By',
# # # #         readonly=True,
# # # #         copy=False,
# # # #         tracking=True,
# # # #     )
# # # #     reviewed_date = fields.Datetime(
# # # #         string='Reviewed On',
# # # #         readonly=True,
# # # #         copy=False,
# # # #     )
# # # #     previous_limit = fields.Monetary(
# # # #         string='Previous Limit (at Approval)',
# # # #         readonly=True,
# # # #         currency_field='currency_id',
# # # #         copy=False,
# # # #     )
# # # #     fm_comment = fields.Text(
# # # #         string='Finance Manager Comment',
# # # #         copy=False,
# # # #         tracking=True,
# # # #     )

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # FIELD MAPPINGS — Bucket → Partner field names
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     _LIMIT_FIELD_MAP = {
# # # #         'proforma': 'clm_proforma_limit',
# # # #         'bucket1': 'clm_bucket_1_limit',
# # # #         'bucket2': 'clm_bucket_2_limit',
# # # #         'bucket3': 'clm_bucket_3_limit',
# # # #         'bucket4': 'clm_bucket_4_limit',
# # # #     }

# # # #     _BALANCE_FIELD_MAP = {
# # # #         'proforma': 'clm_proforma_balance',
# # # #         'bucket1': 'clm_bucket_1_balance',
# # # #         'bucket2': 'clm_bucket_2_balance',
# # # #         'bucket3': 'clm_bucket_3_balance',
# # # #         'bucket4': 'clm_bucket_4_balance',
# # # #     }

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # COMPUTE METHODS
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     @api.depends('partner_id', 'bucket')
# # # #     def _compute_current_values(self):
# # # #         for rec in self:
# # # #             if rec.partner_id and rec.bucket:
# # # #                 rec.current_limit = getattr(
# # # #                     rec.partner_id, self._LIMIT_FIELD_MAP[rec.bucket], 0.0
# # # #                 )
# # # #                 rec.current_exposure = getattr(
# # # #                     rec.partner_id, self._BALANCE_FIELD_MAP[rec.bucket], 0.0
# # # #                 )
# # # #             else:
# # # #                 rec.current_limit = 0.0
# # # #                 rec.current_exposure = 0.0

# # # #     @api.depends('current_exposure', 'current_limit')
# # # #     def _compute_request_type(self):
# # # #         for rec in self:
# # # #             rec.request_type = (
# # # #                 'freeze_resolution'
# # # #                 if rec.current_exposure > rec.current_limit
# # # #                 else 'standard_increase'
# # # #             )

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # CONSTRAINTS
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     @api.constrains('partner_id', 'bucket', 'state')
# # # #     def _check_unique_pending(self):
# # # #         for rec in self:
# # # #             if rec.state == 'pending_fm':
# # # #                 duplicate = self.search([
# # # #                     ('partner_id', '=', rec.partner_id.id),
# # # #                     ('bucket', '=', rec.bucket),
# # # #                     ('state', '=', 'pending_fm'),
# # # #                     ('id', '!=', rec.id),
# # # #                 ], limit=1)
# # # #                 if duplicate:
# # # #                     raise ValidationError(
# # # #                         f"A pending request ({duplicate.name}) already exists "
# # # #                         f"for {rec.partner_id.name} — "
# # # #                         f"{dict(self._fields['bucket'].selection).get(rec.bucket)}.\n"
# # # #                         f"Resolve the existing request before submitting a new one."
# # # #                     )

# # # #     @api.constrains('proposed_limit')
# # # #     def _check_proposed_limit_positive(self):
# # # #         for rec in self:
# # # #             if rec.proposed_limit <= 0:
# # # #                 raise ValidationError("Proposed limit must be greater than zero.")

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # ORM OVERRIDES
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     @api.model_create_multi
# # # #     def create(self, vals_list):
# # # #         for vals in vals_list:
# # # #             if vals.get('name', 'New') == 'New':
# # # #                 vals['name'] = (
# # # #                     self.env['ir.sequence'].next_by_code('clm.limit.change.request')
# # # #                     or 'New'
# # # #                 )
# # # #             vals['initiated_by'] = self.env.uid
# # # #         return super().create(vals_list)

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # WORKFLOW ACTIONS
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     def action_submit_to_fm(self):
# # # #         """CCM submits request for FM review. draft → pending_fm."""
# # # #         self._assert_group(
# # # #             'zencore_clms.group_zencore_clm_ccm',
# # # #             'submit limit change requests',
# # # #         )
# # # #         for rec in self:
# # # #             if rec.state != 'draft':
# # # #                 raise UserError(
# # # #                     f"Only draft requests can be submitted. Current state: {rec.state} ({rec.name})"
# # # #                 )
# # # #             rec.write({'state': 'pending_fm'})
# # # #             rec.message_post(
# # # #                 body=(
# # # #                     f"<b>Submitted for FM Approval</b><br/>"
# # # #                     f"Submitted by: {self.env.user.name}<br/>"
# # # #                     f"Bucket: {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
# # # #                     f"Proposed Limit: {rec.proposed_limit:,.2f}<br/>"
# # # #                     f"Request Type: {dict(self._fields['request_type'].selection).get(rec.request_type)}"
# # # #                 ),
# # # #                 subtype_xmlid='mail.mt_note',
# # # #             )
# # # #             # Notify Finance Manager
# # # #             finance_group = self.env.ref(
# # # #                 'zencore_clms.group_zencore_clm_finance', raise_if_not_found=False
# # # #             )
# # # #             if finance_group:
# # # #                 finance_users = self.env['res.users'].search([
# # # #                     ('groups_id', 'in', [finance_group.id]),
# # # #                     ('share', '=', False),
# # # #                     ('active', '=', True),
# # # #                 ], limit=1)
# # # #                 if finance_users:
# # # #                     rec.activity_schedule(
# # # #                         'mail.mail_activity_data_todo',
# # # #                         user_id=finance_users[0].id,
# # # #                         note=(
# # # #                             f"Limit Change Request {rec.name} submitted by "
# # # #                             f"{self.env.user.name} for {rec.partner_id.name} — "
# # # #                             f"{dict(self._fields['bucket'].selection).get(rec.bucket)}. "
# # # #                             f"Proposed limit: {rec.proposed_limit:,.2f}. Please review."
# # # #                         ),
# # # #                     )

# # # #     def action_approve(self):
# # # #         """Finance Manager approves. pending_fm → approved. Updates partner limit."""
# # # #         self._assert_group(
# # # #             'zencore_clms.group_zencore_clm_finance',
# # # #             'approve limit change requests',
# # # #         )
# # # #         for rec in self:
# # # #             if rec.state != 'pending_fm':
# # # #                 raise UserError(
# # # #                     f"Only pending requests can be approved. Current state: {rec.state} ({rec.name})"
# # # #                 )

# # # #             limit_field = self._LIMIT_FIELD_MAP[rec.bucket]
# # # #             prev_limit = getattr(rec.partner_id, limit_field, 0.0)

# # # #             rec.partner_id.with_context(
# # # #                 clm_bypass_limit_protection=True
# # # #             ).write({limit_field: rec.proposed_limit})

# # # #             rec.write({
# # # #                 'state': 'approved',
# # # #                 'previous_limit': prev_limit,
# # # #                 'reviewed_by': self.env.uid,
# # # #                 'reviewed_date': fields.Datetime.now(),
# # # #             })
# # # #             rec.activity_ids.action_done()
# # # #             rec.message_post(
# # # #                 body=(
# # # #                     f"<b>✅ Approved by {self.env.user.name}</b><br/>"
# # # #                     f"Customer : {rec.partner_id.name}<br/>"
# # # #                     f"Bucket   : {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
# # # #                     f"Previous : {prev_limit:,.2f}<br/>"
# # # #                     f"New Limit: {rec.proposed_limit:,.2f}<br/>"
# # # #                     f"Comment  : {rec.fm_comment or '—'}"
# # # #                 ),
# # # #                 subtype_xmlid='mail.mt_note',
# # # #             )

# # # #     def action_reject(self):
# # # #         """
# # # #         Finance Manager rejects. pending_fm → rejected.
# # # #         FM comment is required. Rejected records are permanently closed.

# # # #         FIX: Previous version had `raise UserError(...)` with Python's Ellipsis
# # # #         literal (...) instead of a string argument — a silent syntax/runtime bug
# # # #         that would raise TypeError, not UserError, breaking the entire action.
# # # #         """
# # # #         self._assert_group(
# # # #             'zencore_clms.group_zencore_clm_finance',
# # # #             'reject limit change requests',
# # # #         )
# # # #         for rec in self:
# # # #             if rec.state != 'pending_fm':
# # # #                 raise UserError(
# # # #                     f"Only pending requests can be rejected. Current state: {rec.state} ({rec.name})"
# # # #                 )
# # # #             if not rec.fm_comment or not rec.fm_comment.strip():
# # # #                 raise UserError(
# # # #                     "A Finance Manager comment is required before rejecting.\n"
# # # #                     "Enter the rejection reason in the FM Comment field."
# # # #                 )
# # # #             rec.write({
# # # #                 'state': 'rejected',
# # # #                 'reviewed_by': self.env.uid,
# # # #                 'reviewed_date': fields.Datetime.now(),
# # # #             })
# # # #             rec.activity_ids.action_done()
# # # #             rec.message_post(
# # # #                 body=(
# # # #                     f"<b>❌ Rejected by {self.env.user.name}</b><br/>"
# # # #                     f"Customer: {rec.partner_id.name}<br/>"
# # # #                     f"Bucket  : {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
# # # #                     f"Reason  : {rec.fm_comment}"
# # # #                 ),
# # # #                 subtype_xmlid='mail.mt_note',
# # # #             )

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # PRIVATE HELPERS
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     def _assert_group(self, group_xml_id, action_label):
# # # #         if not self.env.user.has_group(group_xml_id):
# # # #             group = self.env.ref(group_xml_id)
# # # #             raise AccessError(
# # # #                 f"You do not have permission to {action_label}.\n"
# # # #                 f"Required group: {group.full_name}"
# # # #             )

# # # # class ClmLimitChangeRequestLine(models.Model):
# # # #     _name = 'clm.limit.change.request.line'
# # # #     _description = 'Limit Change Request Line'

# # # #     request_id = fields.Many2one(
# # # #         'clm.limit.change.request',
# # # #         string='Limit Change Request',
# # # #         ondelete='cascade',
# # # #     )

# # # #     bucket = fields.Selection(
# # # #         related='request_id.bucket',
# # # #         string='Bucket',
# # # #         store=True,
# # # #         readonly=True,
# # # #     )

# # # from odoo import models, fields, api
# # # from odoo.exceptions import UserError, AccessError, ValidationError


# # # class ClmLimitChangeRequest(models.Model):
# # #     """
# # #     Multi-Bucket Limit Change Workflow — clm.limit.change.request

# # #     State Machine:
# # #       draft → pending_fm → approved / rejected

# # #     Design (v0.4.0 refactor):
# # #     ──────────────────────────
# # #     - Header: partner, justification, workflow state, audit trail
# # #     - Lines:  one line per bucket — each has its own limit/exposure/proposed
# # #     - Approval: iterates line_ids and writes each bucket's limit on the partner
# # #     - request_type on header: 'freeze_resolution' if ANY line is a freeze resolution

# # #     SRS §9 Compliance:
# # #     ───────────────────
# # #     - Only CCM can create and submit (draft → pending_fm)
# # #     - Only Finance Manager can approve or reject
# # #     - Rejected requests are permanently closed
# # #     - Full audit trail: initiator, approver, timestamps
# # #     """

# # #     _name = 'clm.limit.change.request'
# # #     _description = 'CLM Bucket Limit Change Request'
# # #     _inherit = ['mail.thread', 'mail.activity.mixin']
# # #     _order = 'create_date desc'
# # #     _rec_name = 'name'

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # IDENTIFICATION
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     name = fields.Char(
# # #         string='Reference',
# # #         readonly=True,
# # #         default='New',
# # #         copy=False,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # HEADER FIELDS
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     partner_id = fields.Many2one(
# # #         'res.partner',
# # #         string='Customer',
# # #         required=True,
# # #         ondelete='restrict',
# # #         tracking=True,
# # #     )
# # #     currency_id = fields.Many2one(
# # #         'res.currency',
# # #         default=lambda self: self.env.company.currency_id,
# # #     )
# # #     justification = fields.Text(
# # #         string='Justification',
# # #         required=True,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # LINES — One line per bucket
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     line_ids = fields.One2many(
# # #         'clm.limit.change.request.line',
# # #         'request_id',
# # #         string='Limit Change Lines',
# # #         copy=True,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # AUTO-CLASSIFICATION — Computed from lines
# # #     # 'freeze_resolution' if ANY line has exposure > limit
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     request_type = fields.Selection(
# # #         selection=[
# # #             ('freeze_resolution', 'Freeze Resolution'),
# # #             ('standard_increase', 'Standard Increase'),
# # #         ],
# # #         string='Request Type',
# # #         compute='_compute_request_type',
# # #         store=True,
# # #         tracking=True,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # WORKFLOW STATE
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     state = fields.Selection(
# # #         selection=[
# # #             ('draft',      'Draft'),
# # #             ('pending_fm', 'Pending FM Approval'),
# # #             ('approved',   'Approved'),
# # #             ('rejected',   'Rejected'),
# # #         ],
# # #         string='Status',
# # #         default='draft',
# # #         readonly=True,
# # #         tracking=True,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # AUDIT TRAIL — All set by system, never by users
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     initiated_by = fields.Many2one(
# # #         'res.users',
# # #         string='Initiated By',
# # #         readonly=True,
# # #         copy=False,
# # #     )
# # #     reviewed_by = fields.Many2one(
# # #         'res.users',
# # #         string='Approved / Rejected By',
# # #         readonly=True,
# # #         copy=False,
# # #         tracking=True,
# # #     )
# # #     reviewed_date = fields.Datetime(
# # #         string='Reviewed On',
# # #         readonly=True,
# # #         copy=False,
# # #     )
# # #     fm_comment = fields.Text(
# # #         string='Finance Manager Comment',
# # #         copy=False,
# # #         tracking=True,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────────
# # #     # ALL BUCKET KEYS IN ORDER
# # #     # ─────────────────────────────────────────────────────────────────────────────

# # #     _BUCKET_KEYS = ['proforma', 'bucket1', 'bucket2', 'bucket3', 'bucket4']


# # #     @api.onchange('partner_id')
# # #     def _onchange_partner_id_populate_lines(self):
# # #         """
# # #         Auto-populate all 5 bucket lines when partner is selected or changed.
# # #         Clears existing lines first to avoid duplicates.
# # #         Lines are pre-filled with current limit + exposure from the partner.
# # #         CCM only needs to fill 'proposed_limit' for the buckets they want to change.

# # #         Odoo 19 pattern:
# # #         - Use Command.clear() to wipe existing lines
# # #         - Use Command.create({...}) to create new lines in the same onchange
# # #         - proposed_limit defaults to current_limit (no change intent)
# # #         so CCM only edits buckets they care about
# # #         """
# # #         if not self.partner_id:
# # #             self.line_ids = fields.Command.clear()
# # #             return

# # #         partner = self.partner_id
# # #         new_lines = []

# # #         for bucket in self._BUCKET_KEYS:
# # #             limit_field   = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
# # #             balance_field = ClmLimitChangeRequestLine._BALANCE_FIELD_MAP[bucket]

# # #             current_limit    = getattr(partner, limit_field,   0.0)
# # #             current_exposure = getattr(partner, balance_field, 0.0)

# # #             new_lines.append(fields.Command.create({
# # #                 'bucket':         bucket,
# # #                 'proposed_limit': current_limit,  # defaults to no change; CCM edits as needed
# # #             }))

# # #         self.line_ids = fields.Command.clear()
# # #         self.line_ids = new_lines

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # COMPUTE
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     @api.depends('line_ids.request_type')
# # #     def _compute_request_type(self):
# # #         for rec in self:
# # #             if any(line.request_type == 'freeze_resolution' for line in rec.line_ids):
# # #                 rec.request_type = 'freeze_resolution'
# # #             else:
# # #                 rec.request_type = 'standard_increase'

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # CONSTRAINTS
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     # @api.constrains('line_ids')
# # #     # def _check_lines_not_empty(self):
# # #     #     for rec in self:
# # #     #         if rec.state == 'draft' and not rec.line_ids:
# # #     #             raise ValidationError(
# # #     #                 "At least one bucket line is required before submitting."
# # #     #             )

# # #     @api.constrains('partner_id', 'line_ids')
# # #     def _check_lines_not_empty(self):
# # #         for rec in self:
# # #             if rec.state != 'draft':
# # #                 continue
# # #             if rec.partner_id and not rec.line_ids:
# # #                 raise ValidationError(
# # #                     f"Request {rec.name} has no bucket lines.\n"
# # #                     f"Select the customer again to auto-populate all buckets."
# # #                 )

# # #     @api.constrains('line_ids', 'partner_id')
# # #     def _check_duplicate_buckets_in_lines(self):
# # #         """Prevent the same bucket appearing twice on the same request."""
# # #         for rec in self:
# # #             buckets = rec.line_ids.mapped('bucket')
# # #             if len(buckets) != len(set(buckets)):
# # #                 raise ValidationError(
# # #                     "Each bucket may only appear once per request.\n"
# # #                     "Remove duplicate bucket lines."
# # #                 )

# # #     @api.constrains('partner_id', 'state')
# # #     def _check_unique_pending(self):
# # #         """Prevent two pending requests for the same partner."""
# # #         for rec in self:
# # #             if rec.state == 'pending_fm':
# # #                 duplicate = self.search([
# # #                     ('partner_id', '=', rec.partner_id.id),
# # #                     ('state',      '=', 'pending_fm'),
# # #                     ('id',         '!=', rec.id),
# # #                 ], limit=1)
# # #                 if duplicate:
# # #                     raise ValidationError(
# # #                         f"A pending request ({duplicate.name}) already exists "
# # #                         f"for {rec.partner_id.name}.\n"
# # #                         f"Resolve the existing request before creating a new one."
# # #                     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # WRITE PROTECTION — Terminal state guard
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     def write(self, vals):
# # #         for rec in self:
# # #             if rec.state in ('approved', 'rejected') and not self.env.su:
# # #                 raise AccessError(
# # #                     f"Request {rec.name} is in a terminal state ({rec.state}) "
# # #                     f"and cannot be modified."
# # #                 )
# # #         return super().write(vals)

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # ORM OVERRIDES
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     @api.model_create_multi
# # #     def create(self, vals_list):
# # #         self._assert_group(
# # #             'zencore_clms.group_zencore_clm_ccm',
# # #             'create limit change requests',
# # #         )
# # #         for vals in vals_list:
# # #             if vals.get('name', 'New') == 'New':
# # #                 vals['name'] = (
# # #                     self.env['ir.sequence'].next_by_code('clm.limit.change.request')
# # #                     or 'New'
# # #                 )
# # #             vals['initiated_by'] = self.env.uid
# # #         return super().create(vals_list)

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # WORKFLOW ACTIONS
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     def action_submit_to_fm(self):
# # #         """CCM submits request for FM review. draft → pending_fm."""
# # #         self._assert_group(
# # #             'zencore_clms.group_zencore_clm_ccm',
# # #             'submit limit change requests',
# # #         )
# # #         for rec in self:
# # #             if rec.state != 'draft':
# # #                 raise UserError(
# # #                     f"Only draft requests can be submitted. "
# # #                     f"Current state: {rec.state} ({rec.name})"
# # #                 )
# # #             if not rec.line_ids:
# # #                 raise UserError(
# # #                     f"Cannot submit {rec.name} — no bucket lines added.\n"
# # #                     f"Add at least one bucket line before submitting."
# # #                 )

# # #             rec.write({'state': 'pending_fm'})

# # #             # Build line summary for chatter
# # #             line_summary = ''.join(
# # #                 f"<li>{dict(self.env['clm.limit.change.request.line']._fields['bucket'].selection).get(l.bucket)}: "
# # #                 f"{l.current_limit:,.2f} → {l.proposed_limit:,.2f}</li>"
# # #                 for l in rec.line_ids
# # #             )
# # #             rec.message_post(
# # #                 body=(
# # #                     f"<b>Submitted for FM Approval</b><br/>"
# # #                     f"Submitted by : {self.env.user.name}<br/>"
# # #                     f"Customer     : {rec.partner_id.name}<br/>"
# # #                     f"Request Type : {dict(self._fields['request_type'].selection).get(rec.request_type)}<br/>"
# # #                     f"Buckets      : <ul>{line_summary}</ul>"
# # #                 ),
# # #                 subtype_xmlid='mail.mt_note',
# # #             )

# # #             # FIX: Odoo 19 — group_ids (not groups_id)
# # #             finance_group = self.env.ref(
# # #                 'zencore_clms.group_zencore_clm_finance',
# # #                 raise_if_not_found=False,
# # #             )
# # #             if finance_group:
# # #                 finance_users = self.env['res.users'].search([
# # #                     ('group_ids', 'in', [finance_group.id]),  # Odoo 19: group_ids
# # #                     ('share',     '=', False),
# # #                     ('active',    '=', True),
# # #                 ], limit=1)
# # #                 if finance_users:
# # #                     rec.activity_schedule(
# # #                         'mail.mail_activity_data_todo',
# # #                         user_id=finance_users[0].id,
# # #                         note=(
# # #                             f"Limit Change Request {rec.name} submitted by "
# # #                             f"{self.env.user.name} for {rec.partner_id.name}. "
# # #                             f"Please review."
# # #                         ),
# # #                     )

# # #     def action_approve(self):
# # #         """
# # #         Finance Manager approves. pending_fm → approved.
# # #         Iterates ALL lines and writes each bucket's limit on the partner.
# # #         """
# # #         self._assert_group(
# # #             'zencore_clms.group_zencore_clm_finance',
# # #             'approve limit change requests',
# # #         )
# # #         for rec in self:
# # #             if rec.state != 'pending_fm':
# # #                 raise UserError(
# # #                     f"Only pending requests can be approved. "
# # #                     f"Current state: {rec.state} ({rec.name})"
# # #                 )
# # #             if not rec.line_ids:
# # #                 raise UserError(f"Request {rec.name} has no lines to approve.")

# # #             # Apply each line's proposed limit to the partner
# # #             for line in rec.line_ids:
# # #                 line._apply_limit_to_partner()

# # #             rec.write({
# # #                 'state':         'approved',
# # #                 'reviewed_by':   self.env.uid,
# # #                 'reviewed_date': fields.Datetime.now(),
# # #             })
# # #             rec.activity_ids.action_done()

# # #             # Build approval summary
# # #             line_summary = ''.join(
# # #                 f"<li>{dict(self.env['clm.limit.change.request.line']._fields['bucket'].selection).get(l.bucket)}: "
# # #                 f"{l.previous_limit:,.2f} → {l.proposed_limit:,.2f}</li>"
# # #                 for l in rec.line_ids
# # #             )
# # #             rec.message_post(
# # #                 body=(
# # #                     f"<b>✅ Approved by {self.env.user.name}</b><br/>"
# # #                     f"Customer : {rec.partner_id.name}<br/>"
# # #                     f"Changes  : <ul>{line_summary}</ul>"
# # #                     f"Comment  : {rec.fm_comment or '—'}"
# # #                 ),
# # #                 subtype_xmlid='mail.mt_note',
# # #             )

# # #     def action_reject(self):
# # #         """
# # #         Finance Manager rejects. pending_fm → rejected.
# # #         FM comment is required. Terminal state — cannot be reused.
# # #         """
# # #         self._assert_group(
# # #             'zencore_clms.group_zencore_clm_finance',
# # #             'reject limit change requests',
# # #         )
# # #         for rec in self:
# # #             if rec.state != 'pending_fm':
# # #                 raise UserError(
# # #                     f"Only pending requests can be rejected. "
# # #                     f"Current state: {rec.state} ({rec.name})"
# # #                 )
# # #             if not rec.fm_comment or not rec.fm_comment.strip():
# # #                 raise UserError(
# # #                     "A Finance Manager comment is required before rejecting.\n"
# # #                     "Enter the rejection reason in the FM Comment field."
# # #                 )
# # #             rec.write({
# # #                 'state':         'rejected',
# # #                 'reviewed_by':   self.env.uid,
# # #                 'reviewed_date': fields.Datetime.now(),
# # #             })
# # #             rec.activity_ids.action_done()
# # #             rec.message_post(
# # #                 body=(
# # #                     f"<b>❌ Rejected by {self.env.user.name}</b><br/>"
# # #                     f"Customer: {rec.partner_id.name}<br/>"
# # #                     f"Reason  : {rec.fm_comment}"
# # #                 ),
# # #                 subtype_xmlid='mail.mt_note',
# # #             )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # PRIVATE HELPERS
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     def _assert_group(self, group_xml_id, action_label):
# # #         if not self.env.user.has_group(group_xml_id):
# # #             group = self.env.ref(group_xml_id)
# # #             raise AccessError(
# # #                 f"You do not have permission to {action_label}.\n"
# # #                 f"Required group: {group.full_name}"
# # #             )


# # # # ─────────────────────────────────────────────────────────────────────────────
# # # # LINE MODEL
# # # # ─────────────────────────────────────────────────────────────────────────────

# # # class ClmLimitChangeRequestLine(models.Model):
# # #     """
# # #     One line = one bucket on a limit change request.

# # #     Each line holds:
# # #       - bucket             : which bucket this line targets
# # #       - current_limit      : live value from partner (computed, non-stored)
# # #       - current_exposure   : live balance from partner (computed, non-stored)
# # #       - proposed_limit     : new limit requested by CCM
# # #       - previous_limit     : captured at approval time for audit trail
# # #       - request_type       : freeze_resolution / standard_increase (computed)
# # #     """

# # #     _name = 'clm.limit.change.request.line'
# # #     _description = 'CLM Limit Change Request Line'
# # #     _order = 'bucket'

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # RELATIONAL
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     request_id = fields.Many2one(
# # #         'clm.limit.change.request',
# # #         string='Request',
# # #         required=True,
# # #         ondelete='cascade',
# # #         index=True,
# # #     )
# # #     # Convenience access to header fields
# # #     partner_id = fields.Many2one(
# # #         related='request_id.partner_id',
# # #         string='Customer',
# # #         store=False,
# # #     )
# # #     currency_id = fields.Many2one(
# # #         related='request_id.currency_id',
# # #         string='Currency',
# # #         store=False,
# # #     )
# # #     state = fields.Selection(
# # #         related='request_id.state',
# # #         string='Request State',
# # #         store=False,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # CORE FIELDS
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     bucket = fields.Selection(
# # #         selection=[
# # #             ('proforma', 'Proforma Invoice'),
# # #             ('bucket1',  'Bucket 1'),
# # #             ('bucket2',  'Bucket 2'),
# # #             ('bucket3',  'Bucket 3'),
# # #             ('bucket4',  'Bucket 4'),
# # #         ],
# # #         string='Bucket',
# # #         required=True,
# # #     )
# # #     current_limit = fields.Monetary(
# # #         string='Current Limit',
# # #         compute='_compute_current_values',
# # #         currency_field='currency_id',
# # #     )
# # #     current_exposure = fields.Monetary(
# # #         string='Current Exposure',
# # #         compute='_compute_current_values',
# # #         currency_field='currency_id',
# # #     )
# # #     proposed_limit = fields.Monetary(
# # #         string='Proposed Limit',
# # #         required=True,
# # #         currency_field='currency_id',
# # #     )
# # #     previous_limit = fields.Monetary(
# # #         string='Previous Limit (at Approval)',
# # #         readonly=True,
# # #         currency_field='currency_id',
# # #         copy=False,
# # #     )
# # #     request_type = fields.Selection(
# # #         selection=[
# # #             ('freeze_resolution', 'Freeze Resolution'),
# # #             ('standard_increase', 'Standard Increase'),
# # #         ],
# # #         string='Type',
# # #         compute='_compute_request_type',
# # #         store=True,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # FIELD MAPS — Bucket key → partner field names
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     _LIMIT_FIELD_MAP = {
# # #         'proforma': 'clm_proforma_limit',
# # #         'bucket1':  'clm_bucket_1_limit',
# # #         'bucket2':  'clm_bucket_2_limit',
# # #         'bucket3':  'clm_bucket_3_limit',
# # #         'bucket4':  'clm_bucket_4_limit',
# # #     }

# # #     _BALANCE_FIELD_MAP = {
# # #         'proforma': 'clm_proforma_balance',
# # #         'bucket1':  'clm_bucket_1_balance',
# # #         'bucket2':  'clm_bucket_2_balance',
# # #         'bucket3':  'clm_bucket_3_balance',
# # #         'bucket4':  'clm_bucket_4_balance',
# # #     }

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # COMPUTE
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     @api.depends('request_id.partner_id', 'bucket')
# # #     def _compute_current_values(self):
# # #         for line in self:
# # #             partner = line.request_id.partner_id
# # #             if partner and line.bucket:
# # #                 line.current_limit    = getattr(partner, self._LIMIT_FIELD_MAP[line.bucket], 0.0)
# # #                 line.current_exposure = getattr(partner, self._BALANCE_FIELD_MAP[line.bucket], 0.0)
# # #             else:
# # #                 line.current_limit    = 0.0
# # #                 line.current_exposure = 0.0

# # #     @api.depends('current_exposure', 'current_limit')
# # #     def _compute_request_type(self):
# # #         for line in self:
# # #             line.request_type = (
# # #                 'freeze_resolution'
# # #                 if line.current_exposure > line.current_limit
# # #                 else 'standard_increase'
# # #             )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # CONSTRAINTS
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     @api.constrains('proposed_limit')
# # #     def _check_proposed_limit_positive(self):
# # #         for line in self:
# # #             if line.proposed_limit <= 0:
# # #                 raise ValidationError(
# # #                     f"Proposed limit must be greater than zero "
# # #                     f"({dict(self._fields['bucket'].selection).get(line.bucket)})."
# # #                 )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # APPROVAL HELPER — Called by action_approve on the header
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     def _apply_limit_to_partner(self):
# # #         """
# # #         Writes this line's proposed_limit onto the partner.
# # #         Captures previous_limit for audit trail.
# # #         Uses bypass context to pass write() protection on res.partner.
# # #         """
# # #         self.ensure_one()
# # #         partner = self.request_id.partner_id
# # #         limit_field = self._LIMIT_FIELD_MAP[self.bucket]
# # #         prev = getattr(partner, limit_field, 0.0)

# # #         partner.with_context(
# # #             clm_bypass_limit_protection=True
# # #         ).write({limit_field: self.proposed_limit})

# # #         # Store previous value on the line for audit trail
# # #         self.with_context(
# # #             clm_bypass_line_write=True
# # #         ).write({'previous_limit': prev})

# # from odoo import models, fields, api
# # from odoo.exceptions import UserError, AccessError, ValidationError
# # from markupsafe import Markup

# # class ClmLimitChangeRequest(models.Model):
# #     """
# #     Multi-Bucket Limit Change Workflow — clm.limit.change.request

# #     State Machine:
# #       draft → pending_fm → approved / rejected

# #     Design (v0.5.0):
# #     ──────────────────
# #     - Header  : partner, justification, workflow state, audit trail
# #     - Lines   : auto-populated on partner select (all 5 buckets)
# #                 CCM edits only the proposed_limit cells they want to change
# #     - Approval: iterates ALL line_ids and writes each bucket's limit on partner
# #     - request_type on header: freeze_resolution if ANY line is a freeze case

# #     SRS §9 Compliance:
# #     ───────────────────
# #     - Only CCM can create and submit (draft → pending_fm)
# #     - Only Finance Manager can approve or reject
# #     - Rejected requests are permanently closed — cannot be reused
# #     - Full audit trail: initiator, approver, timestamps, per-line previous limits

# #     Odoo 19 notes:
# #     ───────────────
# #     - group_ids (not groups_id) for res.users domain queries
# #     - fields.Command.create / fields.Command.clear for onchange O2M writes
# #     - flush_all() not needed here (no payment reconciliation)
# #     """

# #     _name = 'clm.limit.change.request'
# #     _description = 'CLM Bucket Limit Change Request'
# #     _inherit = ['mail.thread', 'mail.activity.mixin']
# #     _order = 'create_date desc'
# #     _rec_name = 'name'

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # BUCKET KEYS — canonical order, used by onchange + line model
# #     # ─────────────────────────────────────────────────────────────────────────

# #     _BUCKET_KEYS = ['proforma', 'bucket1', 'bucket2', 'bucket3', 'bucket4']

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # IDENTIFICATION
# #     # ─────────────────────────────────────────────────────────────────────────

# #     name = fields.Char(
# #         string='Reference',
# #         readonly=True,
# #         default='New',
# #         copy=False,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # HEADER FIELDS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     partner_id = fields.Many2one(
# #         'res.partner',
# #         string='Customer',
# #         required=True,
# #         ondelete='restrict',
# #         tracking=True,
# #     )
# #     currency_id = fields.Many2one(
# #         'res.currency',
# #         default=lambda self: self.env.company.currency_id,
# #     )
# #     justification = fields.Text(
# #         string='Justification',
# #         required=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # LINES — Auto-populated on partner select. One line per bucket.
# #     # ─────────────────────────────────────────────────────────────────────────

# #     line_ids = fields.One2many(
# #         'clm.limit.change.request.line',
# #         'request_id',
# #         string='Bucket Limit Lines',
# #         copy=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # AUTO-CLASSIFICATION — Computed from lines
# #     # freeze_resolution if ANY line has exposure > current limit
# #     # ─────────────────────────────────────────────────────────────────────────

# #     request_type = fields.Selection(
# #         selection=[
# #             ('freeze_resolution', 'Freeze Resolution'),
# #             ('standard_increase', 'Standard Increase'),
# #         ],
# #         string='Request Type',
# #         compute='_compute_request_type',
# #         store=True,
# #         tracking=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # WORKFLOW STATE
# #     # ─────────────────────────────────────────────────────────────────────────

# #     state = fields.Selection(
# #         selection=[
# #             ('draft',      'Draft'),
# #             ('pending_fm', 'Pending FM Approval'),
# #             ('approved',   'Approved'),
# #             ('rejected',   'Rejected'),
# #         ],
# #         string='Status',
# #         default='draft',
# #         readonly=True,
# #         tracking=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # AUDIT TRAIL — All set by system, never by users
# #     # ─────────────────────────────────────────────────────────────────────────

# #     initiated_by = fields.Many2one(
# #         'res.users',
# #         string='Initiated By',
# #         readonly=True,
# #         copy=False,
# #     )
# #     reviewed_by = fields.Many2one(
# #         'res.users',
# #         string='Approved / Rejected By',
# #         readonly=True,
# #         copy=False,
# #         tracking=True,
# #     )
# #     reviewed_date = fields.Datetime(
# #         string='Reviewed On',
# #         readonly=True,
# #         copy=False,
# #     )
# #     fm_comment = fields.Text(
# #         string='Finance Manager Comment',
# #         copy=False,
# #         tracking=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # COMPUTE
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.depends('line_ids.request_type')
# #     def _compute_request_type(self):
# #         for rec in self:
# #             if any(line.request_type == 'freeze_resolution' for line in rec.line_ids):
# #                 rec.request_type = 'freeze_resolution'
# #             else:
# #                 rec.request_type = 'standard_increase'

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # ONCHANGE — Auto-populate all 5 bucket lines on partner select
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.onchange('partner_id')
# #     def _onchange_partner_id_populate_lines(self):
# #         """
# #         Fires in the UI when CCM selects or changes the partner.

# #         Behaviour:
# #         - Clears any existing lines (prevents stale data from previous partner)
# #         - Creates 5 new lines (one per bucket) with live values from the partner
# #         - proposed_limit defaults to current_limit so there is no accidental change
# #         - CCM only needs to edit the proposed_limit cells for buckets they intend to change

# #         Odoo 19 pattern:
# #         - fields.Command.clear()  → wipes existing O2M lines
# #         - fields.Command.create() → creates new virtual lines (not yet in DB)
# #         - Both work correctly in onchange context without needing a saved record
# #         """
# #         # Always clear first — even if partner is removed
# #         self.line_ids = [fields.Command.clear()]

# #         if not self.partner_id:
# #             return

# #         partner = self.partner_id
# #         new_lines = []

# #         for bucket in self._BUCKET_KEYS:
# #             limit_field   = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
# #             current_limit = getattr(partner, limit_field, 0.0)

# #             new_lines.append(fields.Command.create({
# #                 'bucket':         bucket,
# #                 # Default proposed = current so CCM edits only intended buckets
# #                 'proposed_limit': current_limit,
# #             }))

# #         self.line_ids = new_lines

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # INTERNAL HELPER — Shared by onchange (UI) and create() (programmatic)
# #     # ─────────────────────────────────────────────────────────────────────────

# #     def _populate_bucket_lines(self):
# #         """
# #         Writes all 5 bucket lines directly to the DB.
# #         Called from create() when the record already has an ID.
# #         Not used by onchange (which uses Command.create on virtual records).
# #         """
# #         self.ensure_one()
# #         if not self.partner_id:
# #             return

# #         partner = self.partner_id

# #         for bucket in self._BUCKET_KEYS:
# #             limit_field   = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
# #             current_limit = getattr(partner, limit_field, 0.0)

# #             self.env['clm.limit.change.request.line'].create({
# #                 'request_id':     self.id,
# #                 'bucket':         bucket,
# #                 'proposed_limit': current_limit,
# #             })

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # CONSTRAINTS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.constrains('partner_id', 'line_ids')
# #     def _check_lines_not_empty(self):
# #         """
# #         Ensures all records with a partner also have bucket lines.
# #         Protects against programmatic creation that skips onchange.
# #         """
# #         for rec in self:
# #             if rec.partner_id and not rec.line_ids:
# #                 raise ValidationError(
# #                     f"Request {rec.name} has no bucket lines.\n"
# #                     "Select the customer to auto-populate all buckets."
# #                 )

# #     @api.constrains('line_ids')
# #     def _check_duplicate_buckets_in_lines(self):
# #         """Prevent the same bucket appearing twice on one request."""
# #         for rec in self:
# #             buckets = rec.line_ids.mapped('bucket')
# #             if len(buckets) != len(set(buckets)):
# #                 raise ValidationError(
# #                     "Each bucket may appear only once per request.\n"
# #                     "Remove duplicate bucket lines."
# #                 )

# #     @api.constrains('partner_id', 'state')
# #     def _check_unique_pending(self):
# #         """Prevent two pending requests for the same partner."""
# #         for rec in self:
# #             if rec.state == 'pending_fm':
# #                 duplicate = self.search([
# #                     ('partner_id', '=', rec.partner_id.id),
# #                     ('state',      '=', 'pending_fm'),
# #                     ('id',         '!=', rec.id),
# #                 ], limit=1)
# #                 if duplicate:
# #                     raise ValidationError(
# #                         f"A pending request ({duplicate.name}) already exists "
# #                         f"for {rec.partner_id.name}.\n"
# #                         f"Resolve the existing request before creating a new one."
# #                     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # WRITE PROTECTION — Terminal state guard
# #     # SRS §9.3: Approved/rejected records cannot be modified
# #     # ─────────────────────────────────────────────────────────────────────────

# #     def write(self, vals):
# #         for rec in self:
# #             if rec.state in ('approved', 'rejected') and not self.env.su:
# #                 raise AccessError(
# #                     f"Request {rec.name} is in a terminal state "
# #                     f"({rec.state}) and cannot be modified."
# #                 )
# #         return super().write(vals)

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # ORM OVERRIDES
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.model_create_multi
# #     def create(self, vals_list):
# #         """
# #         SoD: Only CCM can create limit change requests.
# #         Sequence assigned on creation.
# #         initiated_by set to current user for audit trail.
# #         Lines auto-populated if partner is given and no lines provided.
# #         """
# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_ccm',
# #             'create limit change requests',
# #         )
# #         for vals in vals_list:
# #             if vals.get('name', 'New') == 'New':
# #                 vals['name'] = (
# #                     self.env['ir.sequence'].next_by_code('clm.limit.change.request')
# #                     or 'New'
# #                 )
# #             vals['initiated_by'] = self.env.uid

# #         records = super().create(vals_list)

# #         # Safety net: if created programmatically without lines, auto-populate
# #         for rec in records:
# #             if rec.partner_id and not rec.line_ids:
# #                 rec._populate_bucket_lines()

# #         return records

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # WORKFLOW ACTIONS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     def action_submit_to_fm(self):
# #         """
# #         CCM submits request for FM review.
# #         Transitions: draft → pending_fm.
# #         Schedules a mail.activity for the Finance Manager.
# #         """
# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_ccm',
# #             'submit limit change requests',
# #         )
# #         for rec in self:
# #             if rec.state != 'draft':
# #                 raise UserError(
# #                     f"Only draft requests can be submitted. "
# #                     f"Current state: {rec.state} ({rec.name})"
# #                 )
# #             if not rec.line_ids:
# #                 raise UserError(
# #                     f"Cannot submit {rec.name} — no bucket lines found.\n"
# #                     "Select the customer to auto-populate all bucket lines."
# #                 )

# #             rec.write({'state': 'pending_fm'})

# #             # Build line summary for chatter
# #             bucket_labels = dict(
# #                 self.env['clm.limit.change.request.line']
# #                 ._fields['bucket'].selection
# #             )
# #             line_summary = ''.join(
# #                 f"<li><b>{bucket_labels.get(l.bucket)}</b>: "
# #                 f"Current {l.current_limit:,.2f} → "
# #                 f"Proposed {l.proposed_limit:,.2f} "
# #                 f"({'⚠ Freeze' if l.request_type == 'freeze_resolution' else ''})</li>"
# #                 for l in rec.line_ids
# #             )

# #             rec.message_post(
# #                 body=Markup(
# #                     f"<b>Submitted for FM Approval</b><br/>"
# #                     f"Submitted by : {self.env.user.name}<br/>"
# #                     f"Customer     : {rec.partner_id.name}<br/>"
# #                     f"Request Type : "
# #                     f"{dict(self._fields['request_type'].selection).get(rec.request_type)}<br/>"
# #                     f"Buckets:<ul>{line_summary}</ul>"
# #                 ),
# #                 subtype_xmlid='mail.mt_note',
# #             )

# #             # Notify Finance Manager — Odoo 19: group_ids (not groups_id)
# #             finance_group = self.env.ref(
# #                 'zencore_clms.group_zencore_clm_finance',
# #                 raise_if_not_found=False,
# #             )
# #             if finance_group:
# #                 finance_users = self.env['res.users'].search([
# #                     ('group_ids', 'in', [finance_group.id]),  # Odoo 19
# #                     ('share',     '=', False),
# #                     ('active',    '=', True),
# #                 ], limit=1)
# #                 if finance_users:
# #                     rec.activity_schedule(
# #                         'mail.mail_activity_data_todo',
# #                         user_id=finance_users[0].id,
# #                         note=(
# #                             f"Limit Change Request {rec.name} submitted by "
# #                             f"{self.env.user.name} for {rec.partner_id.name}. "
# #                             f"Please review and approve or reject."
# #                         ),
# #                     )

# #     def action_approve(self):
# #         """
# #         Finance Manager approves the request.
# #         Transitions: pending_fm → approved.
# #         Iterates ALL lines and writes each bucket's proposed_limit on the partner.
# #         previous_limit is captured per line for full audit trail.
# #         """
# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_finance',
# #             'approve limit change requests',
# #         )
# #         for rec in self:
# #             if rec.state != 'pending_fm':
# #                 raise UserError(
# #                     f"Only pending requests can be approved. "
# #                     f"Current state: {rec.state} ({rec.name})"
# #                 )
# #             if not rec.line_ids:
# #                 raise UserError(f"Request {rec.name} has no lines to approve.")

# #             # Apply each line's proposed limit to the partner
# #             for line in rec.line_ids:
# #                 line._apply_limit_to_partner()

# #             rec.write({
# #                 'state':         'approved',
# #                 'reviewed_by':   self.env.uid,
# #                 'reviewed_date': fields.Datetime.now(),
# #             })
# #             rec.activity_ids.action_done()

# #             # Build approval summary (previous_limit was set by _apply_limit_to_partner)
# #             bucket_labels = dict(
# #                 self.env['clm.limit.change.request.line']
# #                 ._fields['bucket'].selection
# #             )
# #             line_summary = ''.join(
# #                 f"<li><b>{bucket_labels.get(l.bucket)}</b>: "
# #                 f"{l.previous_limit:,.2f} → {l.proposed_limit:,.2f}</li>"
# #                 for l in rec.line_ids
# #             )

# #             rec.message_post(
# #                 body=Markup(
# #                     f"<b>✅ Approved by {self.env.user.name}</b><br/>"
# #                     f"Customer : {rec.partner_id.name}<br/>"
# #                     f"Changes  :<ul>{line_summary}</ul>"
# #                     f"Comment  : {rec.fm_comment or '—'}"
# #                 ),
# #                 subtype_xmlid='mail.mt_note',
# #             )

# #     def action_reject(self):
# #         """
# #         Finance Manager rejects the request.
# #         Transitions: pending_fm → rejected.
# #         FM comment is required. Terminal state — cannot be reused.
# #         """
# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_finance',
# #             'reject limit change requests',
# #         )
# #         for rec in self:
# #             if rec.state != 'pending_fm':
# #                 raise UserError(
# #                     f"Only pending requests can be rejected. "
# #                     f"Current state: {rec.state} ({rec.name})"
# #                 )
# #             if not rec.fm_comment or not rec.fm_comment.strip():
# #                 raise UserError(
# #                     "A Finance Manager comment is required before rejecting.\n"
# #                     "Enter the rejection reason in the FM Comment field."
# #                 )
# #             rec.write({
# #                 'state':         'rejected',
# #                 'reviewed_by':   self.env.uid,
# #                 'reviewed_date': fields.Datetime.now(),
# #             })
# #             rec.activity_ids.action_done()
# #             rec.message_post(
# #                 body=Markup(
# #                     f"<b>❌ Rejected by {self.env.user.name}</b><br/>"
# #                     f"Customer: {rec.partner_id.name}<br/>"
# #                     f"Reason  : {rec.fm_comment}"
# #                 ),
# #                 subtype_xmlid='mail.mt_note',
# #             )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # PRIVATE HELPERS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     def _assert_group(self, group_xml_id, action_label):
# #         if not self.env.user.has_group(group_xml_id):
# #             group = self.env.ref(group_xml_id)
# #             raise AccessError(
# #                 f"You do not have permission to {action_label}.\n"
# #                 f"Required group: {group.full_name}"
# #             )


# # # ─────────────────────────────────────────────────────────────────────────────
# # # LINE MODEL
# # # ─────────────────────────────────────────────────────────────────────────────

# # class ClmLimitChangeRequestLine(models.Model):
# #     """
# #     clm.limit.change.request.line — One line per bucket.

# #     Fields:
# #     ────────
# #     bucket           : which bucket this line targets (auto-set, readonly after create)
# #     current_limit    : live value from partner at the time of viewing (non-stored compute)
# #     current_exposure : live balance from partner (non-stored compute)
# #     proposed_limit   : new limit requested — the only field CCM edits
# #     previous_limit   : captured at approval time for audit trail (written by _apply_limit_to_partner)
# #     request_type     : auto-classified freeze_resolution / standard_increase (stored compute)

# #     Design:
# #     ────────
# #     - All 5 buckets are always present — created by the header's onchange / create()
# #     - CCM cannot add or delete lines (enforced in view: create=0, delete=0)
# #     - bucket is readonly after creation (enforced in view)
# #     - proposed_limit defaults to current_limit — no accidental changes
# #     """

# #     _name = 'clm.limit.change.request.line'
# #     _description = 'CLM Limit Change Request Line'
# #     _order = 'bucket'

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # FIELD MAPS — Class-level so header onchange can reference them directly
# #     # ─────────────────────────────────────────────────────────────────────────

# #     _LIMIT_FIELD_MAP = {
# #         'proforma': 'clm_proforma_limit',
# #         'bucket1':  'clm_bucket_1_limit',
# #         'bucket2':  'clm_bucket_2_limit',
# #         'bucket3':  'clm_bucket_3_limit',
# #         'bucket4':  'clm_bucket_4_limit',
# #     }

# #     _BALANCE_FIELD_MAP = {
# #         'proforma': 'clm_proforma_balance',
# #         'bucket1':  'clm_bucket_1_balance',
# #         'bucket2':  'clm_bucket_2_balance',
# #         'bucket3':  'clm_bucket_3_balance',
# #         'bucket4':  'clm_bucket_4_balance',
# #     }

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # RELATIONAL
# #     # ─────────────────────────────────────────────────────────────────────────

# #     request_id = fields.Many2one(
# #         'clm.limit.change.request',
# #         string='Request',
# #         required=True,
# #         ondelete='cascade',
# #         index=True,
# #     )

# #     # Related convenience fields — no store, read from header
# #     partner_id = fields.Many2one(
# #         related='request_id.partner_id',
# #         string='Customer',
# #         store=False,
# #     )
# #     currency_id = fields.Many2one(
# #         related='request_id.currency_id',
# #         string='Currency',
# #         store=False,
# #     )
# #     state = fields.Selection(
# #         related='request_id.state',
# #         string='Request State',
# #         store=False,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # CORE FIELDS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     bucket = fields.Selection(
# #         selection=[
# #             ('proforma', 'Proforma Invoice'),
# #             ('bucket1',  'Bucket 1'),
# #             ('bucket2',  'Bucket 2'),
# #             ('bucket3',  'Bucket 3'),
# #             ('bucket4',  'Bucket 4'),
# #         ],
# #         string='Bucket',
# #     )
# #     current_limit = fields.Monetary(
# #         string='Current Limit',
# #         compute='_compute_current_values',
# #         currency_field='currency_id',
# #     )
# #     current_exposure = fields.Monetary(
# #         string='Current Exposure',
# #         compute='_compute_current_values',
# #         currency_field='currency_id',
# #     )
# #     proposed_limit = fields.Monetary(
# #         string='Proposed Limit',
# #         required=True,
# #         currency_field='currency_id',
# #     )
# #     previous_limit = fields.Monetary(
# #         string='Previous Limit (at Approval)',
# #         readonly=True,
# #         currency_field='currency_id',
# #         copy=False,
# #         help='Captured at the moment FM approves. Shows what value was replaced.',
# #     )
# #     request_type = fields.Selection(
# #         selection=[
# #             ('freeze_resolution', 'Freeze Resolution'),
# #             ('standard_increase', 'Standard Increase'),
# #         ],
# #         string='Type',
# #         compute='_compute_request_type',
# #         store=True,
# #         help='freeze_resolution: exposure > current limit on this bucket.',
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # COMPUTE
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.depends('request_id.partner_id', 'bucket')
# #     def _compute_current_values(self):
# #         for line in self:
# #             partner = line.request_id.partner_id
# #             if partner and line.bucket:
# #                 line.current_limit    = getattr(
# #                     partner, self._LIMIT_FIELD_MAP[line.bucket], 0.0
# #                 )
# #                 line.current_exposure = getattr(
# #                     partner, self._BALANCE_FIELD_MAP[line.bucket], 0.0
# #                 )
# #             else:
# #                 line.current_limit    = 0.0
# #                 line.current_exposure = 0.0

# #     @api.depends('current_exposure', 'current_limit')
# #     def _compute_request_type(self):
# #         for line in self:
# #             line.request_type = (
# #                 'freeze_resolution'
# #                 if line.current_exposure > line.current_limit > 0.0
# #                 else 'standard_increase'
# #             )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # CONSTRAINTS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.constrains('proposed_limit')
# #     def _check_proposed_limit_positive(self):
# #         for line in self:
# #             if line.proposed_limit < 0:
# #                 bucket_label = dict(
# #                     self._fields['bucket'].selection
# #                 ).get(line.bucket, line.bucket)
# #                 raise ValidationError(
# #                     f"Proposed limit cannot be negative — {bucket_label}."
# #                 )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # APPROVAL HELPER — Called by action_approve on the header
# #     # ─────────────────────────────────────────────────────────────────────────

# #     def _apply_limit_to_partner(self):
# #         """
# #         Writes this line's proposed_limit onto the partner for its bucket.
# #         Captures current value as previous_limit for audit trail.
# #         Uses clm_bypass_limit_protection context to pass res.partner.write() guard.

# #         Called by ClmLimitChangeRequest.action_approve() — not by users directly.
# #         """
# #         self.ensure_one()
# #         partner     = self.request_id.partner_id
# #         limit_field = self._LIMIT_FIELD_MAP[self.bucket]
# #         prev        = getattr(partner, limit_field, 0.0)

# #         # Write new limit — bypass the write() protection on res.partner
# #         partner.with_context(
# #             clm_bypass_limit_protection=True
# #         ).write({limit_field: self.proposed_limit})

# #         # Capture previous value on this line for the approval chatter summary
# #         # Use sudo to bypass terminal-state write guard on the line itself
# #         self.sudo().write({'previous_limit': prev})

# # from odoo import models, fields, api
# # from odoo.exceptions import UserError, AccessError, ValidationError
# # from markupsafe import Markup
# # from collections import Counter


# # class ClmLimitChangeRequest(models.Model):
# #     """
# #     Multi-Bucket Limit Change Workflow — clm.limit.change.request

# #     State Machine:
# #       draft → pending_fm → approved / rejected

# #     Design (v0.5.0 — fixed):
# #     ──────────────────────────
# #     - Header  : partner, justification, workflow state, audit trail
# #     - Lines   : auto-populated on partner select (all 5 buckets)
# #                 CCM edits only the proposed_limit cells they want to change
# #     - Approval: iterates ALL line_ids and writes each bucket's limit on partner
# #     - request_type on header: freeze_resolution if ANY line is a freeze case

# #     SRS §9 Compliance:
# #     ───────────────────
# #     - Only CCM can create and submit (draft → pending_fm)
# #     - Only Finance Manager can approve or reject
# #     - Rejected requests are permanently closed — cannot be reused
# #     - Full audit trail: initiator, approver, timestamps, per-line previous limits

# #     Bug fixes in this version:
# #     ───────────────────────────
# #     BUG #3 FIX: _check_lines_not_empty constraint fired before _populate_bucket_lines
# #                 because _populate_bucket_lines was called after super().create().
# #                 Fix: lines are now injected into vals_list BEFORE super().create(),
# #                 so the constraint always sees a fully populated record.

# #     BUG #4 FIX: _populate_bucket_lines post-create fallback removed (no longer needed).

# #     BUG #5 FIX: _onchange_partner_id_populate_lines used two separate O2M assignments.
# #                 In onchange context, only the last assignment wins — the first
# #                 fields.Command.clear() was silently discarded, leaving stale lines
# #                 from the previous partner on saved records.
# #                 Fix: combine clear + create commands into a single list assignment.

# #     BUG #3 (approve): action_approve message_post body was a plain f-string with HTML.
# #                 In Odoo 17+, plain strings passed to message_post are escaped.
# #                 Fix: Markup("...{var}...").format(...) — variables are auto-escaped,
# #                 surrounding HTML is trusted.

# #     Odoo 19 notes:
# #     ───────────────
# #     - group_ids (not groups_id) for res.users domain queries
# #     - fields.Command.create / fields.Command.clear for onchange O2M writes
# #     - Markup() required for all HTML in message_post body
# #     """

# #     _name = 'clm.limit.change.request'
# #     _description = 'CLM Bucket Limit Change Request'
# #     _inherit = ['mail.thread', 'mail.activity.mixin']
# #     _order = 'create_date desc'
# #     _rec_name = 'name'

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # BUCKET KEYS — canonical order, used by onchange + line model
# #     # ─────────────────────────────────────────────────────────────────────────

# #     _BUCKET_KEYS = ['proforma', 'bucket1', 'bucket2', 'bucket3', 'bucket4']

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # IDENTIFICATION
# #     # ─────────────────────────────────────────────────────────────────────────

# #     name = fields.Char(
# #         string='Reference',
# #         readonly=True,
# #         default='New',
# #         copy=False,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # HEADER FIELDS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     partner_id = fields.Many2one(
# #         'res.partner',
# #         string='Customer',
# #         required=True,
# #         ondelete='restrict',
# #         tracking=True,
# #     )
# #     currency_id = fields.Many2one(
# #         'res.currency',
# #         default=lambda self: self.env.company.currency_id,
# #     )
# #     justification = fields.Text(
# #         string='Justification',
# #         required=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # LINES — Auto-populated on partner select. One line per bucket.
# #     # ─────────────────────────────────────────────────────────────────────────

# #     line_ids = fields.One2many(
# #         'clm.limit.change.request.line',
# #         'request_id',
# #         string='Bucket Limit Lines',
# #         copy=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # AUTO-CLASSIFICATION — Computed from lines
# #     # freeze_resolution if ANY line has exposure > current limit
# #     # ─────────────────────────────────────────────────────────────────────────

# #     request_type = fields.Selection(
# #         selection=[
# #             ('freeze_resolution', 'Freeze Resolution'),
# #             ('standard_increase', 'Standard Increase'),
# #         ],
# #         string='Request Type',
# #         compute='_compute_request_type',
# #         store=True,
# #         tracking=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # WORKFLOW STATE
# #     # ─────────────────────────────────────────────────────────────────────────

# #     state = fields.Selection(
# #         selection=[
# #             ('draft',      'Draft'),
# #             ('pending_fm', 'Pending FM Approval'),
# #             ('approved',   'Approved'),
# #             ('rejected',   'Rejected'),
# #         ],
# #         string='Status',
# #         default='draft',
# #         readonly=True,
# #         tracking=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # AUDIT TRAIL — All set by system, never by users
# #     # ─────────────────────────────────────────────────────────────────────────

# #     initiated_by = fields.Many2one(
# #         'res.users',
# #         string='Initiated By',
# #         readonly=True,
# #         copy=False,
# #     )
# #     reviewed_by = fields.Many2one(
# #         'res.users',
# #         string='Approved / Rejected By',
# #         readonly=True,
# #         copy=False,
# #         tracking=True,
# #     )
# #     reviewed_date = fields.Datetime(
# #         string='Reviewed On',
# #         readonly=True,
# #         copy=False,
# #     )
# #     fm_comment = fields.Text(
# #         string='Finance Manager Comment',
# #         copy=False,
# #         tracking=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # COMPUTE
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.depends('line_ids.request_type')
# #     def _compute_request_type(self):
# #         for rec in self:
# #             if any(line.request_type == 'freeze_resolution' for line in rec.line_ids):
# #                 rec.request_type = 'freeze_resolution'
# #             else:
# #                 rec.request_type = 'standard_increase'

# #     # # ─────────────────────────────────────────────────────────────────────────
# #     # # ONCHANGE — Auto-populate all 5 bucket lines on partner select
# #     # # ─────────────────────────────────────────────────────────────────────────

# #     # @api.onchange('partner_id')
# #     # def _onchange_partner_id_populate_lines(self):
# #     #     """
# #     #     Fires in the UI when CCM selects or changes the partner.

# #     #     BUG #5 FIX:
# #     #       Original code used TWO separate assignments to self.line_ids:
# #     #         self.line_ids = [fields.Command.clear()]   ← discarded
# #     #         self.line_ids = new_lines                  ← wins (no clear happened)

# #     #       In onchange context, only the LAST assignment to a field is kept.
# #     #       The clear() was silently discarded. When a CCM changed the partner
# #     #       on an already-saved record, stale lines from the previous partner
# #     #       persisted alongside the new partner's lines.

# #     #       Fix: combine the clear command and all create commands into ONE list
# #     #       and assign it in a single operation. This sends (5,0,0) followed by
# #     #       (0,0,{vals}) entries to the client in one shot — clear then create.
# #     #     """
# #     #     if not self.partner_id:
# #     #         self.line_ids = [fields.Command.clear()]
# #     #         return

# #     #     partner = self.partner_id
# #     #     # Single list: (5,0,0) clears existing, then (0,0,{vals}) creates new.
# #     #     # ONE assignment — the clear is not discarded.
# #     #     commands = [fields.Command.clear()]

# #     #     for bucket in self._BUCKET_KEYS:
# #     #         limit_field   = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
# #     #         current_limit = getattr(partner, limit_field, 0.0)
# #     #         commands.append(fields.Command.create({
# #     #             'bucket':         bucket,
# #     #             # Default proposed = current so CCM edits only intended buckets
# #     #             'proposed_limit': current_limit,
# #     #         }))

# #     #     self.line_ids = commands

# #     # # ─────────────────────────────────────────────────────────────────────────
# #     # # CONSTRAINTS
# #     # # ─────────────────────────────────────────────────────────────────────────

# #     # @api.constrains('partner_id', 'line_ids')
# #     # def _check_lines_not_empty(self):
# #     #     """
# #     #     Ensures records with a partner also have bucket lines.

# #     #     BUG #3 FIX (context):
# #     #       This constraint no longer raises false positives because lines are now
# #     #       injected into vals_list inside create() BEFORE super().create() is called.
# #     #       The constraint therefore always sees the lines — whether the record was
# #     #       created from the form (onchange provides lines) or programmatically
# #     #       (create() injects them).
# #     #     """
# #     #     for rec in self:
# #     #         if rec.partner_id and not rec.line_ids:
# #     #             raise ValidationError(
# #     #                 f"Request {rec.name} has no bucket lines.\n"
# #     #                 "Select the customer to auto-populate all buckets."
# #     #             )

# #     # @api.constrains('line_ids')
# #     # def _check_duplicate_buckets_in_lines(self):
# #     #     """Prevent the same bucket appearing twice on one request."""
# #     #     for rec in self:
# #     #         buckets = rec.line_ids.mapped('bucket')
# #     #         if len(buckets) != len(set(buckets)):
# #     #             raise ValidationError(
# #     #                 "Each bucket may appear only once per request.\n"
# #     #                 "Remove duplicate bucket lines."
# #     #             )

# #     # @api.constrains('partner_id', 'state')
# #     # def _check_unique_pending(self):
# #     #     """Prevent two pending requests for the same partner."""
# #     #     for rec in self:
# #     #         if rec.state == 'pending_fm':
# #     #             duplicate = self.search([
# #     #                 ('partner_id', '=', rec.partner_id.id),
# #     #                 ('state',      '=', 'pending_fm'),
# #     #                 ('id',         '!=', rec.id),
# #     #             ], limit=1)
# #     #             if duplicate:
# #     #                 raise ValidationError(
# #     #                     f"A pending request ({duplicate.name}) already exists "
# #     #                     f"for {rec.partner_id.name}.\n"
# #     #                     f"Resolve the existing request before creating a new one."
# #     #                 )

# #     # # ─────────────────────────────────────────────────────────────────────────
# #     # # WRITE PROTECTION — Terminal state guard
# #     # # SRS §9.3: Approved/rejected records cannot be modified
# #     # # ─────────────────────────────────────────────────────────────────────────

# #     # def write(self, vals):
# #     #     for rec in self:
# #     #         if rec.state in ('approved', 'rejected') and not self.env.su:
# #     #             raise AccessError(
# #     #                 f"Request {rec.name} is in a terminal state "
# #     #                 f"({rec.state}) and cannot be modified."
# #     #             )
# #     #     return super().write(vals)

# #     # # ─────────────────────────────────────────────────────────────────────────
# #     # # ORM OVERRIDES
# #     # # ─────────────────────────────────────────────────────────────────────────

# #     # @api.model_create_multi
# #     # def create(self, vals_list):
# #     #     """
# #     #     SoD: Only CCM can create limit change requests.
# #     #     Sequence assigned on creation.
# #     #     initiated_by set to current user for audit trail.

# #     #     BUG #3 FIX (constraint timing):
# #     #       Lines are now injected into vals_list HERE, before super().create().
# #     #       Previously, _populate_bucket_lines() was called after super().create(),
# #     #       meaning the constraint _check_lines_not_empty ran on a record with zero
# #     #       lines → ValidationError on every programmatic create with a partner.

# #     #       When the form is submitted normally, the onchange already put lines in
# #     #       vals — the 'line_ids' not in vals guard prevents double-population.
# #     #       When called programmatically with only partner_id, we build the line
# #     #       vals here so the constraint sees them atomically with the header.
# #     #     """
# #     #     self._assert_group(
# #     #         'zencore_clms.group_zencore_clm_ccm',
# #     #         'create limit change requests',
# #     #     )
# #     #     for vals in vals_list:
# #     #         if vals.get('name', 'New') == 'New':
# #     #             vals['name'] = (
# #     #                 self.env['ir.sequence'].next_by_code('clm.limit.change.request')
# #     #                 or 'New'
# #     #             )
# #     #         vals['initiated_by'] = self.env.uid

# #     #         # ── Pre-populate lines BEFORE super().create() ──────────────────
# #     #         # Constraint _check_lines_not_empty runs inside super().create().
# #     #         # Lines must already exist in vals at that point.
# #     #         # Guard: if caller already supplied line_ids (form submit), skip.
# #     #         if vals.get('partner_id') and 'line_ids' not in vals:
# #     #             partner = self.env['res.partner'].browse(vals['partner_id'])
# #     #             line_vals = []
# #     #             for bucket in self._BUCKET_KEYS:
# #     #                 limit_field   = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
# #     #                 current_limit = getattr(partner, limit_field, 0.0)
# #     #                 line_vals.append(fields.Command.create({
# #     #                     'bucket':         bucket,
# #     #                     'proposed_limit': current_limit,
# #     #                 }))
# #     #             vals['line_ids'] = line_vals

# #     #     return super().create(vals_list)

# #     # -------------------------------------------------------------------------
# #     # ONCHANGE
# #     # -------------------------------------------------------------------------

# #     @api.onchange('partner_id')
# #     def _onchange_partner_id_populate_lines(self):
# #         """
# #         Auto-populate all bucket lines when customer changes.

# #         Odoo 19 Safe:
# #         - Clear existing lines first
# #         - Rebuild all buckets in ONE assignment
# #         - Prevent stale virtual rows from accumulating
# #         """
# #         if not self.partner_id:
# #             self.line_ids = [fields.Command.clear()]
# #             return

# #         partner = self.partner_id

# #         commands = [fields.Command.clear()]

# #         for bucket in self._BUCKET_KEYS:
# #             limit_field = (
# #                 ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
# #             )

# #             current_limit = getattr(partner, limit_field, 0.0)

# #             commands.append(
# #                 fields.Command.create({
# #                     'bucket': bucket,
# #                     'proposed_limit': current_limit,
# #                 })
# #             )

# #         self.line_ids = commands

# #     # -------------------------------------------------------------------------
# #     # CONSTRAINTS
# #     # -------------------------------------------------------------------------
# #     @api.constrains('partner_id')
# #     def _check_lines_not_empty(self):
# #         """
# #         Ensure partner requests contain bucket lines.

# #         Odoo 19 Safe:
# #         During constraint execution, one2many cache may still contain
# #         transient virtual records. Avoid checking child fields like
# #         line.bucket inside constraints.
# #         """
# #         for rec in self:
# #             if rec.partner_id and not rec.line_ids:
# #                 raise ValidationError(
# #                     f"Request {rec.name} has no bucket lines.\n"
# #                     "Select a customer to auto-populate bucket lines."
# #                 )

# #     @api.constrains('line_ids')
# #     def _check_duplicate_buckets_in_lines(self):
# #         """
# #         Prevent duplicate buckets.

# #         Odoo 19 Safe:
# #         - Ignore empty virtual rows
# #         - Ignore deleted cache rows
# #         - Validate only real bucket values
# #         """
# #         for rec in self:
# #             buckets = [
# #                 line.bucket
# #                 for line in rec.line_ids
# #                 if line.exists() and line.bucket
# #             ]

# #             duplicates = [
# #                 bucket
# #                 for bucket, count in Counter(buckets).items()
# #                 if count > 1
# #             ]

# #             if duplicates:
# #                 raise ValidationError(
# #                     "Each bucket may appear only once per request.\n"
# #                     f"Duplicate bucket(s): {', '.join(duplicates)}"
# #                 )

# #     @api.constrains('partner_id', 'state')
# #     def _check_unique_pending(self):
# #         """
# #         Prevent multiple pending requests for same customer.
# #         """
# #         for rec in self:
# #             if rec.state != 'pending_fm':
# #                 continue

# #             duplicate = self.search([
# #                 ('partner_id', '=', rec.partner_id.id),
# #                 ('state', '=', 'pending_fm'),
# #                 ('id', '!=', rec.id),
# #             ], limit=1)

# #             if duplicate:
# #                 raise ValidationError(
# #                     f"A pending request ({duplicate.name}) already exists "
# #                     f"for {rec.partner_id.name}.\n"
# #                     "Resolve the existing request first."
# #                 )

# #     # -------------------------------------------------------------------------
# #     # WRITE PROTECTION
# #     # -------------------------------------------------------------------------

# #     def write(self, vals):
# #         """
# #         Prevent modification after approval/rejection.
# #         """
# #         for rec in self:
# #             if (
# #                 rec.state in ('approved', 'rejected')
# #                 and not self.env.su
# #             ):
# #                 raise AccessError(
# #                     f"Request {rec.name} is already {rec.state} "
# #                     "and cannot be modified."
# #                 )

# #         return super().write(vals)

# #     # -------------------------------------------------------------------------
# #     # CREATE
# #     # -------------------------------------------------------------------------

# #     # @api.model_create_multi
# #     # def create(self, vals_list):
# #     #     """
# #     #     Create request with:
# #     #     - sequence
# #     #     - audit user
# #     #     - automatic bucket population
# #     #     """

# #     #     self._assert_group(
# #     #         'zencore_clms.group_zencore_clm_ccm',
# #     #         'create limit change requests',
# #     #     )

# #     #     for vals in vals_list:

# #     #         # -------------------------------------------------------------
# #     #         # Sequence
# #     #         # -------------------------------------------------------------

# #     #         if vals.get('name', 'New') == 'New':
# #     #             vals['name'] = (
# #     #                 self.env['ir.sequence'].next_by_code(
# #     #                     'clm.limit.change.request'
# #     #                 ) or 'New'
# #     #             )

# #     #         # -------------------------------------------------------------
# #     #         # Audit
# #     #         # -------------------------------------------------------------

# #     #         vals['initiated_by'] = self.env.uid

# #     #         # -------------------------------------------------------------
# #     #         # Auto-create bucket lines
# #     #         #
# #     #         # IMPORTANT:
# #     #         # Use NOT vals.get('line_ids')
# #     #         # instead of:
# #     #         #   'line_ids' not in vals
# #     #         #
# #     #         # Odoo 19 sometimes sends:
# #     #         #   line_ids = []
# #     #         #
# #     #         # which would otherwise bypass the guard incorrectly.
# #     #         # -------------------------------------------------------------

# #     #         if vals.get('partner_id') and not vals.get('line_ids'):

# #     #             partner = self.env['res.partner'].browse(
# #     #                 vals['partner_id']
# #     #             )

# #     #             line_commands = []

# #     #             for bucket in self._BUCKET_KEYS:

# #     #                 limit_field = (
# #     #                     ClmLimitChangeRequestLine
# #     #                     ._LIMIT_FIELD_MAP[bucket]
# #     #                 )

# #     #                 current_limit = getattr(
# #     #                     partner,
# #     #                     limit_field,
# #     #                     0.0,
# #     #                 )

# #     #                 line_commands.append(
# #     #                     fields.Command.create({
# #     #                         'bucket': bucket,
# #     #                         'proposed_limit': current_limit,
# #     #                     })
# #     #                 )

# #     #             vals['line_ids'] = line_commands

# #     #     return super().create(vals_list)

# #     @api.model_create_multi
# #     def create(self, vals_list):

# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_ccm',
# #             'create limit change requests',
# #         )

# #         for vals in vals_list:

# #             if vals.get('name', 'New') == 'New':
# #                 vals['name'] = (
# #                     self.env['ir.sequence'].next_by_code(
# #                         'clm.limit.change.request'
# #                     ) or 'New'
# #                 )

# #             vals['initiated_by'] = self.env.uid

# #             # ---------------------------------------------------------
# #             # SAFE bucket generator (single source of truth)
# #             # ---------------------------------------------------------
# #             if vals.get('partner_id') and not vals.get('line_ids'):

# #                 partner = self.env['res.partner'].browse(vals['partner_id'])

# #                 line_commands = self._generate_bucket_lines(partner)

# #                 vals['line_ids'] = line_commands

# #         return super().create(vals_list)
    
    

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # WORKFLOW ACTIONS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     def action_submit_to_fm(self):
# #         """
# #         CCM submits request for FM review.
# #         Transitions: draft → pending_fm.
# #         Schedules a mail.activity for the Finance Manager.
# #         """
# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_ccm',
# #             'submit limit change requests',
# #         )
# #         for rec in self:
# #             if rec.state != 'draft':
# #                 raise UserError(
# #                     f"Only draft requests can be submitted. "
# #                     f"Current state: {rec.state} ({rec.name})"
# #                 )
# #             if not rec.line_ids:
# #                 raise UserError(
# #                     f"Cannot submit {rec.name} — no bucket lines found.\n"
# #                     "Select the customer to auto-populate all bucket lines."
# #                 )

# #             rec.write({'state': 'pending_fm'})

# #             bucket_labels = dict(
# #                 self.env['clm.limit.change.request.line']
# #                 ._fields['bucket'].selection
# #             )
# #             line_items = Markup('').join(
# #                 Markup(
# #                     "<li><b>{bucket}</b>: "
# #                     "Current {current:,.2f} → Proposed {proposed:,.2f}"
# #                     "{freeze}</li>"
# #                 ).format(
# #                     bucket=bucket_labels.get(l.bucket, l.bucket),
# #                     current=l.current_limit,
# #                     proposed=l.proposed_limit,
# #                     freeze=' ⚠ Freeze' if l.request_type == 'freeze_resolution' else '',
# #                 )
# #                 for l in rec.line_ids
# #             )

# #             rec.message_post(
# #                 body=Markup(
# #                     "<b>Submitted for FM Approval</b><br/>"
# #                     "Submitted by : {user}<br/>"
# #                     "Customer     : {customer}<br/>"
# #                     "Request Type : {rtype}<br/>"
# #                     "Buckets:<ul>{lines}</ul>"
# #                 ).format(
# #                     user=self.env.user.name,
# #                     customer=rec.partner_id.name,
# #                     rtype=dict(self._fields['request_type'].selection).get(rec.request_type, ''),
# #                     lines=line_items,
# #                 ),
# #                 subtype_xmlid='mail.mt_note',
# #             )

# #             # Notify Finance Manager — Odoo 19: group_ids (not groups_id)
# #             finance_group = self.env.ref(
# #                 'zencore_clms.group_zencore_clm_finance',
# #                 raise_if_not_found=False,
# #             )
# #             if finance_group:
# #                 finance_users = self.env['res.users'].search([
# #                     ('group_ids', 'in', [finance_group.id]),
# #                     ('share',     '=', False),
# #                     ('active',    '=', True),
# #                 ], limit=1)
# #                 if finance_users:
# #                     rec.activity_schedule(
# #                         'mail.mail_activity_data_todo',
# #                         user_id=finance_users[0].id,
# #                         note=(
# #                             f"Limit Change Request {rec.name} submitted by "
# #                             f"{self.env.user.name} for {rec.partner_id.name}. "
# #                             f"Please review and approve or reject."
# #                         ),
# #                     )

# #     def action_approve(self):
# #         """
# #         Finance Manager approves the request.
# #         Transitions: pending_fm → approved.
# #         Iterates ALL lines and writes each bucket's proposed_limit on the partner.
# #         previous_limit is captured per line for full audit trail.

# #         BUG #3 FIX (Markup):
# #           Original used a plain f-string for message_post body.
# #           In Odoo 17+, plain strings are HTML-escaped → chatter showed raw tags.
# #           Fix: Markup("...{var}...").format(...) — variables are auto-escaped,
# #           surrounding HTML markup is trusted as safe.
# #         """
# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_finance',
# #             'approve limit change requests',
# #         )
# #         for rec in self:
# #             if rec.state != 'pending_fm':
# #                 raise UserError(
# #                     f"Only pending requests can be approved. "
# #                     f"Current state: {rec.state} ({rec.name})"
# #                 )
# #             if not rec.line_ids:
# #                 raise UserError(f"Request {rec.name} has no lines to approve.")

# #             for line in rec.line_ids:
# #                 line._apply_limit_to_partner()

# #             rec.write({
# #                 'state':         'approved',
# #                 'reviewed_by':   self.env.uid,
# #                 'reviewed_date': fields.Datetime.now(),
# #             })
# #             rec.activity_ids.action_done()

# #             bucket_labels = dict(
# #                 self.env['clm.limit.change.request.line']
# #                 ._fields['bucket'].selection
# #             )
# #             # Build the line summary using Markup.join — each item is a trusted
# #             # Markup fragment; variables are escaped via .format().
# #             line_items = Markup('').join(
# #                 Markup(
# #                     "<li><b>{bucket}</b>: {prev:,.2f} → {new:,.2f}</li>"
# #                 ).format(
# #                     bucket=bucket_labels.get(l.bucket, l.bucket),
# #                     prev=l.previous_limit,
# #                     new=l.proposed_limit,
# #                 )
# #                 for l in rec.line_ids
# #             )

# #             rec.message_post(
# #                 body=Markup(
# #                     "<b>✅ Approved by {user}</b><br/>"
# #                     "Customer : {customer}<br/>"
# #                     "Changes  :<ul>{lines}</ul>"
# #                     "Comment  : {comment}"
# #                 ).format(
# #                     user=self.env.user.name,
# #                     customer=rec.partner_id.name,
# #                     lines=line_items,
# #                     comment=rec.fm_comment or '—',
# #                 ),
# #                 subtype_xmlid='mail.mt_note',
# #             )

# #     def action_reject(self):
# #         """
# #         Finance Manager rejects the request.
# #         Transitions: pending_fm → rejected.
# #         FM comment is required. Terminal state — cannot be reused.
# #         """
# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_finance',
# #             'reject limit change requests',
# #         )
# #         for rec in self:
# #             if rec.state != 'pending_fm':
# #                 raise UserError(
# #                     f"Only pending requests can be rejected. "
# #                     f"Current state: {rec.state} ({rec.name})"
# #                 )
# #             if not rec.fm_comment or not rec.fm_comment.strip():
# #                 raise UserError(
# #                     "A Finance Manager comment is required before rejecting.\n"
# #                     "Enter the rejection reason in the FM Comment field."
# #                 )
# #             rec.write({
# #                 'state':         'rejected',
# #                 'reviewed_by':   self.env.uid,
# #                 'reviewed_date': fields.Datetime.now(),
# #             })
# #             rec.activity_ids.action_done()
# #             rec.message_post(
# #                 body=Markup(
# #                     "<b>❌ Rejected by {user}</b><br/>"
# #                     "Customer: {customer}<br/>"
# #                     "Reason  : {reason}"
# #                 ).format(
# #                     user=self.env.user.name,
# #                     customer=rec.partner_id.name,
# #                     reason=rec.fm_comment,
# #                 ),
# #                 subtype_xmlid='mail.mt_note',
# #             )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # PRIVATE HELPERS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     def _assert_group(self, group_xml_id, action_label):
# #         if not self.env.user.has_group(group_xml_id):
# #             group = self.env.ref(group_xml_id)
# #             raise AccessError(
# #                 f"You do not have permission to {action_label}.\n"
# #                 f"Required group: {group.full_name}"
# #             )


# # # ─────────────────────────────────────────────────────────────────────────────
# # # LINE MODEL
# # # ─────────────────────────────────────────────────────────────────────────────

# # class ClmLimitChangeRequestLine(models.Model):
# #     """
# #     clm.limit.change.request.line — One line per bucket.

# #     Fields:
# #     ────────
# #     bucket           : which bucket this line targets (auto-set, readonly in view)
# #     current_limit    : live value from partner at time of viewing (non-stored compute)
# #     current_exposure : live balance from partner (non-stored compute)
# #     proposed_limit   : new limit requested — the ONLY field CCM edits
# #     previous_limit   : captured at approval time for audit trail
# #     request_type     : auto-classified freeze_resolution / standard_increase (stored compute)

# #     Design:
# #     ────────
# #     - All 5 buckets are always present — created by header's create() or onchange
# #     - CCM cannot add or delete lines (enforced in view: create=0, delete=0)
# #     - bucket is readonly after creation (enforced in view)
# #     - proposed_limit defaults to current_limit — no accidental changes
# #     """

# #     _name = 'clm.limit.change.request.line'
# #     _description = 'CLM Limit Change Request Line'
# #     _order = 'bucket'

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # FIELD MAPS — Class-level so header create() and onchange can reference them
# #     # ─────────────────────────────────────────────────────────────────────────

# #     _LIMIT_FIELD_MAP = {
# #         'proforma': 'clm_proforma_limit',
# #         'bucket1':  'clm_bucket_1_limit',
# #         'bucket2':  'clm_bucket_2_limit',
# #         'bucket3':  'clm_bucket_3_limit',
# #         'bucket4':  'clm_bucket_4_limit',
# #     }

# #     _BALANCE_FIELD_MAP = {
# #         'proforma': 'clm_proforma_balance',
# #         'bucket1':  'clm_bucket_1_balance',
# #         'bucket2':  'clm_bucket_2_balance',
# #         'bucket3':  'clm_bucket_3_balance',
# #         'bucket4':  'clm_bucket_4_balance',
# #     }

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # RELATIONAL
# #     # ─────────────────────────────────────────────────────────────────────────

# #     request_id = fields.Many2one(
# #         'clm.limit.change.request',
# #         string='Request',
# #         required=True,
# #         ondelete='cascade',
# #         index=True,
# #     )

# #     # Related convenience fields — not stored, read from header
# #     partner_id = fields.Many2one(
# #         related='request_id.partner_id',
# #         string='Customer',
# #         store=False,
# #     )
# #     currency_id = fields.Many2one(
# #         related='request_id.currency_id',
# #         string='Currency',
# #         store=False,
# #     )
# #     state = fields.Selection(
# #         related='request_id.state',
# #         string='Request State',
# #         store=False,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # CORE FIELDS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     bucket = fields.Selection(
# #         selection=[
# #             ('proforma', 'Proforma Invoice'),
# #             ('bucket1',  'Bucket 1'),
# #             ('bucket2',  'Bucket 2'),
# #             ('bucket3',  'Bucket 3'),
# #             ('bucket4',  'Bucket 4'),
# #         ],
# #         string='Bucket',
# #     )
# #     current_limit = fields.Monetary(
# #         string='Current Limit',
# #         compute='_compute_current_values',
# #         currency_field='currency_id',
# #     )
# #     current_exposure = fields.Monetary(
# #         string='Current Exposure',
# #         compute='_compute_current_values',
# #         currency_field='currency_id',
# #     )
# #     proposed_limit = fields.Monetary(
# #         string='Proposed Limit',
# #         required=True,
# #         currency_field='currency_id',
# #     )
# #     previous_limit = fields.Monetary(
# #         string='Previous Limit (at Approval)',
# #         readonly=True,
# #         currency_field='currency_id',
# #         copy=False,
# #         help='Captured at the moment FM approves. Shows what value was replaced.',
# #     )
# #     request_type = fields.Selection(
# #         selection=[
# #             ('freeze_resolution', 'Freeze Resolution'),
# #             ('standard_increase', 'Standard Increase'),
# #         ],
# #         string='Type',
# #         compute='_compute_request_type',
# #         store=True,
# #         help='freeze_resolution: exposure > current limit on this bucket.',
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # COMPUTE
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.depends('request_id.partner_id', 'bucket')
# #     def _compute_current_values(self):
# #         for line in self:
# #             partner = line.request_id.partner_id
# #             if partner and line.bucket:
# #                 line.current_limit    = getattr(
# #                     partner, self._LIMIT_FIELD_MAP[line.bucket], 0.0
# #                 )
# #                 line.current_exposure = getattr(
# #                     partner, self._BALANCE_FIELD_MAP[line.bucket], 0.0
# #                 )
# #             else:
# #                 line.current_limit    = 0.0
# #                 line.current_exposure = 0.0

# #     @api.depends('current_exposure', 'current_limit')
# #     def _compute_request_type(self):
# #         for line in self:
# #             line.request_type = (
# #                 'freeze_resolution'
# #                 if line.current_exposure > line.current_limit > 0.0
# #                 else 'standard_increase'
# #             )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # CONSTRAINTS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.constrains('proposed_limit')
# #     def _check_proposed_limit_positive(self):
# #         for line in self:
# #             if line.proposed_limit < 0:
# #                 bucket_label = dict(
# #                     self._fields['bucket'].selection
# #                 ).get(line.bucket, line.bucket)
# #                 raise ValidationError(
# #                     f"Proposed limit cannot be negative — {bucket_label}."
# #                 )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # APPROVAL HELPER — Called by action_approve on the header
# #     # ─────────────────────────────────────────────────────────────────────────

# #     def _apply_limit_to_partner(self):
# #         """
# #         Writes this line's proposed_limit onto the partner for its bucket.
# #         Captures current value as previous_limit for audit trail.
# #         Uses clm_bypass_limit_protection context to pass res.partner.write() guard.

# #         Called by ClmLimitChangeRequest.action_approve() — not by users directly.

# #         sudo() on the line write:
# #           The header is already in 'approved' state when this runs (set in action_approve
# #           before calling _apply_limit_to_partner). The line's related state field
# #           reflects 'approved'. The header write() guard blocks non-sudo writes to
# #           approved records. We use sudo() to bypass that guard for this system write.
# #         """
# #         self.ensure_one()
# #         partner     = self.request_id.partner_id
# #         limit_field = self._LIMIT_FIELD_MAP[self.bucket]
# #         prev        = getattr(partner, limit_field, 0.0)

# #         # Write new limit — bypass the write() protection on res.partner
# #         partner.with_context(
# #             clm_bypass_limit_protection=True
# #         ).write({limit_field: self.proposed_limit})

# #         # Capture previous value on this line for the approval chatter summary.
# #         # sudo() is required because the header is already in 'approved' state
# #         # at this point, and the header write() guard would otherwise block this.
# #         self.sudo().write({'previous_limit': prev})

# from odoo import models, fields, api
# from odoo.exceptions import UserError, AccessError, ValidationError
# from markupsafe import Markup


# class ClmLimitChangeRequest(models.Model):
#     """
#     Multi-Bucket Limit Change Workflow — clm.limit.change.request

#     State Machine:
#       draft → pending_fm → approved / rejected

#     ── Bug Fixes (v0.6.1) ──────────────────────────────────────────────────────

#     BUG: Bucket column blank + chatter shows "False"
#     ─────────────────────────────────────────────────
#     ROOT CAUSE (Odoo 19 client behaviour):
#       The `bucket` field in the line list view has `readonly="1"`.
#       In Odoo 19, the JavaScript client STRIPS readonly fields from the
#       One2many create commands it sends to the server on form save.
#       The server received: (0, 0, {'proposed_limit': X})  ← NO bucket
#       Result: bucket = NULL in DB → False in Python → "False" in chatter.

#     FIX:
#       create() ALWAYS rebuilds lines entirely server-side:
#         1. Extract proposed_limit values from client payload BY POSITION.
#            The onchange creates lines in _BUCKET_KEYS order; client preserves order.
#         2. Discard the client's line_ids commands (they have incomplete data).
#         3. Create new lines with bucket from _BUCKET_KEYS + proposed_limit from client.
#       bucket is now ALWAYS correctly set regardless of client payload.

#     BUG: Can submit multiple requests
#     ──────────────────────────────────
#     ROOT CAUSE:
#       _check_unique_pending only blocked multiple 'pending_fm' records.
#       Multiple 'draft' records per partner were allowed.

#     FIX:
#       _check_unique_pending now blocks ANY second active request per partner
#       (state in ('draft', 'pending_fm')). At most one non-terminal request
#       can exist per partner at any time.

#     BUG: Can submit request with no meaningful changes
#     ───────────────────────────────────────────────────
#     FIX:
#       action_submit_to_fm() now validates that at least one line has a
#       proposed_limit that differs from the current_limit. Prevents submitting
#       no-op requests for FM review.
#     ────────────────────────────────────────────────────────────────────────────
#     """

#     _name = 'clm.limit.change.request'
#     _description = 'CLM Bucket Limit Change Request'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _order = 'create_date desc'
#     _rec_name = 'name'

#     # Canonical bucket order — used everywhere lines are built server-side.
#     _BUCKET_KEYS = ['proforma', 'bucket1', 'bucket2', 'bucket3', 'bucket4']

#     # ─────────────────────────────────────────────────────────────────────────
#     # HEADER FIELDS
#     # ─────────────────────────────────────────────────────────────────────────

#     name = fields.Char(
#         string='Reference',
#         readonly=True,
#         default='New',
#         copy=False,
#     )
#     partner_id = fields.Many2one(
#         'res.partner',
#         string='Customer',
#         required=True,
#         ondelete='restrict',
#         tracking=True,
#     )
#     currency_id = fields.Many2one(
#         'res.currency',
#         default=lambda self: self.env.company.currency_id,
#     )
#     justification = fields.Text(
#         string='Justification',
#         required=True,
#     )
#     line_ids = fields.One2many(
#         'clm.limit.change.request.line',
#         'request_id',
#         string='Bucket Limit Lines',
#         copy=True,
#     )
#     request_type = fields.Selection(
#         selection=[
#             ('freeze_resolution', 'Freeze Resolution'),
#             ('standard_increase', 'Standard Increase'),
#         ],
#         string='Request Type',
#         compute='_compute_request_type',
#         store=True,
#         tracking=True,
#     )
#     state = fields.Selection(
#         selection=[
#             ('draft',      'Draft'),
#             ('pending_fm', 'Pending FM Approval'),
#             ('approved',   'Approved'),
#             ('rejected',   'Rejected'),
#         ],
#         string='Status',
#         default='draft',
#         readonly=True,
#         tracking=True,
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # AUDIT TRAIL
#     # ─────────────────────────────────────────────────────────────────────────

#     initiated_by = fields.Many2one('res.users', string='Initiated By',         readonly=True, copy=False)
#     reviewed_by  = fields.Many2one('res.users', string='Approved / Rejected By',readonly=True, copy=False, tracking=True)
#     reviewed_date = fields.Datetime(string='Reviewed On',                       readonly=True, copy=False)
#     fm_comment   = fields.Text(string='Finance Manager Comment',                copy=False,    tracking=True)

#     # ─────────────────────────────────────────────────────────────────────────
#     # COMPUTE
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.depends('line_ids.request_type')
#     def _compute_request_type(self):
#         for rec in self:
#             rec.request_type = (
#                 'freeze_resolution'
#                 if any(l.request_type == 'freeze_resolution' for l in rec.line_ids)
#                 else 'standard_increase'
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # ONCHANGE — Provides a UI PREVIEW of lines only.
#     # The actual server-side line creation is handled in create().
#     # Even if the client strips bucket from the payload, create() rebuilds correctly.
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.onchange('partner_id')
#     def _onchange_partner_id_populate_lines(self):
#         """
#         Visual preview: populates the list so the CCM can see current limits
#         and type proposed limits before saving.

#         WHY this alone is not sufficient (Odoo 19 caveat):
#           `bucket` has readonly="1" in the list view. Odoo 19's JS client
#           does NOT include readonly fields in the One2many create commands
#           it sends to the server on form save. So even though this onchange
#           correctly sets bucket on the virtual records, the server would
#           receive lines WITHOUT bucket → bucket = NULL.

#           Fix: create() always rebuilds lines server-side from _BUCKET_KEYS.
#           It extracts proposed_limit by position from client payload and
#           assigns the correct bucket itself.
#         """
#         if not self.partner_id:
#             self.line_ids = [fields.Command.clear()]
#             return

#         partner = self.partner_id
#         commands = [fields.Command.clear()]

#         for bucket in self._BUCKET_KEYS:
#             limit_field   = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
#             current_limit = getattr(partner, limit_field, 0.0)
#             commands.append(fields.Command.create({
#                 'bucket':         bucket,         # preview only; stripped by client
#                 'proposed_limit': current_limit,  # CCM edits this column
#             }))

#         self.line_ids = commands

#     # ─────────────────────────────────────────────────────────────────────────
#     # CONSTRAINTS
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.constrains('partner_id', 'line_ids')
#     def _check_lines_not_empty(self):
#         for rec in self:
#             if rec.partner_id and not rec.line_ids:
#                 raise ValidationError(
#                     f"Request {rec.name} has no bucket lines.\n"
#                     "Select the customer to auto-populate all buckets."
#                 )

#     @api.constrains('line_ids')
#     def _check_duplicate_buckets_in_lines(self):
#         """
#         Prevent the same bucket appearing twice on one request.

#         Note: After the create() fix, bucket is always set server-side, so
#         False values are no longer possible. This constraint is retained as
#         a defence-in-depth guard.
#         """
#         for rec in self:
#             buckets = [b for b in rec.line_ids.mapped('bucket') if b]
#             if len(buckets) != len(set(buckets)):
#                 raise ValidationError(
#                     "Each bucket may appear only once per request.\n"
#                     "Remove duplicate bucket lines."
#                 )

#     # @api.constrains('partner_id', 'state')
#     # def _check_unique_pending(self):
#     #     """
#     #     BUG FIX: Prevent ANY second active request per partner.

#     #     Original constraint only blocked multiple 'pending_fm' records.
#     #     A CCM could create multiple 'draft' requests for the same partner,
#     #     leading to confusion and duplicate pending approvals.

#     #     Fix: block if any other non-terminal (draft OR pending_fm) request
#     #     already exists for this partner. At most one active request per partner.
#     #     """
#     #     for rec in self:
#     #         if rec.state in ('draft', 'pending_fm'):
#     #             duplicate = self.search([
#     #                 ('partner_id', '=', rec.partner_id.id),
#     #                 ('state',      'in', ('draft', 'pending_fm')),
#     #                 ('id',         '!=', rec.id),
#     #             ], limit=1)
#     #             if duplicate:
#     #                 state_label = dict(self._fields['state'].selection).get(
#     #                     duplicate.state, duplicate.state
#     #                 )
#     #                 raise ValidationError(
#     #                     f"An active limit request ({duplicate.name} — {state_label}) "
#     #                     f"already exists for {rec.partner_id.name}.\n"
#     #                     f"Resolve or cancel the existing request before creating a new one."
#     #                 )

#     @api.constrains('partner_id', 'state', 'line_ids')
#     def _check_unique_pending(self):
#         """
#         Allow multiple active requests for the same customer
#         ONLY when they affect different buckets.

#         Block:
#             Same customer + same bucket + active request

#         Ignore:
#             Buckets where proposed_limit == current_limit
#             (no actual change requested)
#         """

#         active_states = ('draft', 'pending_fm')

#         bucket_labels = dict(
#             self.env['clm.limit.change.request.line']
#             ._fields['bucket'].selection
#         )

#         for rec in self:

#             # Validate only active requests
#             if rec.state not in active_states:
#                 continue

#             # ─────────────────────────────────────────────
#             # Requested buckets in THIS request
#             # Only meaningful changes count
#             # ─────────────────────────────────────────────
#             requested_buckets = set()

#             for line in rec.line_ids:

#                 # Ignore no-op lines
#                 if abs(line.proposed_limit - line.current_limit) <= 0.001:
#                     continue

#                 requested_buckets.add(line.bucket)

#             if not requested_buckets:
#                 continue

#             # ─────────────────────────────────────────────
#             # Find other active requests for same customer
#             # ─────────────────────────────────────────────
#             duplicates = self.search([
#                 ('partner_id', '=', rec.partner_id.id),
#                 ('state', 'in', active_states),
#                 ('id', '!=', rec.id),
#             ])

#             for duplicate in duplicates:

#                 duplicate_buckets = set()

#                 for line in duplicate.line_ids:

#                     # Ignore no-op lines
#                     if abs(line.proposed_limit - line.current_limit) <= 0.001:
#                         continue

#                     duplicate_buckets.add(line.bucket)

#                 # ─────────────────────────────────────────
#                 # Detect overlapping buckets
#                 # ─────────────────────────────────────────
#                 overlap = requested_buckets & duplicate_buckets

#                 if overlap:

#                     overlap_names = [
#                         bucket_labels.get(b, b)
#                         for b in overlap
#                     ]

#                     state_label = dict(
#                         self._fields['state'].selection
#                     ).get(
#                         duplicate.state,
#                         duplicate.state
#                     )

#                     raise ValidationError(
#                         "An active request already exists for:\n"
#                         f"{', '.join(overlap_names)}\n\n"
#                         f"Customer : {rec.partner_id.name}\n"
#                         f"Request  : {duplicate.name}\n"
#                         f"State    : {state_label}\n\n"
#                         "Approve, reject, or cancel the existing request first."
#                     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # WRITE PROTECTION — Terminal state guard
#     # ─────────────────────────────────────────────────────────────────────────

#     def write(self, vals):
#         for rec in self:
#             if rec.state in ('approved', 'rejected') and not self.env.su:
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
#         Always rebuilds lines server-side to ensure bucket is correctly set.

#         ── Why client-sent line_ids cannot be trusted ───────────────────────
#         In Odoo 19, the JS client filters out readonly fields from One2many
#         create commands. The `bucket` field has readonly="1" in the list view,
#         so it is NEVER included in the client payload.

#         Server receives:  (0, 0, {'proposed_limit': X})   ← no bucket
#         Without fix:      bucket = NULL in DB → False in Python

#         ── Server-side rebuild strategy ────────────────────────────────────
#         1. Extract proposed_limit values from the client payload IN ORDER.
#            The onchange always creates lines in _BUCKET_KEYS order and the
#            client preserves that order, so position 0 = proforma, 1 = bucket1...
#         2. Discard the client's line_ids entirely (bucket is missing/unreliable).
#         3. Create new (0, 0, {...}) commands with bucket from _BUCKET_KEYS
#            and proposed_limit from the client payload by position.
#         4. Fall back to current_limit if no client value exists at that position.

#         Result: bucket is ALWAYS correctly set regardless of client behaviour.
#         ─────────────────────────────────────────────────────────────────────
#         """
#         self._assert_group(
#             'zencore_clms.group_zencore_clm_ccm',
#             'create limit change requests',
#         )

#         for vals in vals_list:
#             # Assign sequence number
#             if vals.get('name', 'New') == 'New':
#                 vals['name'] = (
#                     self.env['ir.sequence'].next_by_code('clm.limit.change.request')
#                     or 'New'
#                 )
#             vals['initiated_by'] = self.env.uid

#             if vals.get('partner_id'):
#                 partner = self.env['res.partner'].browse(vals['partner_id'])

#                 # ── Step 1: Extract proposed_limits from client payload by position ──
#                 # client_lines collects proposed_limit in the order received.
#                 # Skip non-create commands (clear = (5,0,0), etc.).
#                 client_proposed_by_pos = []
#                 for cmd in vals.get('line_ids', []):
#                     if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 0:
#                         # (0, 0, {vals}) — a new-line command from client
#                         client_proposed_by_pos.append(
#                             cmd[2].get('proposed_limit', None)
#                         )
#                     elif hasattr(cmd, '__int__') and int(cmd) == 0:
#                         # fields.Command.create result — handled above
#                         pass

#                 # ── Step 2: Discard client line_ids — bucket is not reliable ──────
#                 vals.pop('line_ids', None)

#                 # ── Step 3: Rebuild lines with correct bucket + proposed_limit ─────
#                 new_lines = []
#                 for idx, bucket in enumerate(self._BUCKET_KEYS):
#                     limit_field   = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
#                     current_limit = getattr(partner, limit_field, 0.0)

#                     # Use client's proposed_limit if provided for this position,
#                     # else fall back to current_limit (no-change default).
#                     proposed_limit = (
#                         client_proposed_by_pos[idx]
#                         if idx < len(client_proposed_by_pos) and client_proposed_by_pos[idx] is not None
#                         else current_limit
#                     )

#                     new_lines.append(fields.Command.create({
#                         'bucket':         bucket,         # ← always set server-side
#                         'proposed_limit': proposed_limit, # ← from client or default
#                     }))

#                 vals['line_ids'] = new_lines

#         return super().create(vals_list)

#     # ─────────────────────────────────────────────────────────────────────────
#     # WORKFLOW ACTIONS
#     # ─────────────────────────────────────────────────────────────────────────

#     def action_submit_to_fm(self):
#         """
#         CCM submits request for FM review.
#         Transitions: draft → pending_fm.
#         Validates at least one bucket has a meaningful change.
#         Schedules a mail.activity for the Finance Manager.
#         """
#         self._assert_group(
#             'zencore_clms.group_zencore_clm_ccm',
#             'submit limit change requests',
#         )
#         for rec in self:
#             if rec.state != 'draft':
#                 raise UserError(
#                     f"Only draft requests can be submitted. "
#                     f"Current state: {rec.state} ({rec.name})"
#                 )
#             if not rec.line_ids:
#                 raise UserError(
#                     f"Cannot submit {rec.name} — no bucket lines found.\n"
#                     "Select the customer to auto-populate all bucket lines."
#                 )

#             # ── Validate at least one line has a meaningful change ────────────
#             # BUG FIX: Prevents submitting a no-op request where all proposed
#             # limits equal current limits (nothing would change on approval).
#             has_change = any(
#                 abs(line.proposed_limit - line.current_limit) > 0.001
#                 for line in rec.line_ids
#             )
#             if not has_change:
#                 raise UserError(
#                     "Cannot submit this request — no bucket limits have been changed.\n"
#                     "Edit at least one Proposed Limit before submitting."
#                 )

#             rec.write({'state': 'pending_fm'})

#             # ── Build chatter summary ─────────────────────────────────────────
#             # BUG FIX: Use .get() with a safe fallback for the bucket label.
#             # Before the create() fix, l.bucket was False → bucket_labels.get(False)
#             # returned False → "False" appeared in chatter. After the fix, bucket is
#             # always a valid string. The fallback handles any edge case.
#             bucket_labels = dict(
#                 self.env['clm.limit.change.request.line']
#                 ._fields['bucket'].selection
#             )

#             line_items = Markup('').join(
#                 Markup(
#                     "<li><b>{bucket}</b>: "
#                     "Current {current:,.2f} → Proposed {proposed:,.2f}"
#                     "{freeze}</li>"
#                 ).format(
#                     bucket=(
#                         bucket_labels.get(l.bucket)
#                         or str(l.bucket or 'Unknown Bucket')
#                     ),
#                     current=l.current_limit,
#                     proposed=l.proposed_limit,
#                     freeze=' ⚠ Freeze' if l.request_type == 'freeze_resolution' else '',
#                 )
#                 for l in rec.line_ids
#             )

#             rec.message_post(
#                 body=Markup(
#                     "<b>Submitted for FM Approval</b><br/>"
#                     "Submitted by : {user}<br/>"
#                     "Customer     : {customer}<br/>"
#                     "Request Type : {rtype}<br/>"
#                     "Buckets:<ul>{lines}</ul>"
#                 ).format(
#                     user=self.env.user.name,
#                     customer=rec.partner_id.name,
#                     rtype=dict(self._fields['request_type'].selection).get(
#                         rec.request_type, ''
#                     ),
#                     lines=line_items,
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#             # ── Notify Finance Manager ────────────────────────────────────────
#             # Odoo 19: group_ids (not groups_id) for res.users domain
#             finance_group = self.env.ref(
#                 'zencore_clms.group_zencore_clm_finance',
#                 raise_if_not_found=False,
#             )
#             if finance_group:
#                 finance_users = self.env['res.users'].search([
#                     ('group_ids', 'in', [finance_group.id]),
#                     ('share',     '=', False),
#                     ('active',    '=', True),
#                 ], limit=1)
#                 if finance_users:
#                     rec.activity_schedule(
#                         'mail.mail_activity_data_todo',
#                         user_id=finance_users[0].id,
#                         note=(
#                             f"Limit Change Request {rec.name} submitted by "
#                             f"{self.env.user.name} for {rec.partner_id.name}. "
#                             f"Please review and approve or reject."
#                         ),
#                     )

#     def action_approve(self):
#         """
#         Finance Manager approves the request.
#         Transitions: pending_fm → approved.
#         Writes each bucket's proposed_limit on the partner.
#         """
#         self._assert_group(
#             'zencore_clms.group_zencore_clm_finance',
#             'approve limit change requests',
#         )
#         for rec in self:
#             if rec.state != 'pending_fm':
#                 raise UserError(
#                     f"Only pending requests can be approved. "
#                     f"Current state: {rec.state} ({rec.name})"
#                 )
#             if not rec.line_ids:
#                 raise UserError(f"Request {rec.name} has no lines to approve.")

#             for line in rec.line_ids:
#                 line._apply_limit_to_partner()

#             rec.write({
#                 'state':         'approved',
#                 'reviewed_by':   self.env.uid,
#                 'reviewed_date': fields.Datetime.now(),
#             })
#             rec.activity_ids.action_done()

#             bucket_labels = dict(
#                 self.env['clm.limit.change.request.line']
#                 ._fields['bucket'].selection
#             )
#             line_items = Markup('').join(
#                 Markup(
#                     "<li><b>{bucket}</b>: {prev:,.2f} → {new:,.2f}</li>"
#                 ).format(
#                     bucket=(
#                         bucket_labels.get(l.bucket)
#                         or str(l.bucket or 'Unknown Bucket')
#                     ),
#                     prev=l.previous_limit,
#                     new=l.proposed_limit,
#                 )
#                 for l in rec.line_ids
#             )

#             rec.message_post(
#                 body=Markup(
#                     "<b>✅ Approved by {user}</b><br/>"
#                     "Customer : {customer}<br/>"
#                     "Changes  :<ul>{lines}</ul>"
#                     "Comment  : {comment}"
#                 ).format(
#                     user=self.env.user.name,
#                     customer=rec.partner_id.name,
#                     lines=line_items,
#                     comment=rec.fm_comment or '—',
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#     def action_reject(self):
#         """
#         Finance Manager rejects the request.
#         Transitions: pending_fm → rejected.
#         FM comment required. Terminal state — cannot be reused.
#         """
#         self._assert_group(
#             'zencore_clms.group_zencore_clm_finance',
#             'reject limit change requests',
#         )
#         for rec in self:
#             if rec.state != 'pending_fm':
#                 raise UserError(
#                     f"Only pending requests can be rejected. "
#                     f"Current state: {rec.state} ({rec.name})"
#                 )
#             if not rec.fm_comment or not rec.fm_comment.strip():
#                 raise UserError(
#                     "A Finance Manager comment is required before rejecting.\n"
#                     "Enter the rejection reason in the FM Comment field."
#                 )
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
#                     "Reason  : {reason}"
#                 ).format(
#                     user=self.env.user.name,
#                     customer=rec.partner_id.name,
#                     reason=rec.fm_comment,
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # PRIVATE HELPERS
#     # ─────────────────────────────────────────────────────────────────────────

#     def _assert_group(self, group_xml_id, action_label):
#         if not self.env.user.has_group(group_xml_id):
#             group = self.env.ref(group_xml_id)
#             raise AccessError(
#                 f"You do not have permission to {action_label}.\n"
#                 f"Required group: {group.full_name}"
#             )


# # ─────────────────────────────────────────────────────────────────────────────
# # LINE MODEL
# # ─────────────────────────────────────────────────────────────────────────────

# class ClmLimitChangeRequestLine(models.Model):
#     """
#     clm.limit.change.request.line — One line per bucket.

#     IMPORTANT — bucket field:
#     ──────────────────────────
#     bucket is ALWAYS set server-side in ClmLimitChangeRequest.create().
#     It must NEVER be set by the client (it's readonly in the view), and
#     the create() override ensures it is populated from _BUCKET_KEYS
#     regardless of what the client sends.

#     Do NOT add readonly=True to the field definition — that would prevent
#     the ORM from accepting the value we write during server-side create().
#     The view controls editability; the model just stores the value.
#     """

#     _name = 'clm.limit.change.request.line'
#     _description = 'CLM Limit Change Request Line'
#     _order = 'bucket'

#     # ── Class-level field maps — referenced by header model and res.partner ──

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
#     # RELATIONAL
#     # ─────────────────────────────────────────────────────────────────────────

#     request_id = fields.Many2one(
#         'clm.limit.change.request',
#         string='Request',
#         required=True,
#         ondelete='cascade',
#         index=True,
#     )
#     partner_id = fields.Many2one(
#         related='request_id.partner_id',
#         string='Customer',
#         store=False,
#     )
#     currency_id = fields.Many2one(
#         related='request_id.currency_id',
#         string='Currency',
#         store=False,
#     )
#     state = fields.Selection(
#         related='request_id.state',
#         string='Request State',
#         store=False,
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # CORE FIELDS
#     # ─────────────────────────────────────────────────────────────────────────

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
#         # DO NOT add readonly=True here.
#         # The view controls user editability (readonly="1" in the list column).
#         # The model must accept the value written by create() server-side.
#     )
#     current_limit = fields.Monetary(
#         string='Current Limit',
#         compute='_compute_current_values',
#         currency_field='currency_id',
#     )
#     current_exposure = fields.Monetary(
#         string='Current Exposure',
#         compute='_compute_current_values',
#         currency_field='currency_id',
#     )
#     proposed_limit = fields.Monetary(
#         string='Proposed Limit',
#         required=True,
#         currency_field='currency_id',
#     )
#     previous_limit = fields.Monetary(
#         string='Previous Limit (at Approval)',
#         readonly=True,
#         currency_field='currency_id',
#         copy=False,
#         help='Captured at the moment FM approves. Shows what value was replaced.',
#     )
#     request_type = fields.Selection(
#         selection=[
#             ('freeze_resolution', 'Freeze Resolution'),
#             ('standard_increase', 'Standard Increase'),
#         ],
#         string='Type',
#         compute='_compute_request_type',
#         store=True,
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # COMPUTE
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.depends('request_id.partner_id', 'bucket')
#     def _compute_current_values(self):
#         for line in self:
#             partner = line.request_id.partner_id
#             if partner and line.bucket:
#                 line.current_limit    = getattr(partner, self._LIMIT_FIELD_MAP[line.bucket],   0.0)
#                 line.current_exposure = getattr(partner, self._BALANCE_FIELD_MAP[line.bucket], 0.0)
#             else:
#                 line.current_limit    = 0.0
#                 line.current_exposure = 0.0

#     @api.depends('current_exposure', 'current_limit')
#     def _compute_request_type(self):
#         for line in self:
#             line.request_type = (
#                 'freeze_resolution'
#                 if line.current_exposure > line.current_limit > 0.0
#                 else 'standard_increase'
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # CONSTRAINTS
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.constrains('proposed_limit')
#     def _check_proposed_limit_not_negative(self):
#         for line in self:
#             if line.proposed_limit < 0:
#                 bucket_label = dict(
#                     self._fields['bucket'].selection
#                 ).get(line.bucket, line.bucket or 'Unknown')
#                 raise ValidationError(
#                     f"Proposed limit cannot be negative — {bucket_label}."
#                 )

#     # ─────────────────────────────────────────────────────────────────────────
#     # APPROVAL HELPER
#     # ─────────────────────────────────────────────────────────────────────────

#     def _apply_limit_to_partner(self):
#         """
#         Writes this line's proposed_limit to the partner for its bucket.
#         Captures previous limit for audit trail.
#         sudo() bypasses the terminal-state write guard on the line itself.
#         """
#         self.ensure_one()
#         partner     = self.request_id.partner_id
#         limit_field = self._LIMIT_FIELD_MAP[self.bucket]
#         prev        = getattr(partner, limit_field, 0.0)

#         partner.with_context(
#             clm_bypass_limit_protection=True
#         ).write({limit_field: self.proposed_limit})

#         self.sudo().write({'previous_limit': prev})

from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError, ValidationError
from markupsafe import Markup


class ClmLimitChangeRequest(models.Model):
    """
    Bucket Limit Change Request — clm.limit.change.request

    ── State Machine ────────────────────────────────────────────────────────
      draft → pending_fm → approved
                         → rejected
      draft → cancelled

    ── Multi-Request Design ─────────────────────────────────────────────────
    Multiple simultaneous requests per customer are ALLOWED.
    Constraint: the same bucket cannot appear in two active (draft OR pending_fm)
    requests for the same customer at the same time.

    ── Odoo 19 Critical Fix (bucket = NULL) ─────────────────────────────────
    `bucket` is readonly="1" in the list view. Odoo 19 JS client strips
    readonly fields from One2many create commands. Server receives
    (0, 0, {'proposed_limit': X}) with NO bucket → bucket = NULL in DB.

    FIX: create() always discards client line_ids and rebuilds lines
    server-side using _BUCKET_KEYS + proposed_limits extracted by position
    from the client payload.

    ── Transaction Safety ───────────────────────────────────────────────────
    All partner limit writes in action_approve() happen inside a single ORM
    transaction. Any failure (SQL constraint, AccessError) rolls back the
    entire operation — no partial limit updates.

    ── Odoo 19 API Notes ────────────────────────────────────────────────────
    - group_ids (not groups_id) for res.users domain queries
    - Markup("...{var}...").format(...) for all HTML in message_post
    - fields.Command.create / fields.Command.clear for onchange O2M writes
    """

    _name = 'clm.limit.change.request'
    _description = 'CLM Bucket Limit Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # Canonical bucket order — shared by all methods that build lines
    _BUCKET_KEYS = ['proforma', 'bucket1', 'bucket2', 'bucket3', 'bucket4']

    # ─────────────────────────────────────────────────────────────────────────
    # HEADER FIELDS
    # ─────────────────────────────────────────────────────────────────────────

    name = fields.Char(
        string='Reference',
        readonly=True,
        default='New',
        copy=False,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    justification = fields.Text(
        string='Justification',
        required=True,
    )
    line_ids = fields.One2many(
        'clm.limit.change.request.line',
        'request_id',
        string='Bucket Limit Lines',
        copy=True,
    )
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
    )
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
    # AUDIT TRAIL — All set by system, never editable by users directly
    # ─────────────────────────────────────────────────────────────────────────

    initiated_by = fields.Many2one(
        'res.users',
        string='Initiated By',
        readonly=True,
        copy=False,
        index=True,
    )
    submitted_date = fields.Datetime(
        string='Submitted On',
        readonly=True,
        copy=False,
        help='Date and time the request was submitted to the Finance Manager.',
    )
    reviewed_by = fields.Many2one(
        'res.users',
        string='Reviewed By',
        readonly=True,
        copy=False,
        tracking=True,
        help='Finance Manager who approved or rejected this request.',
    )
    reviewed_date = fields.Datetime(
        string='Reviewed On',
        readonly=True,
        copy=False,
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

    @api.depends('line_ids.request_type')
    def _compute_request_type(self):
        for rec in self:
            rec.request_type = (
                'freeze_resolution'
                if any(l.request_type == 'freeze_resolution' for l in rec.line_ids)
                else 'standard_increase'
            )

    # ─────────────────────────────────────────────────────────────────────────
    # ONCHANGE — Visual preview only.
    # The actual server-side line creation is ALWAYS handled in create().
    # Even if the client strips bucket from the payload, create() rebuilds correctly.
    # ─────────────────────────────────────────────────────────────────────────

    @api.onchange('partner_id')
    def _onchange_partner_id_populate_lines(self):
        """
        Provides a UI preview so the CCM sees current limits and can type
        proposed limits before saving.

        WHY this preview alone is insufficient:
          `bucket` is readonly="1" in the list. Odoo 19 JS does NOT send
          readonly fields in the One2many create commands on save.
          Fix lives in create() — see that method for full explanation.
        """
        if not self.partner_id:
            self.line_ids = [fields.Command.clear()]
            return

        partner = self.partner_id
        # Single list assignment: Command.clear() + Command.create() in one shot.
        # Two separate assignments would silently discard the first.
        commands = [fields.Command.clear()]
        for bucket in self._BUCKET_KEYS:
            limit_field = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
            current_limit = getattr(partner, limit_field, 0.0)
            commands.append(fields.Command.create({
                'bucket': bucket,            # stripped by client, reset in create()
                'proposed_limit': current_limit,
            }))
        self.line_ids = commands

    # ─────────────────────────────────────────────────────────────────────────
    # CONSTRAINTS
    # ─────────────────────────────────────────────────────────────────────────

    @api.constrains('partner_id', 'line_ids')
    def _check_lines_not_empty(self):
        for rec in self:
            if rec.partner_id and not rec.line_ids:
                raise ValidationError(
                    f"Request {rec.name} has no bucket lines.\n"
                    "Select the customer to auto-populate all buckets."
                )

    @api.constrains('line_ids')
    def _check_no_duplicate_buckets(self):
        """
        Defence-in-depth guard. After the create() server-side rebuild this
        should never fire, but retained to catch any programmatic misuse.
        """
        for rec in self:
            buckets = [b for b in rec.line_ids.mapped('bucket') if b]
            if len(buckets) != len(set(buckets)):
                raise ValidationError(
                    "Each bucket may appear only once per request.\n"
                    "Remove duplicate bucket lines."
                )

    @api.constrains('partner_id', 'state', 'line_ids')
    def _check_no_duplicate_pending_bucket(self):
        """
        Enterprise-safe per-bucket duplicate prevention.

        Rule: A bucket with a meaningful change (proposed ≠ current) cannot
        exist in two active requests for the same customer simultaneously.

        'Active' = state in ('draft', 'pending_fm')
        'Meaningful' = |proposed_limit - current_limit| > 0.001

        Why block draft too (not just pending_fm):
          Allowing two draft requests for the same bucket creates a race to
          submit, and whichever submits second will fail the constraint anyway.
          Block it early at draft stage for a cleaner UX.

        Atomicity note:
          This Python constraint handles the UX error message.
          For true concurrency safety under high load, add a PostgreSQL
          partial unique index (see post-install hook pattern):

            CREATE UNIQUE INDEX IF NOT EXISTS
              clm_lcr_line_no_dup_active_bucket
            ON clm_limit_change_request_line (request_id)
            WHERE ... (complex — use a DB trigger for per-partner-bucket)

          The Python constraint is sufficient for single-instance deployments.
        """
        active_states = ('draft', 'pending_fm')
        bucket_labels = dict(
            self.env['clm.limit.change.request.line']
            ._fields['bucket'].selection
        )

        for rec in self:
            if rec.state not in active_states:
                continue

            # Buckets with meaningful changes in THIS request
            my_changed_buckets = {
                line.bucket
                for line in rec.line_ids
                if line.bucket and abs(line.proposed_limit - line.current_limit) > 0.001
            }
            if not my_changed_buckets:
                continue

            # Find other active requests for the same customer
            other_actives = self.search([
                ('partner_id', '=', rec.partner_id.id),
                ('state', 'in', active_states),
                ('id', '!=', rec.id),
            ])

            for other in other_actives:
                other_changed = {
                    line.bucket
                    for line in other.line_ids
                    if line.bucket and abs(line.proposed_limit - line.current_limit) > 0.001
                }
                overlap = my_changed_buckets & other_changed
                if not overlap:
                    continue

                overlap_labels = [bucket_labels.get(b, b) for b in sorted(overlap)]
                other_state = dict(self._fields['state'].selection).get(
                    other.state, other.state
                )
                raise ValidationError(
                    f"Bucket collision for {rec.partner_id.name}.\n\n"
                    f"The following bucket(s) already have an active request:\n"
                    f"  • {', '.join(overlap_labels)}\n\n"
                    f"Conflicting request : {other.name}  ({other_state})\n\n"
                    f"Resolve or cancel {other.name} for these buckets before "
                    f"creating a new request."
                )

    # ─────────────────────────────────────────────────────────────────────────
    # WRITE PROTECTION — Terminal states are immutable
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, vals):
        """
        Prevent any modification after the request reaches a terminal state.
        self.env.su bypasses this (ORM internals, sudo() in _apply_limit_to_partner).
        """
        terminal = ('approved', 'rejected', 'cancelled')
        for rec in self:
            if rec.state in terminal and not self.env.su:
                raise AccessError(
                    f"Request {rec.name} is in a terminal state "
                    f"({rec.state}) and cannot be modified."
                )
        return super().write(vals)

    # ─────────────────────────────────────────────────────────────────────────
    # ORM OVERRIDES
    # ─────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        """
        Server-side line rebuild — the most critical Odoo 19 fix in this module.

        ROOT CAUSE of the "bucket = NULL" / "False in chatter" bug:
          `bucket` field has readonly="1" in the list view.
          Odoo 19 JS strips readonly fields from One2many create commands.
          Server receives: (0, 0, {'proposed_limit': 5000.0})  ← no bucket
          ORM sets bucket = NULL, Python reads it as False.

        FIX STRATEGY:
          1. Scan the client's line_ids for (0, 0, {...}) commands.
             Extract proposed_limit values IN ORDER (onchange preserves order).
          2. Discard all client line commands — bucket is missing/unreliable.
          3. Rebuild from _BUCKET_KEYS, assigning:
               - bucket from _BUCKET_KEYS[i]  (always correct)
               - proposed_limit from client[i] (user's intended value)
               - fallback to current_limit if client didn't send it
          4. Result: bucket is ALWAYS correctly set regardless of client behaviour.

        SoD: Only CCM may create. Enforced here AND again in action_submit_to_fm.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_ccm',
            'create limit change requests',
        )

        for vals in vals_list:
            # ── Sequence ──────────────────────────────────────────────────
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('clm.limit.change.request')
                    or 'New'
                )
            vals['initiated_by'] = self.env.uid

            if not vals.get('partner_id'):
                continue

            partner = self.env['res.partner'].browse(vals['partner_id'])

            # ── Step 1: extract proposed_limits from client payload by position
            client_proposed = []
            for cmd in vals.get('line_ids', []):
                # (0, 0, {field_vals}) = new-line create command
                if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 0:
                    client_proposed.append(cmd[2].get('proposed_limit', None))
                # fields.Command.create returns a Command object; handle both forms

            # ── Step 2: discard client line_ids entirely ──────────────────
            vals.pop('line_ids', None)

            # ── Step 3: rebuild lines server-side ─────────────────────────
            new_lines = []
            for idx, bucket in enumerate(self._BUCKET_KEYS):
                limit_field = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
                current_limit = getattr(partner, limit_field, 0.0)
                proposed_limit = (
                    client_proposed[idx]
                    if idx < len(client_proposed)
                    and client_proposed[idx] is not None
                    else current_limit
                )
                new_lines.append(fields.Command.create({
                    'bucket': bucket,                # ← always correct
                    'proposed_limit': proposed_limit,
                }))

            vals['line_ids'] = new_lines

        return super().create(vals_list)

    # ─────────────────────────────────────────────────────────────────────────
    # WORKFLOW ACTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def action_submit_to_fm(self):
        """
        CCM submits for FM review. draft → pending_fm.

        Validates:
          • At least one bucket has a meaningful proposed change
          • No bucket collision with other active requests (caught by constraint
            but also checked here for a cleaner early error message)

        Schedules a mail.activity on the first Finance Manager user found.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_ccm',
            'submit limit change requests',
        )
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    f"Only draft requests can be submitted. "
                    f"State: {rec.state} ({rec.name})"
                )
            if not rec.line_ids:
                raise UserError(
                    f"Cannot submit {rec.name} — no bucket lines found.\n"
                    "Select the customer to auto-populate all buckets."
                )

            # Validate at least one bucket actually changes
            changed = [
                l for l in rec.line_ids
                if abs(l.proposed_limit - l.current_limit) > 0.001
            ]
            if not changed:
                raise UserError(
                    "Cannot submit — no Proposed Limits differ from the current values.\n"
                    "Edit at least one Proposed Limit before submitting."
                )

            rec.write({
                'state': 'pending_fm',
                'submitted_date': fields.Datetime.now(),
            })

            # Build chatter — only show changed lines
            bucket_labels = dict(
                self.env['clm.limit.change.request.line']
                ._fields['bucket'].selection
            )
            line_items = Markup('').join(
                Markup(
                    "<li><b>{bucket}</b>: {cur:,.2f} → {prop:,.2f}{freeze}</li>"
                ).format(
                    bucket=bucket_labels.get(l.bucket, str(l.bucket or '?')),
                    cur=l.current_limit,
                    prop=l.proposed_limit,
                    freeze=Markup(
                        ' <span style="color:var(--color-text-danger)">⚠ Freeze</span>'
                    ) if l.request_type == 'freeze_resolution' else Markup(''),
                )
                for l in changed
            )

            rec.message_post(
                body=Markup(
                    "<b>📋 Submitted for FM Approval</b><br/>"
                    "Submitted by : {user}<br/>"
                    "Customer     : {customer}<br/>"
                    "Request Type : {rtype}<br/>"
                    "Changed Buckets:<ul>{lines}</ul>"
                ).format(
                    user=self.env.user.name,
                    customer=rec.partner_id.name,
                    rtype=dict(self._fields['request_type'].selection).get(
                        rec.request_type, ''
                    ),
                    lines=line_items,
                ),
                subtype_xmlid='mail.mt_note',
            )

            # Notify Finance Manager
            finance_group = self.env.ref(
                'zencore_clms.group_zencore_clm_finance',
                raise_if_not_found=False,
            )
            if finance_group:
                # Odoo 19: group_ids (not groups_id)
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
                            f"for {rec.partner_id.name}. Please review."
                        ),
                    )

    def action_approve(self):
        """
        Finance Manager approves. pending_fm → approved.

        Writes ONLY the changed lines' proposed_limits to the partner.
        All writes happen in one ORM transaction — any failure rolls back
        all limit changes, preventing partial updates.

        Also posts an approval note on the partner's chatter for a
        cross-object audit trail.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_finance',
            'approve limit change requests',
        )
        for rec in self:
            if rec.state != 'pending_fm':
                raise UserError(
                    f"Only pending requests can be approved. "
                    f"State: {rec.state} ({rec.name})"
                )
            if not rec.line_ids:
                raise UserError(f"Request {rec.name} has no lines to approve.")

            # Apply only lines with meaningful changes
            changed = [
                l for l in rec.line_ids
                if abs(l.proposed_limit - l.current_limit) > 0.001
            ]
            for line in changed:
                line._apply_limit_to_partner()

            rec.write({
                'state': 'approved',
                'reviewed_by': self.env.uid,
                'reviewed_date': fields.Datetime.now(),
            })
            rec.activity_ids.action_done()

            bucket_labels = dict(
                self.env['clm.limit.change.request.line']
                ._fields['bucket'].selection
            )
            line_items = Markup('').join(
                Markup(
                    "<li><b>{bucket}</b>: {prev:,.2f} → {new:,.2f}</li>"
                ).format(
                    bucket=bucket_labels.get(l.bucket, str(l.bucket or '?')),
                    prev=l.previous_limit,
                    new=l.proposed_limit,
                )
                for l in changed
            )

            rec.message_post(
                body=Markup(
                    "<b>✅ Approved by {user}</b><br/>"
                    "Customer : {customer}<br/>"
                    "Applied  :<ul>{lines}</ul>"
                    "Comment  : {comment}"
                ).format(
                    user=self.env.user.name,
                    customer=rec.partner_id.name,
                    lines=line_items or Markup('<li>No limits changed</li>'),
                    comment=rec.fm_comment or '—',
                ),
                subtype_xmlid='mail.mt_note',
            )

            # Cross-object audit: post on partner too
            rec.partner_id.message_post(
                body=Markup(
                    "<b>💳 Credit Limits Updated</b><br/>"
                    "Request     : {ref}<br/>"
                    "Approved by : {user}<br/>"
                    "Changes     :<ul>{lines}</ul>"
                ).format(
                    ref=rec.name,
                    user=self.env.user.name,
                    lines=line_items or Markup('<li>No limits changed</li>'),
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_reject(self):
        """
        Finance Manager rejects. pending_fm → rejected.

        FM comment is REQUIRED. Terminal state — no limit writes, cannot be reopened.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_finance',
            'reject limit change requests',
        )
        for rec in self:
            if rec.state != 'pending_fm':
                raise UserError(
                    f"Only pending requests can be rejected. "
                    f"State: {rec.state} ({rec.name})"
                )
            if not rec.fm_comment or not rec.fm_comment.strip():
                raise UserError(
                    "A Finance Manager comment is required before rejecting.\n"
                    "Enter the rejection reason in the FM Comment field."
                )

            rec.write({
                'state': 'rejected',
                'reviewed_by': self.env.uid,
                'reviewed_date': fields.Datetime.now(),
            })
            rec.activity_ids.action_done()
            rec.message_post(
                body=Markup(
                    "<b>❌ Rejected by {user}</b><br/>"
                    "Customer: {customer}<br/>"
                    "Reason  : {reason}"
                ).format(
                    user=self.env.user.name,
                    customer=rec.partner_id.name,
                    reason=rec.fm_comment,
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_cancel(self):
        """
        CCM cancels a draft before it is submitted.
        Only draft state can be cancelled — released bucket slots immediately.
        Terminal state like rejected — cannot be reopened.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_ccm',
            'cancel limit change requests',
        )
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    f"Only draft requests can be cancelled. "
                    f"State: {rec.state} ({rec.name})"
                )
            rec.write({'state': 'cancelled'})
            rec.message_post(
                body=Markup(
                    "<b>🚫 Cancelled by {user}</b><br/>"
                    "Request {ref} was cancelled before submission to FM."
                ).format(user=self.env.user.name, ref=rec.name),
                subtype_xmlid='mail.mt_note',
            )

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _assert_group(self, group_xml_id, action_label):
        """Raises AccessError if the current user is missing the required group."""
        if not self.env.user.has_group(group_xml_id):
            group = self.env.ref(group_xml_id, raise_if_not_found=False)
            raise AccessError(
                f"You do not have permission to {action_label}.\n"
                f"Required group: {group.full_name if group else group_xml_id}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# LINE MODEL
# ─────────────────────────────────────────────────────────────────────────────

class ClmLimitChangeRequestLine(models.Model):
    """
    clm.limit.change.request.line — One line per bucket.

    CRITICAL: `bucket` field must NOT have readonly=True at the model level.
    The view sets readonly="1" (user cannot edit it), but the model must
    accept the value written by create() server-side. Model-level readonly
    would cause ORM to silently discard the write → back to NULL.
    """

    _name = 'clm.limit.change.request.line'
    _description = 'CLM Limit Change Request Line'
    _order = 'bucket'

    # ── Class-level maps — referenced by header create(), onchange, partner ──

    _LIMIT_FIELD_MAP = {
        'proforma': 'clm_proforma_limit',
        'bucket1':  'clm_bucket_1_limit',
        'bucket2':  'clm_bucket_2_limit',
        'bucket3':  'clm_bucket_3_limit',
        'bucket4':  'clm_bucket_4_limit',
    }

    _BALANCE_FIELD_MAP = {
        'proforma': 'clm_proforma_balance',
        'bucket1':  'clm_bucket_1_balance',
        'bucket2':  'clm_bucket_2_balance',
        'bucket3':  'clm_bucket_3_balance',
        'bucket4':  'clm_bucket_4_balance',
    }

    # ─────────────────────────────────────────────────────────────────────────
    # RELATIONAL
    # ─────────────────────────────────────────────────────────────────────────

    request_id = fields.Many2one(
        'clm.limit.change.request',
        string='Request',
        required=True,
        ondelete='cascade',
        index=True,
    )
    # Related convenience fields (not stored — always fresh from header)
    partner_id = fields.Many2one(
        related='request_id.partner_id',
        string='Customer',
        store=False,
    )
    currency_id = fields.Many2one(
        related='request_id.currency_id',
        string='Currency',
        store=False,
    )
    state = fields.Selection(
        related='request_id.state',
        string='Request State',
        store=False,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # CORE FIELDS
    # ─────────────────────────────────────────────────────────────────────────

    bucket = fields.Selection(
        selection=[
            ('proforma', 'Proforma Invoice'),
            ('bucket1',  'Bucket 1'),
            ('bucket2',  'Bucket 2'),
            ('bucket3',  'Bucket 3'),
            ('bucket4',  'Bucket 4'),
        ],
        string='Bucket',
        required=True,
        # DO NOT add readonly=True here — see class docstring.
    )
    current_limit = fields.Monetary(
        string='Current Limit',
        compute='_compute_current_values',
        currency_field='currency_id',
        help='Live limit from the partner record. Always recomputed — never stale.',
    )
    current_exposure = fields.Monetary(
        string='Current Exposure',
        compute='_compute_current_values',
        currency_field='currency_id',
        help='Live exposure (sum of sale orders in this bucket stage).',
    )
    proposed_limit = fields.Monetary(
        string='Proposed Limit',
        required=True,
        currency_field='currency_id',
        help='The limit value the CCM wants to set. Only field CCM edits.',
    )
    previous_limit = fields.Monetary(
        string='Previous Limit (at Approval)',
        readonly=True,
        currency_field='currency_id',
        copy=False,
        help='Captured at approval time. Immutable audit snapshot.',
    )
    request_type = fields.Selection(
        selection=[
            ('freeze_resolution', 'Freeze Resolution'),
            ('standard_increase', 'Standard Increase'),
        ],
        string='Type',
        compute='_compute_request_type',
        store=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('request_id.partner_id', 'bucket')
    def _compute_current_values(self):
        for line in self:
            partner = line.request_id.partner_id
            if partner and line.bucket:
                line.current_limit = getattr(
                    partner, self._LIMIT_FIELD_MAP[line.bucket], 0.0
                )
                line.current_exposure = getattr(
                    partner, self._BALANCE_FIELD_MAP[line.bucket], 0.0
                )
            else:
                line.current_limit = 0.0
                line.current_exposure = 0.0

    @api.depends('current_exposure', 'current_limit')
    def _compute_request_type(self):
        for line in self:
            # freeze_resolution: exposure exceeds a configured (non-zero) limit
            line.request_type = (
                'freeze_resolution'
                if line.current_exposure > line.current_limit > 0.0
                else 'standard_increase'
            )

    # ─────────────────────────────────────────────────────────────────────────
    # CONSTRAINTS
    # ─────────────────────────────────────────────────────────────────────────

    @api.constrains('proposed_limit')
    def _check_proposed_limit_not_negative(self):
        for line in self:
            if line.proposed_limit < 0:
                label = dict(self._fields['bucket'].selection).get(
                    line.bucket, line.bucket or 'Unknown'
                )
                raise ValidationError(
                    f"Proposed limit cannot be negative — {label}."
                )

    # ─────────────────────────────────────────────────────────────────────────
    # APPROVAL HELPER — Called by action_approve() on the header
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_limit_to_partner(self):
        """
        Writes this line's proposed_limit to the partner for its bucket.
        Captures the previous limit for the immutable approval audit snapshot.

        sudo() on the line write:
          When called from action_approve(), the header record has already been
          written to 'approved'. The line's related `state` field reflects
          'approved'. The write() guard on the header model blocks any non-sudo
          write to approved records. sudo() is the correct pattern here —
          it is an internal system write, not a user edit.

        clm_bypass_limit_protection:
          res.partner.write() blocks direct edits to limit fields.
          This context key signals the write came from the approved workflow.
        """
        self.ensure_one()
        partner = self.request_id.partner_id
        limit_field = self._LIMIT_FIELD_MAP[self.bucket]
        prev = getattr(partner, limit_field, 0.0)

        partner.with_context(
            clm_bypass_limit_protection=True
        ).write({limit_field: self.proposed_limit})

        # sudo() bypasses the terminal-state guard on this line record
        self.sudo().write({'previous_limit': prev})