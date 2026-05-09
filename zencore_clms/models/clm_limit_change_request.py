# # # # from odoo import models, fields, api
# # # # from odoo.exceptions import UserError, AccessError, ValidationError


# # # # class ClmLimitChangeRequest(models.Model):
# # # #     """
# # # #     Bucket Limit Change Workflow — clm.limit.change.request.

# # # #     State Machine:
# # # #       draft → pending_fm → approved / rejected

# # # #     SRS §9 Compliance:
# # # #     ───────────────────
# # # #     - Only CCM can create and submit (draft → pending_fm)
# # # #     - Only Finance Manager can approve or reject
# # # #     - Approved: limit updated immediately on res.partner
# # # #     - Rejected: permanently closed, cannot be reused or resubmitted
# # # #     - Full audit trail: initiator, approver, timestamps, old/new values

# # # #     FIXES from v0.2.0:
# # # #     ───────────────────
# # # #     - action_reject: Fixed syntax error (raise UserError(...) with Ellipsis)
# # # #     - action_reject: Added message_post for audit trail
# # # #     - write() guard: Rejected records cannot be modified
# # # #     - action_approve: Posts activity completion notification
# # # #     - Unique pending constraint: Improved duplicate detection
# # # #     - FM activity: Created on submit to notify Finance Manager
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
# # # #             ('bucket1',  'Bucket 1'),
# # # #             ('bucket2',  'Bucket 2'),
# # # #             ('bucket3',  'Bucket 3'),
# # # #             ('bucket4',  'Bucket 4'),
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
# # # #     # AUTO-CLASSIFICATION (SRS §9.2)
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
# # # #             ('draft',      'Draft'),
# # # #             ('pending_fm', 'Pending FM Approval'),
# # # #             ('approved',   'Approved'),
# # # #             ('rejected',   'Rejected'),
# # # #         ],
# # # #         string='Status',
# # # #         default='draft',
# # # #         readonly=True,
# # # #         tracking=True,
# # # #     )

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # AUDIT TRAIL (SRS §9.4) — All set by system, never by users
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
# # # #         string='Previous Limit (at Decision)',
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
# # # #     # FIELD MAPPINGS — Bucket key → partner field names
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     _LIMIT_FIELD_MAP = {
# # # #         'proforma': 'clm_proforma_limit',
# # # #         'bucket1':  'clm_bucket_1_limit',
# # # #         'bucket2':  'clm_bucket_2_limit',
# # # #         'bucket3':  'clm_bucket_3_limit',
# # # #         'bucket4':  'clm_bucket_4_limit',
# # # #     }

# # # #     _BALANCE_FIELD_MAP = {
# # # #         'proforma': 'clm_proforma_balance',
# # # #         'bucket1':  'clm_bucket_1_balance',
# # # #         'bucket2':  'clm_bucket_2_balance',
# # # #         'bucket3':  'clm_bucket_3_balance',
# # # #         'bucket4':  'clm_bucket_4_balance',
# # # #     }

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # COMPUTE METHODS
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     @api.depends('partner_id', 'bucket')
# # # #     def _compute_current_values(self):
# # # #         for rec in self:
# # # #             if rec.partner_id and rec.bucket:
# # # #                 rec.current_limit    = getattr(rec.partner_id, self._LIMIT_FIELD_MAP[rec.bucket], 0.0)
# # # #                 rec.current_exposure = getattr(rec.partner_id, self._BALANCE_FIELD_MAP[rec.bucket], 0.0)
# # # #             else:
# # # #                 rec.current_limit    = 0.0
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
# # # #         """
# # # #         Prevent duplicate pending requests for the same partner+bucket.
# # # #         Note: This constraint is best-effort. For true atomicity, a
# # # #         PostgreSQL unique partial index would be required.
# # # #         """
# # # #         for rec in self:
# # # #             if rec.state == 'pending_fm':
# # # #                 duplicate = self.search([
# # # #                     ('partner_id', '=', rec.partner_id.id),
# # # #                     ('bucket',     '=', rec.bucket),
# # # #                     ('state',      '=', 'pending_fm'),
# # # #                     ('id',         '!=', rec.id),
# # # #                 ], limit=1)
# # # #                 if duplicate:
# # # #                     raise ValidationError(
# # # #                         f"A pending request ({duplicate.name}) already exists "
# # # #                         f"for {rec.partner_id.name} — {dict(self._fields['bucket'].selection).get(rec.bucket)}.\n"
# # # #                         f"Resolve the existing request before creating a new one."
# # # #                     )

# # # #     @api.constrains('proposed_limit')
# # # #     def _check_proposed_limit_positive(self):
# # # #         for rec in self:
# # # #             if rec.proposed_limit <= 0:
# # # #                 raise ValidationError("Proposed limit must be greater than zero.")

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # WRITE PROTECTION — Prevent modification of terminal states
# # # #     # SRS §9.3: Rejected requests cannot be reused.
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     def write(self, vals):
# # # #         """
# # # #         Block any modification to records in terminal states (approved/rejected).
# # # #         This prevents attempts to reset and reuse rejected requests.
# # # #         """
# # # #         for rec in self:
# # # #             if rec.state in ('approved', 'rejected'):
# # # #                 # Only allow system-level writes (e.g., ORM internal)
# # # #                 if not self.env.su:
# # # #                     raise AccessError(
# # # #                         f"Request {rec.name} is in a terminal state ({rec.state}) "
# # # #                         f"and cannot be modified. Rejected requests cannot be reused."
# # # #                     )
# # # #         return super().write(vals)

# # # #     # ─────────────────────────────────────────────────────────────────────────
# # # #     # ORM OVERRIDES
# # # #     # ─────────────────────────────────────────────────────────────────────────

# # # #     @api.model_create_multi
# # # #     def create(self, vals_list):
# # # #         """
# # # #         SoD: Only CCM can create limit change requests.
# # # #         Sequence number assigned on creation.
# # # #         Initiated_by always set to current user for audit trail.
# # # #         """
# # # #         self._assert_group(
# # # #             'zencore_clms.group_zencore_clm_ccm',
# # # #             'create limit change requests'
# # # #         )
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
# # # #         """
# # # #         CCM submits the request for FM review.
# # # #         Transitions: draft → pending_fm.
# # # #         Creates a mail.activity for the Finance Manager group to ensure
# # # #         FM is notified (SRS §9.4 — audit and traceability).
# # # #         """
# # # #         self._assert_group(
# # # #             'zencore_clms.group_zencore_clm_ccm',
# # # #             'submit limit change requests'
# # # #         )
# # # #         for rec in self:
# # # #             if rec.state != 'draft':
# # # #                 raise UserError(
# # # #                     f"Only Draft requests can be submitted. Current state: {rec.state} ({rec.name})"
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
# # # #             # Create activity to notify Finance Manager
# # # #             # finance_group = self.env.ref('zencore_clms.group_zencore_clm_finance')
# # # #             # finance_users = finance_group.users if finance_group else self.env['res.users']
# # # #             # FIXED — Query res.users directly by group membership

# # # #             finance_group = self.env.ref('zencore_clms.group_zencore_clm_finance', raise_if_not_found=False)
# # # #             finance_users = (
# # # #                 self.env['res.users'].search([
# # # #                     ('groups_id', 'in', [finance_group.id]),
# # # #                     ('share', '=', False),      # exclude portal users
# # # #                     ('active', '=', True),
# # # #                 ])
# # # #                 if finance_group
# # # #                 else self.env['res.users']
# # # #             )

# # # #             if finance_users:
# # # #                 rec.activity_schedule(
# # # #                     'mail.mail_activity_data_todo',
# # # #                     user_id=finance_users[0].id,
# # # #                     note=(
# # # #                         f"Limit Change Request {rec.name} submitted by CCM "
# # # #                         f"({self.env.user.name}) for {rec.partner_id.name} — "
# # # #                         f"{dict(self._fields['bucket'].selection).get(rec.bucket)}. "
# # # #                         f"Proposed limit: {rec.proposed_limit:,.2f}. Please review."
# # # #                     ),
# # # #                 )

# # # #     def action_approve(self):
# # # #         """
# # # #         Finance Manager approves the request.
# # # #         Transitions: pending_fm → approved.
# # # #         Immediately updates the partner limit via bypass context.
# # # #         Freeze is auto-re-evaluated (non-stored compute).
# # # #         SRS §9.2 Stage 2.
# # # #         """
# # # #         self._assert_group(
# # # #             'zencore_clms.group_zencore_clm_finance',
# # # #             'approve limit change requests'
# # # #         )
# # # #         for rec in self:
# # # #             if rec.state != 'pending_fm':
# # # #                 raise UserError(
# # # #                     f"Only Pending requests can be approved. Current state: {rec.state} ({rec.name})"
# # # #                 )

# # # #             limit_field = self._LIMIT_FIELD_MAP[rec.bucket]
# # # #             prev_limit  = getattr(rec.partner_id, limit_field, 0.0)

# # # #             # Write new limit with bypass (res.partner.write() blocks direct edits)
# # # #             rec.partner_id.with_context(
# # # #                 clm_bypass_limit_protection=True
# # # #             ).write({limit_field: rec.proposed_limit})

# # # #             rec.write({
# # # #                 'state':          'approved',
# # # #                 'previous_limit': prev_limit,
# # # #                 'reviewed_by':    self.env.uid,
# # # #                 'reviewed_date':  fields.Datetime.now(),
# # # #             })

# # # #             # Mark any pending activity as done
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
# # # #         Finance Manager rejects the request.
# # # #         Transitions: pending_fm → rejected.
# # # #         Rejected requests are permanently closed (SRS §9.3).
# # # #         FM comment is REQUIRED for rejected requests (governance rule).

# # # #         FIX from v0.2.0: Was `raise UserError(...)` with Python Ellipsis literal —
# # # #         that is a syntax error. Fixed to proper string arguments.
# # # #         """
# # # #         self._assert_group(
# # # #             'zencore_clms.group_zencore_clm_finance',
# # # #             'reject limit change requests'
# # # #         )
# # # #         for rec in self:
# # # #             if rec.state != 'pending_fm':
# # # #                 raise UserError(
# # # #                     f"Only Pending requests can be rejected. Current state: {rec.state} ({rec.name})"
# # # #                 )
# # # #             if not rec.fm_comment or not rec.fm_comment.strip():
# # # #                 raise UserError(
# # # #                     "A Finance Manager comment is required before rejecting.\n"
# # # #                     "Please enter the rejection reason in the FM Comment field."
# # # #                 )

# # # #             rec.write({
# # # #                 'state':         'rejected',
# # # #                 'reviewed_by':   self.env.uid,
# # # #                 'reviewed_date': fields.Datetime.now(),
# # # #             })

# # # #             # Mark any pending activity as done
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
# # # #         """
# # # #         Raises AccessError if current user does not belong to the required group.
# # # #         Provides a clear, user-friendly error with group name.
# # # #         """
# # # #         if not self.env.user.has_group(group_xml_id):
# # # #             group = self.env.ref(group_xml_id)
# # # #             raise AccessError(
# # # #                 f"You do not have permission to {action_label}.\n"
# # # #                 f"Required group: {group.full_name}"
# # # #             )

# # # from odoo import models, fields, api
# # # from odoo.exceptions import UserError, AccessError, ValidationError


# # # class ClmLimitChangeRequest(models.Model):
# # #     """
# # #     Bucket Limit Change Workflow.

# # #     State Machine:
# # #       draft → pending_fm → approved / rejected

# # #     Rules:
# # #       - Only CCM can create and submit requests
# # #       - Only Finance Manager can approve or reject
# # #       - Rejected requests are closed and cannot be reused
# # #       - Limit is updated directly on res.partner upon approval
# # #       - Full audit trail: initiator, approver, timestamps, old/new values
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
# # #     # REQUEST DETAILS
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     partner_id = fields.Many2one(
# # #         'res.partner',
# # #         string='Customer',
# # #         required=True,
# # #         # domain=[('customer_rank', '>', 0)],
# # #         ondelete='restrict',
# # #         tracking=True,
# # #     )
# # #     bucket = fields.Selection(
# # #         selection=[
# # #             ('proforma', 'Proforma Invoice'),
# # #             ('bucket1', 'Bucket 1'),
# # #             ('bucket2', 'Bucket 2'),
# # #             ('bucket3', 'Bucket 3'),
# # #             ('bucket4', 'Bucket 4'),
# # #         ],
# # #         string='Bucket',
# # #         required=True,
# # #         tracking=True,
# # #     )
# # #     currency_id = fields.Many2one(
# # #         'res.currency',
# # #         default=lambda self: self.env.company.currency_id,
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
# # #         tracking=True,
# # #     )
# # #     justification = fields.Text(
# # #         string='Justification',
# # #         required=True,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # AUTO-CLASSIFICATION
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
# # #             ('draft', 'Draft'),
# # #             ('pending_fm', 'Pending FM Approval'),
# # #             ('approved', 'Approved'),
# # #             ('rejected', 'Rejected'),
# # #         ],
# # #         string='Status',
# # #         default='draft',
# # #         readonly=True,
# # #         tracking=True,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # AUDIT TRAIL — All readonly, set by system
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
# # #     previous_limit = fields.Monetary(
# # #         string='Previous Limit (at Approval)',
# # #         readonly=True,
# # #         currency_field='currency_id',
# # #         copy=False,
# # #     )
# # #     fm_comment = fields.Text(
# # #         string='Finance Manager Comment',
# # #         copy=False,
# # #         tracking=True,
# # #     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # FIELD MAPPINGS — Bucket → Partner field names
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     _LIMIT_FIELD_MAP = {
# # #         'proforma': 'clm_proforma_limit',
# # #         'bucket1': 'clm_bucket_1_limit',
# # #         'bucket2': 'clm_bucket_2_limit',
# # #         'bucket3': 'clm_bucket_3_limit',
# # #         'bucket4': 'clm_bucket_4_limit',
# # #     }

# # #     _BALANCE_FIELD_MAP = {
# # #         'proforma': 'clm_proforma_balance',
# # #         'bucket1': 'clm_bucket_1_balance',
# # #         'bucket2': 'clm_bucket_2_balance',
# # #         'bucket3': 'clm_bucket_3_balance',
# # #         'bucket4': 'clm_bucket_4_balance',
# # #     }

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # COMPUTE METHODS
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     @api.depends('partner_id', 'bucket')
# # #     def _compute_current_values(self):
# # #         for rec in self:
# # #             if rec.partner_id and rec.bucket:
# # #                 rec.current_limit = getattr(
# # #                     rec.partner_id, self._LIMIT_FIELD_MAP[rec.bucket], 0.0
# # #                 )
# # #                 rec.current_exposure = getattr(
# # #                     rec.partner_id, self._BALANCE_FIELD_MAP[rec.bucket], 0.0
# # #                 )
# # #             else:
# # #                 rec.current_limit = 0.0
# # #                 rec.current_exposure = 0.0

# # #     @api.depends('current_exposure', 'current_limit')
# # #     def _compute_request_type(self):
# # #         for rec in self:
# # #             rec.request_type = (
# # #                 'freeze_resolution'
# # #                 if rec.current_exposure > rec.current_limit
# # #                 else 'standard_increase'
# # #             )


# # #     #check unique pending request per bucket per partner
# # #     @api.constrains('partner_id', 'bucket', 'state')
# # #     def _check_unique_pending(self):
# # #         for rec in self:
# # #             if rec.state == 'pending_fm':
# # #                 duplicate = self.search([
# # #                     ('partner_id', '=', rec.partner_id.id),
# # #                     ('bucket', '=', rec.bucket),
# # #                     ('state', '=', 'pending_fm'),
# # #                     ('id', '!=', rec.id),
# # #                 ], limit=1)
# # #                 if duplicate:
# # #                     raise ValidationError( 
# # #                         f"A pending request ({duplicate.name}) already exists "
# # #                         f"for {rec.partner_id.name} — {rec.bucket}."
# # #                     )

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # ORM OVERRIDES
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     @api.model_create_multi
# # #     def create(self, vals_list):
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
# # #         """
# # #         CCM submits request for FM review.
# # #         Only CCM group members can call this action.
# # #         """
# # #         self._assert_group('zencore_clms.group_zencore_clm_ccm', 'submit limit change requests')
# # #         for rec in self:
# # #             if rec.state != 'draft':
# # #                 raise UserError(f"Only draft requests can be submitted. ({rec.name})")
# # #             if rec.proposed_limit <= 0:
# # #                 raise UserError("Proposed limit must be greater than zero.")
# # #             rec.write({'state': 'pending_fm'})
# # #             rec.message_post(
# # #                 body=f"Request submitted by {self.env.user.name} for FM review.",
# # #                 subtype_xmlid='mail.mt_note',
# # #             )

# # #     def action_approve(self):
# # #         """
# # #         Finance Manager approves the request.
# # #         Updates the partner limit immediately.
# # #         Freeze status is automatically re-evaluated (non-stored compute).
# # #         """
# # #         self._assert_group('zencore_clms.group_zencore_clm_finance', 'approve limit change requests')
# # #         for rec in self:
# # #             if rec.state != 'pending_fm':
# # #                 raise UserError(f"Only pending requests can be approved. ({rec.name})")

# # #             limit_field = self._LIMIT_FIELD_MAP[rec.bucket]

# # #             # Capture previous value for audit
# # #             prev_limit = getattr(rec.partner_id, limit_field, 0.0)

# # #             # Apply the new limit
# # #             # rec.partner_id.write({limit_field: rec.proposed_limit})

# # #             rec.partner_id.with_context(
# # #                 clm_bypass_limit_protection=True
# # #             ).write({limit_field: rec.proposed_limit})

# # #             rec.write({
# # #                 'state': 'approved',
# # #                 'previous_limit': prev_limit,
# # #                 'reviewed_by': self.env.uid,
# # #                 'reviewed_date': fields.Datetime.now(),
# # #             })
# # #             rec.message_post(
# # #                 body=(
# # #                     f"✅ Approved by {self.env.user.name}.\n"
# # #                     f"Bucket: {dict(rec._fields['bucket'].selection).get(rec.bucket)}\n"
# # #                     f"Previous Limit: {prev_limit:,.2f} → New Limit: {rec.proposed_limit:,.2f}"
# # #                 ),
# # #                 subtype_xmlid='mail.mt_note',
# # #             )

# # #     # def action_reject(self):
# # #     #     """
# # #     #     Finance Manager rejects the request.
# # #     #     Rejected requests are permanently closed — cannot be reused.
# # #     #     """
# # #     #     self._assert_group('zencore_clms.group_zencore_clm_finance', 'reject limit change requests')
# # #     #     for rec in self:
# # #     #         if rec.state != 'pending_fm':
# # #     #             raise UserError(f"Only pending requests can be rejected. ({rec.name})")
# # #     #         rec.write({
# # #     #             'state': 'rejected',
# # #     #             'reviewed_by': self.env.uid,
# # #     #             'reviewed_date': fields.Datetime.now(),
# # #     #         })
# # #     #         rec.message_post(
# # #     #             body=f"❌ Rejected by {self.env.user.name}. Comment: {rec.fm_comment or 'None'}",
# # #     #             subtype_xmlid='mail.mt_note',
# # #     #         )

# # #     def action_reject(self):
# # #         self._assert_group('zencore_clms.group_zencore_clm_finance', 'reject')
# # #         for rec in self:
# # #             if rec.state != 'pending_fm':
# # #                 raise UserError(...)
# # #             if not rec.fm_comment or not rec.fm_comment.strip():
# # #                 raise UserError(
# # #                     "Rejection requires a Finance Manager comment.\n"
# # #                     "Please explain the reason for rejection in the FM Comment field."
# # #                 )
# # #             rec.write({
# # #                 'state': 'rejected',
# # #                 'reviewed_by': self.env.uid,
# # #                 'reviewed_date': fields.Datetime.now(),
# # #             })

# # #     # ─────────────────────────────────────────────────────────────────────────
# # #     # PRIVATE HELPERS
# # #     # ─────────────────────────────────────────────────────────────────────────

# # #     def _assert_group(self, group_xml_id, action_label):
# # #         """Raises AccessError if current user does not belong to the required group."""
# # #         if not self.env.user.has_group(group_xml_id):
# # #             group = self.env.ref(group_xml_id)
# # #             raise AccessError(
# # #                 f"You do not have permission to {action_label}.\n"
# # #                 f"Required group: {group.full_name}"
# # #             )


# # from odoo import models, fields, api
# # from odoo.exceptions import UserError, AccessError, ValidationError


# # class ClmLimitChangeRequest(models.Model):
# #     """
# #     Individual Bucket Limit Change Workflow.

# #     State Machine:
# #       draft → pending_fm → approved / rejected

# #     Rules:
# #       - Only CCM can create and submit requests
# #       - Only Finance Manager can approve or reject
# #       - Rejected requests are permanently closed and cannot be reused
# #       - Limit is updated directly on res.partner upon approval
# #       - Full audit trail: initiator, approver, timestamps, old/new values

# #     See clm.bulk.limit.change.request for multi-bucket batch requests.
# #     """

# #     _name = 'clm.limit.change.request'
# #     _description = 'CLM Bucket Limit Change Request'
# #     _inherit = ['mail.thread', 'mail.activity.mixin']
# #     _order = 'create_date desc'
# #     _rec_name = 'name'

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # IDENTIFICATION
# #     # ─────────────────────────────────────────────────────────────────────────

# #     name = fields.Char(
# #         string='Reference',
# #         readonly=True,
# #         default='New',
# #         copy=False,
# #     )

# #     #add line
# #     line_ids = fields.One2many(
# #         'clm.limit.change.request.line',
# #         'request_id',
# #         string='Limit Change Lines',
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # REQUEST DETAILS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     partner_id = fields.Many2one(
# #         'res.partner',
# #         string='Customer',
# #         required=True,
# #         ondelete='restrict',
# #         tracking=True,
# #     )
# #     bucket = fields.Selection(
# #         selection=[
# #             ('proforma', 'Proforma Invoice'),
# #             ('bucket1', 'Bucket 1'),
# #             ('bucket2', 'Bucket 2'),
# #             ('bucket3', 'Bucket 3'),
# #             ('bucket4', 'Bucket 4'),
# #         ],
# #         string='Bucket',
# #         required=True,
# #         tracking=True,
# #     )
# #     currency_id = fields.Many2one(
# #         'res.currency',
# #         default=lambda self: self.env.company.currency_id,
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
# #         tracking=True,
# #     )
# #     justification = fields.Text(
# #         string='Justification',
# #         required=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # AUTO-CLASSIFICATION
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
# #             ('draft', 'Draft'),
# #             ('pending_fm', 'Pending FM Approval'),
# #             ('approved', 'Approved'),
# #             ('rejected', 'Rejected'),
# #         ],
# #         string='Status',
# #         default='draft',
# #         readonly=True,
# #         tracking=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # AUDIT TRAIL — All readonly, set by system
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
# #     previous_limit = fields.Monetary(
# #         string='Previous Limit (at Approval)',
# #         readonly=True,
# #         currency_field='currency_id',
# #         copy=False,
# #     )
# #     fm_comment = fields.Text(
# #         string='Finance Manager Comment',
# #         copy=False,
# #         tracking=True,
# #     )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # FIELD MAPPINGS — Bucket → Partner field names
# #     # ─────────────────────────────────────────────────────────────────────────

# #     _LIMIT_FIELD_MAP = {
# #         'proforma': 'clm_proforma_limit',
# #         'bucket1': 'clm_bucket_1_limit',
# #         'bucket2': 'clm_bucket_2_limit',
# #         'bucket3': 'clm_bucket_3_limit',
# #         'bucket4': 'clm_bucket_4_limit',
# #     }

# #     _BALANCE_FIELD_MAP = {
# #         'proforma': 'clm_proforma_balance',
# #         'bucket1': 'clm_bucket_1_balance',
# #         'bucket2': 'clm_bucket_2_balance',
# #         'bucket3': 'clm_bucket_3_balance',
# #         'bucket4': 'clm_bucket_4_balance',
# #     }

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # COMPUTE METHODS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.depends('partner_id', 'bucket')
# #     def _compute_current_values(self):
# #         for rec in self:
# #             if rec.partner_id and rec.bucket:
# #                 rec.current_limit = getattr(
# #                     rec.partner_id, self._LIMIT_FIELD_MAP[rec.bucket], 0.0
# #                 )
# #                 rec.current_exposure = getattr(
# #                     rec.partner_id, self._BALANCE_FIELD_MAP[rec.bucket], 0.0
# #                 )
# #             else:
# #                 rec.current_limit = 0.0
# #                 rec.current_exposure = 0.0

# #     @api.depends('current_exposure', 'current_limit')
# #     def _compute_request_type(self):
# #         for rec in self:
# #             rec.request_type = (
# #                 'freeze_resolution'
# #                 if rec.current_exposure > rec.current_limit
# #                 else 'standard_increase'
# #             )

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # CONSTRAINTS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.constrains('partner_id', 'bucket', 'state')
# #     def _check_unique_pending(self):
# #         for rec in self:
# #             if rec.state == 'pending_fm':
# #                 duplicate = self.search([
# #                     ('partner_id', '=', rec.partner_id.id),
# #                     ('bucket', '=', rec.bucket),
# #                     ('state', '=', 'pending_fm'),
# #                     ('id', '!=', rec.id),
# #                 ], limit=1)
# #                 if duplicate:
# #                     raise ValidationError(
# #                         f"A pending request ({duplicate.name}) already exists "
# #                         f"for {rec.partner_id.name} — "
# #                         f"{dict(self._fields['bucket'].selection).get(rec.bucket)}.\n"
# #                         f"Resolve the existing request before submitting a new one."
# #                     )

# #     @api.constrains('proposed_limit')
# #     def _check_proposed_limit_positive(self):
# #         for rec in self:
# #             if rec.proposed_limit <= 0:
# #                 raise ValidationError("Proposed limit must be greater than zero.")

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # ORM OVERRIDES
# #     # ─────────────────────────────────────────────────────────────────────────

# #     @api.model_create_multi
# #     def create(self, vals_list):
# #         for vals in vals_list:
# #             if vals.get('name', 'New') == 'New':
# #                 vals['name'] = (
# #                     self.env['ir.sequence'].next_by_code('clm.limit.change.request')
# #                     or 'New'
# #                 )
# #             vals['initiated_by'] = self.env.uid
# #         return super().create(vals_list)

# #     # ─────────────────────────────────────────────────────────────────────────
# #     # WORKFLOW ACTIONS
# #     # ─────────────────────────────────────────────────────────────────────────

# #     def action_submit_to_fm(self):
# #         """CCM submits request for FM review. draft → pending_fm."""
# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_ccm',
# #             'submit limit change requests',
# #         )
# #         for rec in self:
# #             if rec.state != 'draft':
# #                 raise UserError(
# #                     f"Only draft requests can be submitted. Current state: {rec.state} ({rec.name})"
# #                 )
# #             rec.write({'state': 'pending_fm'})
# #             rec.message_post(
# #                 body=(
# #                     f"<b>Submitted for FM Approval</b><br/>"
# #                     f"Submitted by: {self.env.user.name}<br/>"
# #                     f"Bucket: {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
# #                     f"Proposed Limit: {rec.proposed_limit:,.2f}<br/>"
# #                     f"Request Type: {dict(self._fields['request_type'].selection).get(rec.request_type)}"
# #                 ),
# #                 subtype_xmlid='mail.mt_note',
# #             )
# #             # Notify Finance Manager
# #             finance_group = self.env.ref(
# #                 'zencore_clms.group_zencore_clm_finance', raise_if_not_found=False
# #             )
# #             if finance_group:
# #                 finance_users = self.env['res.users'].search([
# #                     ('groups_id', 'in', [finance_group.id]),
# #                     ('share', '=', False),
# #                     ('active', '=', True),
# #                 ], limit=1)
# #                 if finance_users:
# #                     rec.activity_schedule(
# #                         'mail.mail_activity_data_todo',
# #                         user_id=finance_users[0].id,
# #                         note=(
# #                             f"Limit Change Request {rec.name} submitted by "
# #                             f"{self.env.user.name} for {rec.partner_id.name} — "
# #                             f"{dict(self._fields['bucket'].selection).get(rec.bucket)}. "
# #                             f"Proposed limit: {rec.proposed_limit:,.2f}. Please review."
# #                         ),
# #                     )

# #     def action_approve(self):
# #         """Finance Manager approves. pending_fm → approved. Updates partner limit."""
# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_finance',
# #             'approve limit change requests',
# #         )
# #         for rec in self:
# #             if rec.state != 'pending_fm':
# #                 raise UserError(
# #                     f"Only pending requests can be approved. Current state: {rec.state} ({rec.name})"
# #                 )

# #             limit_field = self._LIMIT_FIELD_MAP[rec.bucket]
# #             prev_limit = getattr(rec.partner_id, limit_field, 0.0)

# #             rec.partner_id.with_context(
# #                 clm_bypass_limit_protection=True
# #             ).write({limit_field: rec.proposed_limit})

# #             rec.write({
# #                 'state': 'approved',
# #                 'previous_limit': prev_limit,
# #                 'reviewed_by': self.env.uid,
# #                 'reviewed_date': fields.Datetime.now(),
# #             })
# #             rec.activity_ids.action_done()
# #             rec.message_post(
# #                 body=(
# #                     f"<b>✅ Approved by {self.env.user.name}</b><br/>"
# #                     f"Customer : {rec.partner_id.name}<br/>"
# #                     f"Bucket   : {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
# #                     f"Previous : {prev_limit:,.2f}<br/>"
# #                     f"New Limit: {rec.proposed_limit:,.2f}<br/>"
# #                     f"Comment  : {rec.fm_comment or '—'}"
# #                 ),
# #                 subtype_xmlid='mail.mt_note',
# #             )

# #     def action_reject(self):
# #         """
# #         Finance Manager rejects. pending_fm → rejected.
# #         FM comment is required. Rejected records are permanently closed.

# #         FIX: Previous version had `raise UserError(...)` with Python's Ellipsis
# #         literal (...) instead of a string argument — a silent syntax/runtime bug
# #         that would raise TypeError, not UserError, breaking the entire action.
# #         """
# #         self._assert_group(
# #             'zencore_clms.group_zencore_clm_finance',
# #             'reject limit change requests',
# #         )
# #         for rec in self:
# #             if rec.state != 'pending_fm':
# #                 raise UserError(
# #                     f"Only pending requests can be rejected. Current state: {rec.state} ({rec.name})"
# #                 )
# #             if not rec.fm_comment or not rec.fm_comment.strip():
# #                 raise UserError(
# #                     "A Finance Manager comment is required before rejecting.\n"
# #                     "Enter the rejection reason in the FM Comment field."
# #                 )
# #             rec.write({
# #                 'state': 'rejected',
# #                 'reviewed_by': self.env.uid,
# #                 'reviewed_date': fields.Datetime.now(),
# #             })
# #             rec.activity_ids.action_done()
# #             rec.message_post(
# #                 body=(
# #                     f"<b>❌ Rejected by {self.env.user.name}</b><br/>"
# #                     f"Customer: {rec.partner_id.name}<br/>"
# #                     f"Bucket  : {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
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

# # class ClmLimitChangeRequestLine(models.Model):
# #     _name = 'clm.limit.change.request.line'
# #     _description = 'Limit Change Request Line'

# #     request_id = fields.Many2one(
# #         'clm.limit.change.request',
# #         string='Limit Change Request',
# #         ondelete='cascade',
# #     )

# #     bucket = fields.Selection(
# #         related='request_id.bucket',
# #         string='Bucket',
# #         store=True,
# #         readonly=True,
# #     )

# from odoo import models, fields, api
# from odoo.exceptions import UserError, AccessError, ValidationError


# class ClmLimitChangeRequest(models.Model):
#     """
#     Multi-Bucket Limit Change Workflow — clm.limit.change.request

#     State Machine:
#       draft → pending_fm → approved / rejected

#     Design (v0.4.0 refactor):
#     ──────────────────────────
#     - Header: partner, justification, workflow state, audit trail
#     - Lines:  one line per bucket — each has its own limit/exposure/proposed
#     - Approval: iterates line_ids and writes each bucket's limit on the partner
#     - request_type on header: 'freeze_resolution' if ANY line is a freeze resolution

#     SRS §9 Compliance:
#     ───────────────────
#     - Only CCM can create and submit (draft → pending_fm)
#     - Only Finance Manager can approve or reject
#     - Rejected requests are permanently closed
#     - Full audit trail: initiator, approver, timestamps
#     """

#     _name = 'clm.limit.change.request'
#     _description = 'CLM Bucket Limit Change Request'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _order = 'create_date desc'
#     _rec_name = 'name'

#     # ─────────────────────────────────────────────────────────────────────────
#     # IDENTIFICATION
#     # ─────────────────────────────────────────────────────────────────────────

#     name = fields.Char(
#         string='Reference',
#         readonly=True,
#         default='New',
#         copy=False,
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # HEADER FIELDS
#     # ─────────────────────────────────────────────────────────────────────────

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

#     # ─────────────────────────────────────────────────────────────────────────
#     # LINES — One line per bucket
#     # ─────────────────────────────────────────────────────────────────────────

#     line_ids = fields.One2many(
#         'clm.limit.change.request.line',
#         'request_id',
#         string='Limit Change Lines',
#         copy=True,
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # AUTO-CLASSIFICATION — Computed from lines
#     # 'freeze_resolution' if ANY line has exposure > limit
#     # ─────────────────────────────────────────────────────────────────────────

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

#     # ─────────────────────────────────────────────────────────────────────────
#     # WORKFLOW STATE
#     # ─────────────────────────────────────────────────────────────────────────

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
#     # AUDIT TRAIL — All set by system, never by users
#     # ─────────────────────────────────────────────────────────────────────────

#     initiated_by = fields.Many2one(
#         'res.users',
#         string='Initiated By',
#         readonly=True,
#         copy=False,
#     )
#     reviewed_by = fields.Many2one(
#         'res.users',
#         string='Approved / Rejected By',
#         readonly=True,
#         copy=False,
#         tracking=True,
#     )
#     reviewed_date = fields.Datetime(
#         string='Reviewed On',
#         readonly=True,
#         copy=False,
#     )
#     fm_comment = fields.Text(
#         string='Finance Manager Comment',
#         copy=False,
#         tracking=True,
#     )

#     # ─────────────────────────────────────────────────────────────────────────────
#     # ALL BUCKET KEYS IN ORDER
#     # ─────────────────────────────────────────────────────────────────────────────

#     _BUCKET_KEYS = ['proforma', 'bucket1', 'bucket2', 'bucket3', 'bucket4']


#     @api.onchange('partner_id')
#     def _onchange_partner_id_populate_lines(self):
#         """
#         Auto-populate all 5 bucket lines when partner is selected or changed.
#         Clears existing lines first to avoid duplicates.
#         Lines are pre-filled with current limit + exposure from the partner.
#         CCM only needs to fill 'proposed_limit' for the buckets they want to change.

#         Odoo 19 pattern:
#         - Use Command.clear() to wipe existing lines
#         - Use Command.create({...}) to create new lines in the same onchange
#         - proposed_limit defaults to current_limit (no change intent)
#         so CCM only edits buckets they care about
#         """
#         if not self.partner_id:
#             self.line_ids = fields.Command.clear()
#             return

#         partner = self.partner_id
#         new_lines = []

#         for bucket in self._BUCKET_KEYS:
#             limit_field   = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
#             balance_field = ClmLimitChangeRequestLine._BALANCE_FIELD_MAP[bucket]

#             current_limit    = getattr(partner, limit_field,   0.0)
#             current_exposure = getattr(partner, balance_field, 0.0)

#             new_lines.append(fields.Command.create({
#                 'bucket':         bucket,
#                 'proposed_limit': current_limit,  # defaults to no change; CCM edits as needed
#             }))

#         self.line_ids = fields.Command.clear()
#         self.line_ids = new_lines

#     # ─────────────────────────────────────────────────────────────────────────
#     # COMPUTE
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.depends('line_ids.request_type')
#     def _compute_request_type(self):
#         for rec in self:
#             if any(line.request_type == 'freeze_resolution' for line in rec.line_ids):
#                 rec.request_type = 'freeze_resolution'
#             else:
#                 rec.request_type = 'standard_increase'

#     # ─────────────────────────────────────────────────────────────────────────
#     # CONSTRAINTS
#     # ─────────────────────────────────────────────────────────────────────────

#     # @api.constrains('line_ids')
#     # def _check_lines_not_empty(self):
#     #     for rec in self:
#     #         if rec.state == 'draft' and not rec.line_ids:
#     #             raise ValidationError(
#     #                 "At least one bucket line is required before submitting."
#     #             )

#     @api.constrains('partner_id', 'line_ids')
#     def _check_lines_not_empty(self):
#         for rec in self:
#             if rec.state != 'draft':
#                 continue
#             if rec.partner_id and not rec.line_ids:
#                 raise ValidationError(
#                     f"Request {rec.name} has no bucket lines.\n"
#                     f"Select the customer again to auto-populate all buckets."
#                 )

#     @api.constrains('line_ids', 'partner_id')
#     def _check_duplicate_buckets_in_lines(self):
#         """Prevent the same bucket appearing twice on the same request."""
#         for rec in self:
#             buckets = rec.line_ids.mapped('bucket')
#             if len(buckets) != len(set(buckets)):
#                 raise ValidationError(
#                     "Each bucket may only appear once per request.\n"
#                     "Remove duplicate bucket lines."
#                 )

#     @api.constrains('partner_id', 'state')
#     def _check_unique_pending(self):
#         """Prevent two pending requests for the same partner."""
#         for rec in self:
#             if rec.state == 'pending_fm':
#                 duplicate = self.search([
#                     ('partner_id', '=', rec.partner_id.id),
#                     ('state',      '=', 'pending_fm'),
#                     ('id',         '!=', rec.id),
#                 ], limit=1)
#                 if duplicate:
#                     raise ValidationError(
#                         f"A pending request ({duplicate.name}) already exists "
#                         f"for {rec.partner_id.name}.\n"
#                         f"Resolve the existing request before creating a new one."
#                     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # WRITE PROTECTION — Terminal state guard
#     # ─────────────────────────────────────────────────────────────────────────

#     def write(self, vals):
#         for rec in self:
#             if rec.state in ('approved', 'rejected') and not self.env.su:
#                 raise AccessError(
#                     f"Request {rec.name} is in a terminal state ({rec.state}) "
#                     f"and cannot be modified."
#                 )
#         return super().write(vals)

#     # ─────────────────────────────────────────────────────────────────────────
#     # ORM OVERRIDES
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.model_create_multi
#     def create(self, vals_list):
#         self._assert_group(
#             'zencore_clms.group_zencore_clm_ccm',
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
#     # WORKFLOW ACTIONS
#     # ─────────────────────────────────────────────────────────────────────────

#     def action_submit_to_fm(self):
#         """CCM submits request for FM review. draft → pending_fm."""
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
#                     f"Cannot submit {rec.name} — no bucket lines added.\n"
#                     f"Add at least one bucket line before submitting."
#                 )

#             rec.write({'state': 'pending_fm'})

#             # Build line summary for chatter
#             line_summary = ''.join(
#                 f"<li>{dict(self.env['clm.limit.change.request.line']._fields['bucket'].selection).get(l.bucket)}: "
#                 f"{l.current_limit:,.2f} → {l.proposed_limit:,.2f}</li>"
#                 for l in rec.line_ids
#             )
#             rec.message_post(
#                 body=(
#                     f"<b>Submitted for FM Approval</b><br/>"
#                     f"Submitted by : {self.env.user.name}<br/>"
#                     f"Customer     : {rec.partner_id.name}<br/>"
#                     f"Request Type : {dict(self._fields['request_type'].selection).get(rec.request_type)}<br/>"
#                     f"Buckets      : <ul>{line_summary}</ul>"
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#             # FIX: Odoo 19 — group_ids (not groups_id)
#             finance_group = self.env.ref(
#                 'zencore_clms.group_zencore_clm_finance',
#                 raise_if_not_found=False,
#             )
#             if finance_group:
#                 finance_users = self.env['res.users'].search([
#                     ('group_ids', 'in', [finance_group.id]),  # Odoo 19: group_ids
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
#                             f"Please review."
#                         ),
#                     )

#     def action_approve(self):
#         """
#         Finance Manager approves. pending_fm → approved.
#         Iterates ALL lines and writes each bucket's limit on the partner.
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

#             # Apply each line's proposed limit to the partner
#             for line in rec.line_ids:
#                 line._apply_limit_to_partner()

#             rec.write({
#                 'state':         'approved',
#                 'reviewed_by':   self.env.uid,
#                 'reviewed_date': fields.Datetime.now(),
#             })
#             rec.activity_ids.action_done()

#             # Build approval summary
#             line_summary = ''.join(
#                 f"<li>{dict(self.env['clm.limit.change.request.line']._fields['bucket'].selection).get(l.bucket)}: "
#                 f"{l.previous_limit:,.2f} → {l.proposed_limit:,.2f}</li>"
#                 for l in rec.line_ids
#             )
#             rec.message_post(
#                 body=(
#                     f"<b>✅ Approved by {self.env.user.name}</b><br/>"
#                     f"Customer : {rec.partner_id.name}<br/>"
#                     f"Changes  : <ul>{line_summary}</ul>"
#                     f"Comment  : {rec.fm_comment or '—'}"
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#     def action_reject(self):
#         """
#         Finance Manager rejects. pending_fm → rejected.
#         FM comment is required. Terminal state — cannot be reused.
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
#                 body=(
#                     f"<b>❌ Rejected by {self.env.user.name}</b><br/>"
#                     f"Customer: {rec.partner_id.name}<br/>"
#                     f"Reason  : {rec.fm_comment}"
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
#     One line = one bucket on a limit change request.

#     Each line holds:
#       - bucket             : which bucket this line targets
#       - current_limit      : live value from partner (computed, non-stored)
#       - current_exposure   : live balance from partner (computed, non-stored)
#       - proposed_limit     : new limit requested by CCM
#       - previous_limit     : captured at approval time for audit trail
#       - request_type       : freeze_resolution / standard_increase (computed)
#     """

#     _name = 'clm.limit.change.request.line'
#     _description = 'CLM Limit Change Request Line'
#     _order = 'bucket'

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
#     # Convenience access to header fields
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
#     # FIELD MAPS — Bucket key → partner field names
#     # ─────────────────────────────────────────────────────────────────────────

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
#     # COMPUTE
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.depends('request_id.partner_id', 'bucket')
#     def _compute_current_values(self):
#         for line in self:
#             partner = line.request_id.partner_id
#             if partner and line.bucket:
#                 line.current_limit    = getattr(partner, self._LIMIT_FIELD_MAP[line.bucket], 0.0)
#                 line.current_exposure = getattr(partner, self._BALANCE_FIELD_MAP[line.bucket], 0.0)
#             else:
#                 line.current_limit    = 0.0
#                 line.current_exposure = 0.0

#     @api.depends('current_exposure', 'current_limit')
#     def _compute_request_type(self):
#         for line in self:
#             line.request_type = (
#                 'freeze_resolution'
#                 if line.current_exposure > line.current_limit
#                 else 'standard_increase'
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # CONSTRAINTS
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.constrains('proposed_limit')
#     def _check_proposed_limit_positive(self):
#         for line in self:
#             if line.proposed_limit <= 0:
#                 raise ValidationError(
#                     f"Proposed limit must be greater than zero "
#                     f"({dict(self._fields['bucket'].selection).get(line.bucket)})."
#                 )

#     # ─────────────────────────────────────────────────────────────────────────
#     # APPROVAL HELPER — Called by action_approve on the header
#     # ─────────────────────────────────────────────────────────────────────────

#     def _apply_limit_to_partner(self):
#         """
#         Writes this line's proposed_limit onto the partner.
#         Captures previous_limit for audit trail.
#         Uses bypass context to pass write() protection on res.partner.
#         """
#         self.ensure_one()
#         partner = self.request_id.partner_id
#         limit_field = self._LIMIT_FIELD_MAP[self.bucket]
#         prev = getattr(partner, limit_field, 0.0)

#         partner.with_context(
#             clm_bypass_limit_protection=True
#         ).write({limit_field: self.proposed_limit})

#         # Store previous value on the line for audit trail
#         self.with_context(
#             clm_bypass_line_write=True
#         ).write({'previous_limit': prev})

from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError, ValidationError
from markupsafe import Markup

class ClmLimitChangeRequest(models.Model):
    """
    Multi-Bucket Limit Change Workflow — clm.limit.change.request

    State Machine:
      draft → pending_fm → approved / rejected

    Design (v0.5.0):
    ──────────────────
    - Header  : partner, justification, workflow state, audit trail
    - Lines   : auto-populated on partner select (all 5 buckets)
                CCM edits only the proposed_limit cells they want to change
    - Approval: iterates ALL line_ids and writes each bucket's limit on partner
    - request_type on header: freeze_resolution if ANY line is a freeze case

    SRS §9 Compliance:
    ───────────────────
    - Only CCM can create and submit (draft → pending_fm)
    - Only Finance Manager can approve or reject
    - Rejected requests are permanently closed — cannot be reused
    - Full audit trail: initiator, approver, timestamps, per-line previous limits

    Odoo 19 notes:
    ───────────────
    - group_ids (not groups_id) for res.users domain queries
    - fields.Command.create / fields.Command.clear for onchange O2M writes
    - flush_all() not needed here (no payment reconciliation)
    """

    _name = 'clm.limit.change.request'
    _description = 'CLM Bucket Limit Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # ─────────────────────────────────────────────────────────────────────────
    # BUCKET KEYS — canonical order, used by onchange + line model
    # ─────────────────────────────────────────────────────────────────────────

    _BUCKET_KEYS = ['proforma', 'bucket1', 'bucket2', 'bucket3', 'bucket4']

    # ─────────────────────────────────────────────────────────────────────────
    # IDENTIFICATION
    # ─────────────────────────────────────────────────────────────────────────

    name = fields.Char(
        string='Reference',
        readonly=True,
        default='New',
        copy=False,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # HEADER FIELDS
    # ─────────────────────────────────────────────────────────────────────────

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    justification = fields.Text(
        string='Justification',
        required=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # LINES — Auto-populated on partner select. One line per bucket.
    # ─────────────────────────────────────────────────────────────────────────

    line_ids = fields.One2many(
        'clm.limit.change.request.line',
        'request_id',
        string='Bucket Limit Lines',
        copy=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # AUTO-CLASSIFICATION — Computed from lines
    # freeze_resolution if ANY line has exposure > current limit
    # ─────────────────────────────────────────────────────────────────────────

    request_type = fields.Selection(
        selection=[
            ('freeze_resolution', 'Freeze Resolution'),
            ('standard_increase', 'Standard Increase'),
        ],
        string='Request Type',
        compute='_compute_request_type',
        store=True,
        tracking=True,
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
        ],
        string='Status',
        default='draft',
        readonly=True,
        tracking=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # AUDIT TRAIL — All set by system, never by users
    # ─────────────────────────────────────────────────────────────────────────

    initiated_by = fields.Many2one(
        'res.users',
        string='Initiated By',
        readonly=True,
        copy=False,
    )
    reviewed_by = fields.Many2one(
        'res.users',
        string='Approved / Rejected By',
        readonly=True,
        copy=False,
        tracking=True,
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
    )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('line_ids.request_type')
    def _compute_request_type(self):
        for rec in self:
            if any(line.request_type == 'freeze_resolution' for line in rec.line_ids):
                rec.request_type = 'freeze_resolution'
            else:
                rec.request_type = 'standard_increase'

    # ─────────────────────────────────────────────────────────────────────────
    # ONCHANGE — Auto-populate all 5 bucket lines on partner select
    # ─────────────────────────────────────────────────────────────────────────

    @api.onchange('partner_id')
    def _onchange_partner_id_populate_lines(self):
        """
        Fires in the UI when CCM selects or changes the partner.

        Behaviour:
        - Clears any existing lines (prevents stale data from previous partner)
        - Creates 5 new lines (one per bucket) with live values from the partner
        - proposed_limit defaults to current_limit so there is no accidental change
        - CCM only needs to edit the proposed_limit cells for buckets they intend to change

        Odoo 19 pattern:
        - fields.Command.clear()  → wipes existing O2M lines
        - fields.Command.create() → creates new virtual lines (not yet in DB)
        - Both work correctly in onchange context without needing a saved record
        """
        # Always clear first — even if partner is removed
        self.line_ids = [fields.Command.clear()]

        if not self.partner_id:
            return

        partner = self.partner_id
        new_lines = []

        for bucket in self._BUCKET_KEYS:
            limit_field   = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
            current_limit = getattr(partner, limit_field, 0.0)

            new_lines.append(fields.Command.create({
                'bucket':         bucket,
                # Default proposed = current so CCM edits only intended buckets
                'proposed_limit': current_limit,
            }))

        self.line_ids = new_lines

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL HELPER — Shared by onchange (UI) and create() (programmatic)
    # ─────────────────────────────────────────────────────────────────────────

    def _populate_bucket_lines(self):
        """
        Writes all 5 bucket lines directly to the DB.
        Called from create() when the record already has an ID.
        Not used by onchange (which uses Command.create on virtual records).
        """
        self.ensure_one()
        if not self.partner_id:
            return

        partner = self.partner_id

        for bucket in self._BUCKET_KEYS:
            limit_field   = ClmLimitChangeRequestLine._LIMIT_FIELD_MAP[bucket]
            current_limit = getattr(partner, limit_field, 0.0)

            self.env['clm.limit.change.request.line'].create({
                'request_id':     self.id,
                'bucket':         bucket,
                'proposed_limit': current_limit,
            })

    # ─────────────────────────────────────────────────────────────────────────
    # CONSTRAINTS
    # ─────────────────────────────────────────────────────────────────────────

    @api.constrains('partner_id', 'line_ids')
    def _check_lines_not_empty(self):
        """
        Ensures all records with a partner also have bucket lines.
        Protects against programmatic creation that skips onchange.
        """
        for rec in self:
            if rec.partner_id and not rec.line_ids:
                raise ValidationError(
                    f"Request {rec.name} has no bucket lines.\n"
                    "Select the customer to auto-populate all buckets."
                )

    @api.constrains('line_ids')
    def _check_duplicate_buckets_in_lines(self):
        """Prevent the same bucket appearing twice on one request."""
        for rec in self:
            buckets = rec.line_ids.mapped('bucket')
            if len(buckets) != len(set(buckets)):
                raise ValidationError(
                    "Each bucket may appear only once per request.\n"
                    "Remove duplicate bucket lines."
                )

    @api.constrains('partner_id', 'state')
    def _check_unique_pending(self):
        """Prevent two pending requests for the same partner."""
        for rec in self:
            if rec.state == 'pending_fm':
                duplicate = self.search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('state',      '=', 'pending_fm'),
                    ('id',         '!=', rec.id),
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"A pending request ({duplicate.name}) already exists "
                        f"for {rec.partner_id.name}.\n"
                        f"Resolve the existing request before creating a new one."
                    )

    # ─────────────────────────────────────────────────────────────────────────
    # WRITE PROTECTION — Terminal state guard
    # SRS §9.3: Approved/rejected records cannot be modified
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, vals):
        for rec in self:
            if rec.state in ('approved', 'rejected') and not self.env.su:
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
        SoD: Only CCM can create limit change requests.
        Sequence assigned on creation.
        initiated_by set to current user for audit trail.
        Lines auto-populated if partner is given and no lines provided.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_ccm',
            'create limit change requests',
        )
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('clm.limit.change.request')
                    or 'New'
                )
            vals['initiated_by'] = self.env.uid

        records = super().create(vals_list)

        # Safety net: if created programmatically without lines, auto-populate
        for rec in records:
            if rec.partner_id and not rec.line_ids:
                rec._populate_bucket_lines()

        return records

    # ─────────────────────────────────────────────────────────────────────────
    # WORKFLOW ACTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def action_submit_to_fm(self):
        """
        CCM submits request for FM review.
        Transitions: draft → pending_fm.
        Schedules a mail.activity for the Finance Manager.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_ccm',
            'submit limit change requests',
        )
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    f"Only draft requests can be submitted. "
                    f"Current state: {rec.state} ({rec.name})"
                )
            if not rec.line_ids:
                raise UserError(
                    f"Cannot submit {rec.name} — no bucket lines found.\n"
                    "Select the customer to auto-populate all bucket lines."
                )

            rec.write({'state': 'pending_fm'})

            # Build line summary for chatter
            bucket_labels = dict(
                self.env['clm.limit.change.request.line']
                ._fields['bucket'].selection
            )
            line_summary = ''.join(
                f"<li><b>{bucket_labels.get(l.bucket)}</b>: "
                f"Current {l.current_limit:,.2f} → "
                f"Proposed {l.proposed_limit:,.2f} "
                f"({'⚠ Freeze' if l.request_type == 'freeze_resolution' else ''})</li>"
                for l in rec.line_ids
            )

            rec.message_post(
                body=Markup(
                    f"<b>Submitted for FM Approval</b><br/>"
                    f"Submitted by : {self.env.user.name}<br/>"
                    f"Customer     : {rec.partner_id.name}<br/>"
                    f"Request Type : "
                    f"{dict(self._fields['request_type'].selection).get(rec.request_type)}<br/>"
                    f"Buckets:<ul>{line_summary}</ul>"
                ),
                subtype_xmlid='mail.mt_note',
            )

            # Notify Finance Manager — Odoo 19: group_ids (not groups_id)
            finance_group = self.env.ref(
                'zencore_clms.group_zencore_clm_finance',
                raise_if_not_found=False,
            )
            if finance_group:
                finance_users = self.env['res.users'].search([
                    ('group_ids', 'in', [finance_group.id]),  # Odoo 19
                    ('share',     '=', False),
                    ('active',    '=', True),
                ], limit=1)
                if finance_users:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=finance_users[0].id,
                        note=(
                            f"Limit Change Request {rec.name} submitted by "
                            f"{self.env.user.name} for {rec.partner_id.name}. "
                            f"Please review and approve or reject."
                        ),
                    )

    def action_approve(self):
        """
        Finance Manager approves the request.
        Transitions: pending_fm → approved.
        Iterates ALL lines and writes each bucket's proposed_limit on the partner.
        previous_limit is captured per line for full audit trail.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_finance',
            'approve limit change requests',
        )
        for rec in self:
            if rec.state != 'pending_fm':
                raise UserError(
                    f"Only pending requests can be approved. "
                    f"Current state: {rec.state} ({rec.name})"
                )
            if not rec.line_ids:
                raise UserError(f"Request {rec.name} has no lines to approve.")

            # Apply each line's proposed limit to the partner
            for line in rec.line_ids:
                line._apply_limit_to_partner()

            rec.write({
                'state':         'approved',
                'reviewed_by':   self.env.uid,
                'reviewed_date': fields.Datetime.now(),
            })
            rec.activity_ids.action_done()

            # Build approval summary (previous_limit was set by _apply_limit_to_partner)
            bucket_labels = dict(
                self.env['clm.limit.change.request.line']
                ._fields['bucket'].selection
            )
            line_summary = ''.join(
                f"<li><b>{bucket_labels.get(l.bucket)}</b>: "
                f"{l.previous_limit:,.2f} → {l.proposed_limit:,.2f}</li>"
                for l in rec.line_ids
            )

            rec.message_post(
                body=(
                    f"<b>✅ Approved by {self.env.user.name}</b><br/>"
                    f"Customer : {rec.partner_id.name}<br/>"
                    f"Changes  :<ul>{line_summary}</ul>"
                    f"Comment  : {rec.fm_comment or '—'}"
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_reject(self):
        """
        Finance Manager rejects the request.
        Transitions: pending_fm → rejected.
        FM comment is required. Terminal state — cannot be reused.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_finance',
            'reject limit change requests',
        )
        for rec in self:
            if rec.state != 'pending_fm':
                raise UserError(
                    f"Only pending requests can be rejected. "
                    f"Current state: {rec.state} ({rec.name})"
                )
            if not rec.fm_comment or not rec.fm_comment.strip():
                raise UserError(
                    "A Finance Manager comment is required before rejecting.\n"
                    "Enter the rejection reason in the FM Comment field."
                )
            rec.write({
                'state':         'rejected',
                'reviewed_by':   self.env.uid,
                'reviewed_date': fields.Datetime.now(),
            })
            rec.activity_ids.action_done()
            rec.message_post(
                body=Markup(
                    f"<b>❌ Rejected by {self.env.user.name}</b><br/>"
                    f"Customer: {rec.partner_id.name}<br/>"
                    f"Reason  : {rec.fm_comment}"
                ),
                subtype_xmlid='mail.mt_note',
            )

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _assert_group(self, group_xml_id, action_label):
        if not self.env.user.has_group(group_xml_id):
            group = self.env.ref(group_xml_id)
            raise AccessError(
                f"You do not have permission to {action_label}.\n"
                f"Required group: {group.full_name}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# LINE MODEL
# ─────────────────────────────────────────────────────────────────────────────

class ClmLimitChangeRequestLine(models.Model):
    """
    clm.limit.change.request.line — One line per bucket.

    Fields:
    ────────
    bucket           : which bucket this line targets (auto-set, readonly after create)
    current_limit    : live value from partner at the time of viewing (non-stored compute)
    current_exposure : live balance from partner (non-stored compute)
    proposed_limit   : new limit requested — the only field CCM edits
    previous_limit   : captured at approval time for audit trail (written by _apply_limit_to_partner)
    request_type     : auto-classified freeze_resolution / standard_increase (stored compute)

    Design:
    ────────
    - All 5 buckets are always present — created by the header's onchange / create()
    - CCM cannot add or delete lines (enforced in view: create=0, delete=0)
    - bucket is readonly after creation (enforced in view)
    - proposed_limit defaults to current_limit — no accidental changes
    """

    _name = 'clm.limit.change.request.line'
    _description = 'CLM Limit Change Request Line'
    _order = 'bucket'

    # ─────────────────────────────────────────────────────────────────────────
    # FIELD MAPS — Class-level so header onchange can reference them directly
    # ─────────────────────────────────────────────────────────────────────────

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

    # Related convenience fields — no store, read from header
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
    )
    current_limit = fields.Monetary(
        string='Current Limit',
        compute='_compute_current_values',
        currency_field='currency_id',
    )
    current_exposure = fields.Monetary(
        string='Current Exposure',
        compute='_compute_current_values',
        currency_field='currency_id',
    )
    proposed_limit = fields.Monetary(
        string='Proposed Limit',
        required=True,
        currency_field='currency_id',
    )
    previous_limit = fields.Monetary(
        string='Previous Limit (at Approval)',
        readonly=True,
        currency_field='currency_id',
        copy=False,
        help='Captured at the moment FM approves. Shows what value was replaced.',
    )
    request_type = fields.Selection(
        selection=[
            ('freeze_resolution', 'Freeze Resolution'),
            ('standard_increase', 'Standard Increase'),
        ],
        string='Type',
        compute='_compute_request_type',
        store=True,
        help='freeze_resolution: exposure > current limit on this bucket.',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('request_id.partner_id', 'bucket')
    def _compute_current_values(self):
        for line in self:
            partner = line.request_id.partner_id
            if partner and line.bucket:
                line.current_limit    = getattr(
                    partner, self._LIMIT_FIELD_MAP[line.bucket], 0.0
                )
                line.current_exposure = getattr(
                    partner, self._BALANCE_FIELD_MAP[line.bucket], 0.0
                )
            else:
                line.current_limit    = 0.0
                line.current_exposure = 0.0

    @api.depends('current_exposure', 'current_limit')
    def _compute_request_type(self):
        for line in self:
            line.request_type = (
                'freeze_resolution'
                if line.current_exposure > line.current_limit > 0.0
                else 'standard_increase'
            )

    # ─────────────────────────────────────────────────────────────────────────
    # CONSTRAINTS
    # ─────────────────────────────────────────────────────────────────────────

    @api.constrains('proposed_limit')
    def _check_proposed_limit_positive(self):
        for line in self:
            if line.proposed_limit < 0:
                bucket_label = dict(
                    self._fields['bucket'].selection
                ).get(line.bucket, line.bucket)
                raise ValidationError(
                    f"Proposed limit cannot be negative — {bucket_label}."
                )

    # ─────────────────────────────────────────────────────────────────────────
    # APPROVAL HELPER — Called by action_approve on the header
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_limit_to_partner(self):
        """
        Writes this line's proposed_limit onto the partner for its bucket.
        Captures current value as previous_limit for audit trail.
        Uses clm_bypass_limit_protection context to pass res.partner.write() guard.

        Called by ClmLimitChangeRequest.action_approve() — not by users directly.
        """
        self.ensure_one()
        partner     = self.request_id.partner_id
        limit_field = self._LIMIT_FIELD_MAP[self.bucket]
        prev        = getattr(partner, limit_field, 0.0)

        # Write new limit — bypass the write() protection on res.partner
        partner.with_context(
            clm_bypass_limit_protection=True
        ).write({limit_field: self.proposed_limit})

        # Capture previous value on this line for the approval chatter summary
        # Use sudo to bypass terminal-state write guard on the line itself
        self.sudo().write({'previous_limit': prev})