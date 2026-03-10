/** @odoo-module **/

/**
 * OWL Asset Dashboard component.
 *
 * FIX: Chart.js is now imported via the Odoo 18/19 bundler-compatible syntax.
 * Chart.js must be present at static/lib/chartjs/chart.umd.min.js and
 * declared in __manifest__.py under web.assets_backend BEFORE this file.
 * (The global `Chart` constructor is then available from that UMD bundle.)
 *
 * If you prefer the ES-module approach (Odoo 18 bundles chart.js as an npm dep):
 *   import { Chart, registerables } from "chart.js";
 *   Chart.register(...registerables);
 */

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AssetDashboard extends Component {
    static template = "asset_management_bdcalling.AssetDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        /** @type {Chart|null} */
        this._chart = null;

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
            recent_assignments: [],
        });

        onWillStart(async () => {
            await this._loadDashboard();
        });

        onMounted(() => {
            if (!this.state.loading) {
                this._renderChart();
            }
        });

        // FIX: destroy Chart instance when component unmounts to avoid canvas reuse errors
        onWillUnmount(() => {
            if (this._chart) {
                this._chart.destroy();
                this._chart = null;
            }
        });
    }

    async _loadDashboard() {
        try {
            const data = await this.orm.call("asset.asset", "get_dashboard_data", []);
            Object.assign(this.state, data, { loading: false });
        } catch (e) {
            console.error("AMS Dashboard: failed to load data", e);
            this.state.loading = false;
        }
    }

    _renderChart() {
        if (!this.state.by_category.length) {
            return;
        }

        // Guard: Chart must be available from the UMD bundle loaded before this file
        if (typeof Chart === "undefined") {
            console.warn(
                "AMS Dashboard: Chart.js not found. " +
                "Make sure static/lib/chartjs/chart.umd.min.js is present and " +
                "listed in __manifest__.py assets BEFORE asset_dashboard.js."
            );
            return;
        }

        const canvas = this.__owl__.refs && this.__owl__.refs["categoryChart"]
            ? this.__owl__.refs["categoryChart"]
            : document.getElementById("categoryChart");

        if (!canvas) {
            return;
        }

        // Destroy previous instance before re-creating (prevents canvas reuse error)
        if (this._chart) {
            this._chart.destroy();
            this._chart = null;
        }

        const labels = this.state.by_category.map((x) => x.category);
        const values = this.state.by_category.map((x) => x.count);

        // eslint-disable-next-line no-undef
        this._chart = new Chart(canvas, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Assets",
                        data: values,
                        backgroundColor: "#3b82f6",
                        borderRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                    },
                },
            },
        });
    }

    async openAllAssets() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Assets",
            res_model: "asset.asset",
            view_mode: "list,form",
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

    async refresh() {
        this.state.loading = true;
        await this._loadDashboard();
        this._renderChart();
    }
}

registry.category("actions").add(
    "asset_management_bdcalling.AssetDashboard",
    AssetDashboard
);
