from odoo import models, fields, api


class AccountAssetExtended(models.Model):
    _inherit = "account.asset"

    product_id = fields.Many2one(
        "product.template",
        string="Product",
        domain=[('is_asset', '=', True)]
    )

    lot_id = fields.Many2one(
        "stock.lot",
        string="Serial Number",
        domain="[('product_id', '=', product_id)]"
    )

    location_id = fields.Many2one(
        "stock.quant",
        string="Location",
        # compute="_compute_location",
        store=True
    )

    stock_value = fields.Float(
        string="Value",
        store=True
    )

    # 📍 Get location from selected serial/lot
    @api.depends("lot_id")
    def _compute_location(self):
        for rec in self:
            quant = self.env["stock.quant"].search(
                [("lot_id", '=', rec.lot_id.id)],
                limit=1
            )
            rec.location_id = quant.location_id if quant else False

    # 💰 Get cost from stock valuation
    # @api.depends("lot_id")
    # def _compute_stock_value(self):
    #     for rec in self:
    #         valuation = self.env["stock.valuation.layer"].search(
    #             [("lot_id", '=', rec.lot_id.id)],
    #             limit=1,
    #             order="create_date desc"
    #         )
    #         rec.stock_value = valuation.value if valuation else 0.0