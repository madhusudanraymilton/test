# -*- coding: utf-8 -*-
from odoo import fields, models


class AssetValuation(models.Model):
    _name = 'asset.valuation'
    _description = 'Asset Valuation (SQL View)'
    _auto = False
    _order = 'code'

    name = fields.Char(string='Asset Name', readonly=True)
    code = fields.Char(string='Asset Code', readonly=True)
    category_id = fields.Many2one('asset.category', string='Category', readonly=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('available', 'Available'),
            ('assigned', 'Assigned'),
            ('returned', 'Returned'),
            ('scrapped', 'Scrapped'),
            ('disposed', 'Disposed'),
        ],
        string='Status',
        readonly=True,
    )
    purchase_price = fields.Float(string='Purchase Price', readonly=True)
    total_depreciated = fields.Float(string='Total Depreciated', readonly=True)
    residual_value = fields.Float(string='Net Book Value', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS asset_valuation;
            CREATE OR REPLACE VIEW asset_valuation AS (
                SELECT
                    aa.id                           AS id,
                    aa.name                         AS name,
                    aa.code                         AS code,
                    aa.category_id                  AS category_id,
                    aa.state                        AS state,
                    aa.purchase_price               AS purchase_price,
                    aa.company_id                   AS company_id,
                    aa.currency_id                  AS currency_id,
                    COALESCE(dep.total_depreciated, 0.0) AS total_depreciated,
                    aa.purchase_price - COALESCE(dep.total_depreciated, 0.0)
                                                    AS residual_value
                FROM asset_asset aa
                LEFT JOIN (
                    SELECT
                        asset_id,
                        SUM(amount) AS total_depreciated
                    FROM asset_depreciation_line
                    WHERE move_posted_check = TRUE
                    GROUP BY asset_id
                ) dep ON dep.asset_id = aa.id
                WHERE aa.active = TRUE
            )
        """)
