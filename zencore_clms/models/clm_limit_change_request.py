from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError, ValidationError


class ClmLimitChangeRequest(models.Model):
    """
    Bucket Limit Change Workflow.

    State Machine:
      draft → pending_fm → approved / rejected

    Rules:
      - Only CCM can create and submit requests
      - Only Finance Manager can approve or reject
      - Rejected requests are closed and cannot be reused
      - Limit is updated directly on res.partner upon approval
      - Full audit trail: initiator, approver, timestamps, old/new values
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
        # domain=[('customer_rank', '>', 0)],
        ondelete='restrict',
        tracking=True,
    )
    bucket = fields.Selection(
        selection=[
            ('proforma', 'Proforma Invoice'),
            ('bucket1', 'Bucket 1'),
            ('bucket2', 'Bucket 2'),
            ('bucket3', 'Bucket 3'),
            ('bucket4', 'Bucket 4'),
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
    # AUTO-CLASSIFICATION
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
            ('draft', 'Draft'),
            ('pending_fm', 'Pending FM Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        readonly=True,
        tracking=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # AUDIT TRAIL — All readonly, set by system
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
        string='Previous Limit (at Approval)',
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
    # FIELD MAPPINGS — Bucket → Partner field names
    # ─────────────────────────────────────────────────────────────────────────

    _LIMIT_FIELD_MAP = {
        'proforma': 'clm_proforma_limit',
        'bucket1': 'clm_bucket_1_limit',
        'bucket2': 'clm_bucket_2_limit',
        'bucket3': 'clm_bucket_3_limit',
        'bucket4': 'clm_bucket_4_limit',
    }

    _BALANCE_FIELD_MAP = {
        'proforma': 'clm_proforma_balance',
        'bucket1': 'clm_bucket_1_balance',
        'bucket2': 'clm_bucket_2_balance',
        'bucket3': 'clm_bucket_3_balance',
        'bucket4': 'clm_bucket_4_balance',
    }

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE METHODS
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

    @api.depends('current_exposure', 'current_limit')
    def _compute_request_type(self):
        for rec in self:
            rec.request_type = (
                'freeze_resolution'
                if rec.current_exposure > rec.current_limit
                else 'standard_increase'
            )


    #check unique pending request per bucket per partner
    @api.constrains('partner_id', 'bucket', 'state')
    def _check_unique_pending(self):
        for rec in self:
            if rec.state == 'pending_fm':
                duplicate = self.search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('bucket', '=', rec.bucket),
                    ('state', '=', 'pending_fm'),
                    ('id', '!=', rec.id),
                ], limit=1)
                if duplicate:
                    raise ValidationError( 
                        f"A pending request ({duplicate.name}) already exists "
                        f"for {rec.partner_id.name} — {rec.bucket}."
                    )

    # ─────────────────────────────────────────────────────────────────────────
    # ORM OVERRIDES
    # ─────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
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
        CCM submits request for FM review.
        Only CCM group members can call this action.
        """
        self._assert_group('zencore_clms.group_zencore_clm_ccm', 'submit limit change requests')
        for rec in self:
            if rec.state != 'draft':
                raise UserError(f"Only draft requests can be submitted. ({rec.name})")
            if rec.proposed_limit <= 0:
                raise UserError("Proposed limit must be greater than zero.")
            rec.write({'state': 'pending_fm'})
            rec.message_post(
                body=f"Request submitted by {self.env.user.name} for FM review.",
                subtype_xmlid='mail.mt_note',
            )

    def action_approve(self):
        """
        Finance Manager approves the request.
        Updates the partner limit immediately.
        Freeze status is automatically re-evaluated (non-stored compute).
        """
        self._assert_group('zencore_clms.group_zencore_clm_finance', 'approve limit change requests')
        for rec in self:
            if rec.state != 'pending_fm':
                raise UserError(f"Only pending requests can be approved. ({rec.name})")

            limit_field = self._LIMIT_FIELD_MAP[rec.bucket]

            # Capture previous value for audit
            prev_limit = getattr(rec.partner_id, limit_field, 0.0)

            # Apply the new limit
            # rec.partner_id.write({limit_field: rec.proposed_limit})

            rec.partner_id.with_context(
                clm_bypass_limit_protection=True
            ).write({limit_field: rec.proposed_limit})

            rec.write({
                'state': 'approved',
                'previous_limit': prev_limit,
                'reviewed_by': self.env.uid,
                'reviewed_date': fields.Datetime.now(),
            })
            rec.message_post(
                body=(
                    f"✅ Approved by {self.env.user.name}.\n"
                    f"Bucket: {dict(rec._fields['bucket'].selection).get(rec.bucket)}\n"
                    f"Previous Limit: {prev_limit:,.2f} → New Limit: {rec.proposed_limit:,.2f}"
                ),
                subtype_xmlid='mail.mt_note',
            )

    # def action_reject(self):
    #     """
    #     Finance Manager rejects the request.
    #     Rejected requests are permanently closed — cannot be reused.
    #     """
    #     self._assert_group('zencore_clms.group_zencore_clm_finance', 'reject limit change requests')
    #     for rec in self:
    #         if rec.state != 'pending_fm':
    #             raise UserError(f"Only pending requests can be rejected. ({rec.name})")
    #         rec.write({
    #             'state': 'rejected',
    #             'reviewed_by': self.env.uid,
    #             'reviewed_date': fields.Datetime.now(),
    #         })
    #         rec.message_post(
    #             body=f"❌ Rejected by {self.env.user.name}. Comment: {rec.fm_comment or 'None'}",
    #             subtype_xmlid='mail.mt_note',
    #         )

    def action_reject(self):
        self._assert_group('zencore_clms.group_zencore_clm_finance', 'reject')
        for rec in self:
            if rec.state != 'pending_fm':
                raise UserError(...)
            if not rec.fm_comment or not rec.fm_comment.strip():
                raise UserError(
                    "Rejection requires a Finance Manager comment.\n"
                    "Please explain the reason for rejection in the FM Comment field."
                )
            rec.write({
                'state': 'rejected',
                'reviewed_by': self.env.uid,
                'reviewed_date': fields.Datetime.now(),
            })

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _assert_group(self, group_xml_id, action_label):
        """Raises AccessError if current user does not belong to the required group."""
        if not self.env.user.has_group(group_xml_id):
            group = self.env.ref(group_xml_id)
            raise AccessError(
                f"You do not have permission to {action_label}.\n"
                f"Required group: {group.full_name}"
            )