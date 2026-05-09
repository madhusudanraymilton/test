from odoo import models
from odoo.exceptions import AccessError


class StockPickingExtended(models.Model):
    """
    Delivery Validation Hook — stock.picking extension.

    SRS §3.2: Delivery validation → stage PI → Bucket 1.
    SRS §6.2: Delivery validation is BLOCKED when group is frozen.
    SRS §10 (SoD): Only Warehouse staff may validate deliveries.

    Design:
    ────────
    - Freeze check in button_validate() — user-facing gate, raises before wizard opens.
    - Stage transition in _action_done() — reliable post-validation hook.
    - SoD group check ONLY in button_validate() — _action_done() is also called
      programmatically by Odoo internals (backorder wizard, scheduled auto-validate).
      Putting the group check in _action_done() would break those automated flows.
    """

    _inherit = 'stock.picking'

    def button_validate(self):
        """
        User-facing validation button.
        Gate 1: SoD — Only Warehouse staff.
        Gate 2: Freeze — Block if customer group is frozen.

        NOTE: _action_done() is intentionally NOT protected by SoD group check.
        It is an internal ORM method called by Odoo's own backorder and scheduling
        logic. Protecting it would break automated flows.
        """
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_warehouse'):
            raise AccessError(
                "Only Warehouse staff can validate deliveries."
            )

        # Freeze check only on outgoing (customer delivery) transfers with a linked SO
        for picking in self.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.sale_id
        ):
            picking.sale_id._clm_check_group_freeze('Delivery Validation')

        return super().button_validate()

    def _action_done(self):
        """
        Internal post-validation hook. Fires after all backorder wizard interactions.
        At this point picking.state == 'done' is guaranteed.

        No SoD group check here — this method is called by Odoo internals
        (backorder wizard, scheduler). Only the stage transition logic runs.
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
