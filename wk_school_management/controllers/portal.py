# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>; )
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>;
#
#################################################################################

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal
import logging
_logger = logging.getLogger(__name__)


class PaymentPortal(payment_portal.PaymentPortal):
    @http.route()
    def payment_pay(self, *args, amount=None, fee_slip_id=None, access_token=None, **kwargs):

        amount = self._cast_as_float(amount)
        fee_slip_id = self._cast_as_int(fee_slip_id)
        if fee_slip_id:
            slip_sudo = request.env['wk.fee.slip'].sudo().browse(fee_slip_id).exists()
            if not slip_sudo:
                raise ValidationError(_("The provided parameters are invalid."))

            if not payment_utils.check_access_token(
                access_token, slip_sudo.student_id.user_id.partner_id.id, amount, slip_sudo.currency_id.id
            ):
                raise ValidationError(_("The provided parameters are invalid."))

            kwargs.update({
                'reference': slip_sudo.name,
                'currency_id': slip_sudo.currency_id.id,
                'partner_id': slip_sudo.student_id.user_id.partner_id.id,
                'company_id': slip_sudo.student_id.company_id.id,
                'fee_slip_id': fee_slip_id,
            })
        return super().payment_pay(*args, amount=amount, access_token=access_token, **kwargs)

    def _create_transaction(
        self, provider_id, payment_method_id, token_id, amount, currency_id, partner_id, flow,
        tokenization_requested, landing_route, reference_prefix=None, is_validation=False,custom_create_values=None, **kwargs):

        tx_sudo = super()._create_transaction(
            provider_id, payment_method_id, token_id, amount, currency_id, partner_id, flow,
            tokenization_requested, landing_route, reference_prefix, is_validation,
            custom_create_values, **kwargs
        )
        if kwargs.get('fee_slip_id'):
            tx_sudo.write({
                'fee_slip_ids': [(6, 0, [kwargs.get('fee_slip_id')])]
            })
        return tx_sudo


class CustomPaymentPortal(PaymentPortal):
    @staticmethod
    def _validate_transaction_kwargs(kwargs, additional_allowed_keys=()):
        whitelist = {
            'provider_id',
            'payment_method_id',
            'token_id',
            'amount',
            'flow',
            'tokenization_requested',
            'landing_route',
            'is_validation',
            'csrf_token',
        }
        additional_allowed_keys = ('fee_slip_id', 'reference_prefix')
        whitelist.update(additional_allowed_keys)

        if 'PaymentPortal' in globals():
            PaymentPortal._validate_transaction_kwargs(kwargs, additional_allowed_keys)

        rejected_keys = set(kwargs.keys()) - whitelist
        if rejected_keys:
            raise ValidationError(
                _("The following kwargs are not whitelisted: %s", ', '.join(rejected_keys))
            )
