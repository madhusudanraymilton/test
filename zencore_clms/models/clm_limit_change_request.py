from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError, ValidationError


class ClmLimitChangeRequest(models.Model):
    """
    Bucket Limit Change Workflow — clm.limit.change.request.

    State Machine:
      draft → pending_fm → approved / rejected

    SRS §9 Compliance:
    ───────────────────
    - Only CCM can create and submit (draft → pending_fm)
    - Only Finance Manager can approve or reject
    - Approved: limit updated immediately on res.partner
    - Rejected: permanently closed, cannot be reused or resubmitted
    - Full audit trail: initiator, approver, timestamps, old/new values

    FIXES from v0.2.0:
    ───────────────────
    - action_reject: Fixed syntax error (raise UserError(...) with Ellipsis)
    - action_reject: Added message_post for audit trail
    - write() guard: Rejected records cannot be modified
    - action_approve: Posts activity completion notification
    - Unique pending constraint: Improved duplicate detection
    - FM activity: Created on submit to notify Finance Manager
    """

    _name = 'clm.limit.change.request'
    _description = 'CLM Bucket Limit Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

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
    # REQUEST DETAILS
    # ─────────────────────────────────────────────────────────────────────────

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
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
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
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
        tracking=True,
    )
    justification = fields.Text(
        string='Justification',
        required=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # AUTO-CLASSIFICATION (SRS §9.2)
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
    # AUDIT TRAIL (SRS §9.4) — All set by system, never by users
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
    previous_limit = fields.Monetary(
        string='Previous Limit (at Decision)',
        readonly=True,
        currency_field='currency_id',
        copy=False,
    )
    fm_comment = fields.Text(
        string='Finance Manager Comment',
        copy=False,
        tracking=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # FIELD MAPPINGS — Bucket key → partner field names
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
    # COMPUTE METHODS
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('partner_id', 'bucket')
    def _compute_current_values(self):
        for rec in self:
            if rec.partner_id and rec.bucket:
                rec.current_limit    = getattr(rec.partner_id, self._LIMIT_FIELD_MAP[rec.bucket], 0.0)
                rec.current_exposure = getattr(rec.partner_id, self._BALANCE_FIELD_MAP[rec.bucket], 0.0)
            else:
                rec.current_limit    = 0.0
                rec.current_exposure = 0.0

    @api.depends('current_exposure', 'current_limit')
    def _compute_request_type(self):
        for rec in self:
            rec.request_type = (
                'freeze_resolution'
                if rec.current_exposure > rec.current_limit
                else 'standard_increase'
            )

    # ─────────────────────────────────────────────────────────────────────────
    # CONSTRAINTS
    # ─────────────────────────────────────────────────────────────────────────

    @api.constrains('partner_id', 'bucket', 'state')
    def _check_unique_pending(self):
        """
        Prevent duplicate pending requests for the same partner+bucket.
        Note: This constraint is best-effort. For true atomicity, a
        PostgreSQL unique partial index would be required.
        """
        for rec in self:
            if rec.state == 'pending_fm':
                duplicate = self.search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('bucket',     '=', rec.bucket),
                    ('state',      '=', 'pending_fm'),
                    ('id',         '!=', rec.id),
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"A pending request ({duplicate.name}) already exists "
                        f"for {rec.partner_id.name} — {dict(self._fields['bucket'].selection).get(rec.bucket)}.\n"
                        f"Resolve the existing request before creating a new one."
                    )

    @api.constrains('proposed_limit')
    def _check_proposed_limit_positive(self):
        for rec in self:
            if rec.proposed_limit <= 0:
                raise ValidationError("Proposed limit must be greater than zero.")

    # ─────────────────────────────────────────────────────────────────────────
    # WRITE PROTECTION — Prevent modification of terminal states
    # SRS §9.3: Rejected requests cannot be reused.
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, vals):
        """
        Block any modification to records in terminal states (approved/rejected).
        This prevents attempts to reset and reuse rejected requests.
        """
        for rec in self:
            if rec.state in ('approved', 'rejected'):
                # Only allow system-level writes (e.g., ORM internal)
                if not self.env.su:
                    raise AccessError(
                        f"Request {rec.name} is in a terminal state ({rec.state}) "
                        f"and cannot be modified. Rejected requests cannot be reused."
                    )
        return super().write(vals)

    # ─────────────────────────────────────────────────────────────────────────
    # ORM OVERRIDES
    # ─────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        """
        SoD: Only CCM can create limit change requests.
        Sequence number assigned on creation.
        Initiated_by always set to current user for audit trail.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_ccm',
            'create limit change requests'
        )
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('clm.limit.change.request')
                    or 'New'
                )
            vals['initiated_by'] = self.env.uid
        return super().create(vals_list)

    # ─────────────────────────────────────────────────────────────────────────
    # WORKFLOW ACTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def action_submit_to_fm(self):
        """
        CCM submits the request for FM review.
        Transitions: draft → pending_fm.
        Creates a mail.activity for the Finance Manager group to ensure
        FM is notified (SRS §9.4 — audit and traceability).
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_ccm',
            'submit limit change requests'
        )
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    f"Only Draft requests can be submitted. Current state: {rec.state} ({rec.name})"
                )
            rec.write({'state': 'pending_fm'})
            rec.message_post(
                body=(
                    f"<b>Submitted for FM Approval</b><br/>"
                    f"Submitted by: {self.env.user.name}<br/>"
                    f"Bucket: {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
                    f"Proposed Limit: {rec.proposed_limit:,.2f}<br/>"
                    f"Request Type: {dict(self._fields['request_type'].selection).get(rec.request_type)}"
                ),
                subtype_xmlid='mail.mt_note',
            )
            # Create activity to notify Finance Manager
            finance_group = self.env.ref('zencore_clms.group_zencore_clm_finance')
            finance_users = finance_group.users if finance_group else self.env['res.users']
            if finance_users:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=finance_users[0].id,
                    note=(
                        f"Limit Change Request {rec.name} submitted by CCM "
                        f"({self.env.user.name}) for {rec.partner_id.name} — "
                        f"{dict(self._fields['bucket'].selection).get(rec.bucket)}. "
                        f"Proposed limit: {rec.proposed_limit:,.2f}. Please review."
                    ),
                )

    def action_approve(self):
        """
        Finance Manager approves the request.
        Transitions: pending_fm → approved.
        Immediately updates the partner limit via bypass context.
        Freeze is auto-re-evaluated (non-stored compute).
        SRS §9.2 Stage 2.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_finance',
            'approve limit change requests'
        )
        for rec in self:
            if rec.state != 'pending_fm':
                raise UserError(
                    f"Only Pending requests can be approved. Current state: {rec.state} ({rec.name})"
                )

            limit_field = self._LIMIT_FIELD_MAP[rec.bucket]
            prev_limit  = getattr(rec.partner_id, limit_field, 0.0)

            # Write new limit with bypass (res.partner.write() blocks direct edits)
            rec.partner_id.with_context(
                clm_bypass_limit_protection=True
            ).write({limit_field: rec.proposed_limit})

            rec.write({
                'state':          'approved',
                'previous_limit': prev_limit,
                'reviewed_by':    self.env.uid,
                'reviewed_date':  fields.Datetime.now(),
            })

            # Mark any pending activity as done
            rec.activity_ids.action_done()

            rec.message_post(
                body=(
                    f"<b>✅ Approved by {self.env.user.name}</b><br/>"
                    f"Customer : {rec.partner_id.name}<br/>"
                    f"Bucket   : {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
                    f"Previous : {prev_limit:,.2f}<br/>"
                    f"New Limit: {rec.proposed_limit:,.2f}<br/>"
                    f"Comment  : {rec.fm_comment or '—'}"
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_reject(self):
        """
        Finance Manager rejects the request.
        Transitions: pending_fm → rejected.
        Rejected requests are permanently closed (SRS §9.3).
        FM comment is REQUIRED for rejected requests (governance rule).

        FIX from v0.2.0: Was `raise UserError(...)` with Python Ellipsis literal —
        that is a syntax error. Fixed to proper string arguments.
        """
        self._assert_group(
            'zencore_clms.group_zencore_clm_finance',
            'reject limit change requests'
        )
        for rec in self:
            if rec.state != 'pending_fm':
                raise UserError(
                    f"Only Pending requests can be rejected. Current state: {rec.state} ({rec.name})"
                )
            if not rec.fm_comment or not rec.fm_comment.strip():
                raise UserError(
                    "A Finance Manager comment is required before rejecting.\n"
                    "Please enter the rejection reason in the FM Comment field."
                )

            rec.write({
                'state':         'rejected',
                'reviewed_by':   self.env.uid,
                'reviewed_date': fields.Datetime.now(),
            })

            # Mark any pending activity as done
            rec.activity_ids.action_done()

            rec.message_post(
                body=(
                    f"<b>❌ Rejected by {self.env.user.name}</b><br/>"
                    f"Customer: {rec.partner_id.name}<br/>"
                    f"Bucket  : {dict(self._fields['bucket'].selection).get(rec.bucket)}<br/>"
                    f"Reason  : {rec.fm_comment}"
                ),
                subtype_xmlid='mail.mt_note',
            )

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _assert_group(self, group_xml_id, action_label):
        """
        Raises AccessError if current user does not belong to the required group.
        Provides a clear, user-friendly error with group name.
        """
        if not self.env.user.has_group(group_xml_id):
            group = self.env.ref(group_xml_id)
            raise AccessError(
                f"You do not have permission to {action_label}.\n"
                f"Required group: {group.full_name}"
            )
