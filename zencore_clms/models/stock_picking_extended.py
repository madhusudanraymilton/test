# # models/stock_picking_extended.py

from odoo import models
from odoo.exceptions import AccessError


class StockPickingExtended(models.Model):
    """
    Delivery Validation Hook — stock.picking extension.

    SRS §3.2: Outgoing delivery validation → CLM stage PI → Bucket 1.
    SRS §6.2: Outgoing delivery is BLOCKED when customer group is frozen.
    SRS §10 (SoD): Only Warehouse staff may validate OUTGOING (customer) deliveries.

    SCOPE:
      All CLM checks (SoD group + freeze) apply ONLY to:
        - picking_type_code == 'outgoing'   (customer delivery)
        - sale_id is set                    (linked to a sale order)

      Purchase receipts (incoming), internal transfers, returns, and any
      other picking type bypass ALL CLM logic entirely. Odoo's own stock
      and purchase ACL rules govern those flows.
    """

    _inherit = 'stock.picking'

    def button_validate(self):
        """
        User-facing validation button.

        CLM SoD + freeze checks apply ONLY to outgoing CLM-tracked deliveries.
        All other picking types (purchase receipts, internal moves, returns)
        fall through to super() without any CLM restriction.
        """
        for picking in self:
            if (
                picking.picking_type_code == 'outgoing'
                and picking.sale_id
            ):
                # Gate 1: SoD — Warehouse only for customer deliveries
                if not self.env.user.has_group(
                    'zencore_groups.group_zencore_clm_warehouse'
                ):
                    raise AccessError(
                        "Only Warehouse staff can validate customer deliveries."
                    )
                # Gate 2: Freeze — block if customer group is frozen
                picking.sale_id._clm_check_group_freeze('Delivery Validation')

        return super().button_validate()

    def _action_done(self):
        """
        Internal post-validation hook. Fires after all backorder interactions.

        No SoD check here — called by Odoo internals (backorder wizard,
        scheduler, purchase receipt confirmation).
        Only outgoing sale-linked pickings trigger CLM stage transitions.
        """
        result = super()._action_done()

        for picking in self.filtered(
            lambda p: (
                p.picking_type_code == 'outgoing'
                and p.state == 'done'
                and p.sale_id
            )
        ):
            picking.sale_id._clm_move_to_bucket1()

        return result