# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AssetUnregisterWizard(models.TransientModel):
    _name = 'asset.unregister.wizard'
    _description = 'Asset Unregistration Wizard'

    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True,
    )
    reason = fields.Text(
        string='Reason for Unregistration',
        required=True,
    )
    destination_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        required=True,
        domain="[('usage', 'in', ['internal', 'transit'])]",
    )

    def action_unregister(self):
        self.ensure_one()
        asset = self.asset_id

        # ── 1. Validate state ─────────────────────────────────────────────────
        if asset.state != 'available':
            raise UserError(_(
                'Only assets in "Available" state can be unregistered. '
                'Current state: %s'
            ) % asset.state)

        # ── 2. Determine asset location ───────────────────────────────────────
        asset_location = (
            self.env.company.asset_location_id
            or self.env.ref(
                'custom_asset_management.asset_stock_location',
                raise_if_not_found=False,
            )
        )
        if not asset_location:
            raise UserError(_(
                'No Asset Location configured. Please set it in Configuration > Settings.'
            ))

        # ── 3. Reverse stock move: asset_location → destination ───────────────
        move = self.env['stock.move'].create({
            'name': _('Asset Unregistration: %s') % asset.code,
            'product_id': asset.product_id.id,
            'product_uom': asset.product_id.uom_id.id,
            'product_uom_qty': 1.0,
            'location_id': asset_location.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': _('Asset Unregistration / %s') % asset.code,
            'state': 'draft',
            'company_id': asset.company_id.id,
        })
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': asset.product_id.id,
            'lot_id': asset.lot_id.id,
            'quantity': 1.0,
            'location_id': asset_location.id,
            'location_dest_id': self.destination_location_id.id,
            'company_id': asset.company_id.id,
        })
        move._action_confirm()
        move._action_assign()
        move.move_line_ids.quantity = 1.0
        move._action_done()

        # ── 4. Remove unposted depreciation lines ─────────────────────────────
        # unposted = asset.depreciation_line_ids.filtered(
        #     lambda l: not l.move_posted_check
        # )
        # # bypass the normal unlink (no override on dep lines)
        # unposted.unlink()
        if asset.odoo_asset_id:
            oa = asset.odoo_asset_id

            posted = oa.depreciation_move_ids.filtered(
                lambda m: m.state == 'posted'
            )

            if posted:
                # SCENARIO B — posted entries exist, cannot delete
                # pause stops the native cron from posting more entries
                oa.write({'state': 'paused'})
            else:
                # SCENARIO A — all entries are still draft, safe to wipe
                drafts = oa.depreciation_move_ids  # all are draft here
                if drafts:
                    drafts.button_cancel()   # draft → cancel (required before unlink)
                    drafts.unlink()          # physically remove from DB
                oa.write({'state': 'draft'}) # reset account.asset to draft

            # Detach the link regardless of scenario so re-registration
            # creates a brand new account.asset
            asset.write({'odoo_asset_id': False})

        # # ── 5. Reset asset state to draft ─────────────────────────────────────
        # old_state = asset.state
        # asset.write({
        #     'state': 'draft',
        #     'registration_date': False,
        #     'location_id': False,
        # })
        # ── 5. Remove custom unposted depreciation lines (legacy fallback) ────
        #
        # These only exist on assets registered before the native engine
        # integration. New registrations won't have them.
        asset.depreciation_line_ids.filtered(
            lambda l: not l.move_posted_check
        ).unlink()


        # # ── 6. Log history ────────────────────────────────────────────────────
        # asset._log_history(
        #     event_type='unregister',
        #     old_state=old_state,
        #     new_state='draft',
        #     description=_('Asset unregistered. Reason: %s') % self.reason,
        #     metadata={'destination': self.destination_location_id.complete_name},
        # )
        # ── 6. Reset asset state to draft ─────────────────────────────────────
        old_state = asset.state
        asset.write({
            'state': 'draft',
            'registration_date': False,
            'location_id': False,
        })

         # ── 7. Log history ────────────────────────────────────────────────────
        asset._log_history(
            event_type='unregister',
            old_state=old_state,
            new_state='draft',
            description=_('Asset unregistered. Reason: %s') % self.reason,
            metadata={'destination': self.destination_location_id.complete_name},
        )


        return {'type': 'ir.actions.act_window_close'}
