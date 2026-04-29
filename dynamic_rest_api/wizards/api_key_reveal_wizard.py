# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class DynamicApiKeyRevealWizard(models.TransientModel):
    """
    One-time display of the raw API key secret.

    After the key is generated (or regenerated), this wizard is opened so
    the user can copy the value.  The wizard stores the raw key only in a
    transient table — it is never persisted to the main model.
    """
    _name = 'dynamic.api.key.reveal.wizard'
    _description = 'API Key Reveal Wizard'

    api_key_id = fields.Many2one(
        'dynamic.api.key', string='API Key',
        readonly=True, required=True,
    )
    raw_key = fields.Char(
        string='Your API Key Secret',
        readonly=True,
        help='Copy this key now — it will NOT be shown again.',
    )
    key_name = fields.Char(
        related='api_key_id.name', string='Key Name', readonly=True,
    )

    def action_open_wizard(self):
        """Return an act_window action that opens this wizard record."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('API Key Generated'),
            'res_model': 'dynamic.api.key.reveal.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.model
    def create_and_open(self, api_key_id, raw_key):
        """Convenience method: create the wizard and return the open action."""
        wizard = self.create({'api_key_id': api_key_id, 'raw_key': raw_key})
        return wizard.action_open_wizard()