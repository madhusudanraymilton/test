# # # models/stock_picking_extended.py

# from odoo import models
# from odoo.exceptions import AccessError

# class StockPickingExtended(models.Model):
#     """
#     Delivery Validation Hook — stock.picking extension.

#     SRS §3.2: Outgoing delivery validation → CLM stage PI → Bucket 1.
#     SRS §6.2: Outgoing delivery is BLOCKED when customer group is frozen.
#     SRS §10 (SoD): Only Warehouse staff may validate OUTGOING (customer) deliveries.

#     SCOPE:
#       All CLM checks (SoD group + freeze) apply ONLY to:
#         - picking_type_code == 'outgoing'   (customer delivery)
#         - sale_id is set                    (linked to a sale order)

#       Purchase receipts (incoming), internal transfers, returns, and any
#       other picking type bypass ALL CLM logic entirely. Odoo's own stock
#       and purchase ACL rules govern those flows.
#     """

#     _inherit = 'stock.picking'

#     def button_validate(self):
#         """
#         User-facing validation button.

#         CLM SoD + freeze checks apply ONLY to outgoing CLM-tracked deliveries.
#         All other picking types (purchase receipts, internal moves, returns)
#         fall through to super() without any CLM restriction.
#         """

#         for picking in self:
#             if (
#                 picking.picking_type_code == 'outgoing'
#                 and picking.sale_id
#             ):
#                 # Gate 1: SoD — Warehouse only for customer deliveries
#                 if not self.env.user.has_group(
#                     'zencore_groups.group_zencore_clm_warehouse'
#                 ):
#                     raise AccessError(
#                         "Only Warehouse staff can validate customer deliveries."
#                     )
#                 # Gate 2: Freeze — block if customer group is frozen
#                 picking.sale_id._clm_check_group_freeze('Delivery Validation')

#         return super().button_validate()

#     # def _action_done(self):
#     #     """
#     #     Internal post-validation hook. Fires after all backorder interactions.

#     #     No SoD check here — called by Odoo internals (backorder wizard,
#     #     scheduler, purchase receipt confirmation).
#     #     Only outgoing sale-linked pickings trigger CLM stage transitions.
#     #     """
#     #     result = super()._action_done()

#     #     for picking in self.filtered(
#     #         lambda p: (
#     #             p.picking_type_code == 'outgoing'
#     #             and p.state == 'done'
#     #             and p.sale_id
#     #         )
#     #     ):
#     #         picking.sale_id._clm_move_to_fully_delivered()

#     #     return result

#     # def _action_done(self):
#     #     """
#     #     Internal post-validation hook.  Fires after all backorder
#     #     interactions are resolved by Odoo.
 
#     #     No SoD check here — this method is also called by Odoo internals
#     #     (backorder wizard, scheduler, purchase receipt confirmation).
 
#     #     Only outgoing, done, sale-linked pickings trigger CLM stage
#     #     transitions.  The delivery-progress helper on the order compares
#     #     cumulative delivered qty against ordered qty to decide whether the
#     #     transition is partial or final.
#     #     """
#     #     result = super()._action_done()
 
#     #     for picking in self.filtered(
#     #         lambda p: (
#     #             p.picking_type_code == 'outgoing'
#     #             and p.state == 'done'
#     #             and p.sale_id
#     #         )
#     #     ):
#     #         order = picking.sale_id
#     #         delivered, ordered = order._clm_get_delivery_progress()
 
#     #         if ordered <= 0:
#     #             # No ordered quantity on the SO — nothing to advance.
#     #             continue
 
#     #         if delivered >= ordered:
#     #             # ── Full delivery (or over-delivery) ─────────────────────────
#     #             # Handles both:
#     #             #   pi → fully_delivered        (single complete delivery)
#     #             #   partially_delivered → fully_delivered  (final delivery)
#     #             order._clm_move_to_fully_delivered()
 
#     #         elif delivered > 0:
#     #             # ── Partial delivery ─────────────────────────────────────────
#     #             # Only advances if order is still in 'pi'; if already
#     #             # partially_delivered the filter inside the method is a no-op
#     #             # (correct — we don't loop back within the same stage).
#     #             order._clm_move_to_partially_delivered()
 
#     #     return result

from odoo import models
from odoo.exceptions import AccessError


class StockPickingExtended(models.Model):
    """
    Delivery Validation Hook — stock.picking extension.

    SRS §3.2: Outgoing delivery → CLM operational stage update on the linked SO.
    SRS §6.2: Outgoing delivery is BLOCKED when the customer group is frozen.
    SRS §10  : Only Warehouse staff may validate OUTGOING (customer) deliveries.

    SCOPE:
      All CLM checks (SoD + freeze) apply ONLY to:
        - picking_type_code == 'outgoing'   (customer delivery)
        - sale_id is set                    (linked to a sale order)

      Purchase receipts, internal transfers, returns → bypass ALL CLM logic.

    ── FIX vs previous version ─────────────────────────────────────────────────
    Previous code used:
      total = sum(picking.mapped('product_uom_qty'))
      done  = sum(picking.mapped('quantity_done'))

    BUG: product_uom_qty and quantity_done are fields on stock.move,
    NOT on stock.picking. picking.mapped() returns an empty list → always 0.

    Fix: Use SO order_line.qty_delivered AFTER super()._action_done().
    This reads from sale.order.line which Odoo recalculates from done stock
    moves automatically. Using the SO aggregate also correctly handles
    multi-picking scenarios (multiple pickings for one SO).
    """

    _inherit = 'stock.picking'

    def button_validate(self):
        """
        User-facing validation button.
        SoD + freeze checks apply to outgoing CLM-tracked deliveries only.
        """
        for picking in self:
            if picking.picking_type_code == 'outgoing' and picking.sale_id:
                # Gate 1: SoD — Warehouse only
                if not self.env.user.has_group('zencore_groups.group_zencore_clm_warehouse'):
                    raise AccessError(
                        "Only Warehouse staff can validate customer deliveries."
                    )
                # Gate 2: Freeze — block if customer group is frozen (SRS §6.2)
                picking.sale_id._clm_check_group_freeze('Delivery Validation')

        return super().button_validate()

    def _action_done(self):
        """
        Internal post-validation hook. Fires after all backorder interactions.
        Updates SO operational stage based on aggregate delivery status.

        Uses order_line.qty_delivered (not picking-level move quantities) because:
          1. qty_delivered on sale.order.line is recomputed from all done moves
             after super()._action_done() writes stock.move state to 'done'.
          2. This correctly handles multi-picking and backorder scenarios.
          3. We invalidate the cache to force a fresh read after the ORM writes.
        """
        result = super()._action_done()

        for picking in self.filtered(
            lambda p: (
                p.sale_id
                and p.picking_type_code == 'outgoing'
                and p.state == 'done'
            )
        ):
            order = picking.sale_id

            # Invalidate qty_delivered cache: it must re-read from DB after
            # _action_done() has written the stock.move done quantities.
            order.order_line.invalidate_recordset(['qty_delivered'])

            total_ordered = sum(
                line.product_uom_qty for line in order.order_line
                if not line.display_type           # exclude sections/notes
            )
            total_delivered = sum(
                line.qty_delivered for line in order.order_line
                if not line.display_type
            )

            if total_ordered <= 0:
                continue

            # Tolerance: 0.001 to handle float rounding (e.g. 9.99999 ≈ 10)
            if total_delivered >= total_ordered - 0.001:
                order._clm_move_to_fully_delivered()
            elif total_delivered > 0:
                order._clm_move_to_partially_delivered()

        return result