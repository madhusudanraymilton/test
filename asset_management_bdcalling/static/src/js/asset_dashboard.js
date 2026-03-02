/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class AssetDashboard extends Component {
    static template = "asset_management_bdcalling.AssetDashboard";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            total: 0,
            available: 0,
            assigned: 0,
            scrapped_disposed: 0,
            total_value: 0,
            net_book_value: 0,
            pending_depreciation: 0,
            by_category: [],
        });

        onWillStart(async () => {
            await this._loadDashboardData();
        });
    }

    async _loadDashboardData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("asset.asset", "get_dashboard_data", []);
            Object.assign(this.state, data);
        } finally {
            this.state.loading = false;
        }
    }

    formatCurrency(value) {
        return new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value || 0);
    }

    getPct(count) {
        if (!this.state.total) return 0;
        return Math.round((count / this.state.total) * 100);
    }

    async openAllAssets() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "All Assets",
            res_model: "asset.asset",
            view_mode: "list,form",
            domain: [],
        });
    }

    async openAvailableAssets() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Available Assets",
            res_model: "asset.asset",
            view_mode: "list,form",
            domain: [["state", "=", "available"]],
        });
    }

    async openAssignedAssets() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Assigned Assets",
            res_model: "asset.asset",
            view_mode: "list,form",
            domain: [["state", "=", "assigned"]],
        });
    }

    async openPendingDepreciation() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Pending Depreciation Lines",
            res_model: "asset.depreciation.line",
            view_mode: "list",
            domain: [["move_check", "=", false]],
        });
    }

    async refresh() {
        await this._loadDashboardData();
    }
}

registry.category("actions").add("asset_management_bdcalling.AssetDashboard", AssetDashboard);
