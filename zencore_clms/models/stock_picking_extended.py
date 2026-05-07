from odoo import models


class StockPickingExtended(models.Model):
    """
    Delivery Validation Hook.

    On button_validate() for outgoing pickings:
      1. Check if customer group is frozen → block if yes
      2. After successful validation → move CLM stage: PI → Bucket 1
    """

    _inherit = 'stock.picking'

    def button_validate(self):
        """
        Override delivery validation.
        Freeze check runs BEFORE super() so the action is stopped early.
        Stage transition runs AFTER super() so we only move on success.
        """
        # Pre-validation: freeze check on outgoing (delivery) transfers
        for picking in self:
            if picking.picking_type_code == 'outgoing':
                sale = picking.sale_id if hasattr(picking, 'sale_id') else False
                if sale:
                    sale._clm_check_group_freeze('Delivery Validation')

        # Execute standard Odoo validation
        result = super().button_validate()

        # Post-validation: move CLM stage for all successfully validated pickings
        for picking in self:
            if (
                picking.picking_type_code == 'outgoing'
                and picking.state == 'done'
            ):
                sale = picking.sale_id if hasattr(picking, 'sale_id') else False
                if sale:
                    sale._clm_move_to_bucket1()

        return result