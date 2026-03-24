# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AssetUnregisterWizard(models.TransientModel):
    _name = 'asset.unregister.wizard'
    _description = 'Asset Unregistration Wizard'

    asset_id = fields.Many2one(
        'account.asset',
        string='Asset',
        required=True,
    )
    reason = fields.Text(
        string='Reason for Unregistration',
        required=True,
    )
    destination_location_id = fields.Many2one(
        'stock.location',
        string='Return to Location',
        required=True,
        domain="[('usage', 'in', ['internal', 'transit'])]",
        default=lambda self: self.env.ref(
            'stock.stock_location_stock', raise_if_not_found=False
        ),
    )

    def action_unregister(self):
        self.ensure_one()
        asset = self.asset_id

        # ── 1. Validate AMS state ─────────────────────────────────────────────
        if asset.asset_state != 'available':
            raise UserError(_(
                'Only assets in "Available" status can be unregistered. '
                'Current status: %s'
            ) % asset.asset_state)

        if not asset.product_id or not asset.lot_id:
            raise UserError(_('Asset must have a Product and Serial Number.'))

        # ── 2. Locate where the serial number actually is right now ───────────
        #
        # action_register() moved the item:  source_location → scrap_location
        # We must move it back from wherever it currently sits (quant > 0),
        # which is the scrap location after a normal registration.
        #
        quant = self.env['stock.quant'].search([
            ('product_id', '=', asset.product_id.id),
            ('lot_id',     '=', asset.lot_id.id),
            ('quantity',   '>',  0),
        ], limit=1)

        if not quant:
            raise UserError(_(
                'Serial number "%s" could not be found in any stock location. '
                'It may have already been moved or the registration did not '
                'complete correctly.'
            ) % asset.lot_id.name)

        source_location = quant.location_id   # ← scrap (or wherever register put it)

        # ── 3. Reverse stock move — identical pattern to action_register() ────
        #
        #   register:   source_location  →  scrap_location   (removes from stock)
        #   unregister: scrap_location   →  destination      (restores to stock)
        #
        move = self.env['stock.move'].create({
            'product_id':          asset.product_id.id,
            'product_uom_qty':     1.0,
            'product_uom':         asset.product_id.uom_id.id,
            'location_id':         source_location.id,
            'location_dest_id':    self.destination_location_id.id,
            'description_picking': _('Asset Unregister: %s') % asset.name,
            'company_id':          asset.company_id.id,
        })

        move._action_confirm()
        move._action_assign()

        self.env['stock.move.line'].create({
            'move_id':          move.id,
            'product_id':       asset.product_id.id,
            'qty_done':         1.0,
            'location_id':      source_location.id,
            'location_dest_id': self.destination_location_id.id,
            'lot_id':           asset.lot_id.id,
        })

        move._action_done()

        # ── 4. Reset AMS state and clear registration fields ──────────────────
        old_state = asset.asset_state
        asset.write({
            'asset_state':          'draft',
            'registration_date':    False,
            'location_id':          False,
            'original_location_id': False,
        })

        # ── 5. Log history ────────────────────────────────────────────────────
        asset._log_history(
            event_type='unregister',
            old_state=old_state,
            new_state='draft',
            description=_('Asset unregistered. Reason: %s') % self.reason,
            metadata={
                'source':      source_location.complete_name,
                'destination': self.destination_location_id.complete_name,
            },
        )

        return {'type': 'ir.actions.act_window_close'}