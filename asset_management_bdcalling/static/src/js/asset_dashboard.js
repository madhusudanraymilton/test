// /** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { loadBundle } from "@web/core/assets";
// import { Component, onWillStart, onMounted, onPatched, useState, useRef } from "@odoo/owl";
// import { useService } from "@web/core/utils/hooks";

// export class AssetDashboard extends Component {

//     static template = "asset_management_bdcalling.AssetDashboard";

//     setup() {
//         this.orm       = useService("orm");
//         this.action    = useService("action");
//         this.canvasRef = useRef("categoryChart");
//         this._chart    = null;

//         this.state = useState({
//             loading:              true,
//             total:                0,
//             available:            0,
//             assigned:             0,
//             scrapped_disposed:    0,
//             // total_value:          0,
//             // net_book_value:       0,
//             // pending_depreciation: 0,
//             by_category:          [],
//             recent_assignments:   [],
//         });

//         onWillStart(async () => {
//             // "web.chartjs_lib" is the named bundle Odoo uses for Chart.js.
//             // This is identical to how @web/views/graph/graph_renderer.js loads it.
//             // After this resolves, window.Chart is available globally.
//             await loadBundle("web.chartjs_lib");
//             await this._loadDashboard();
//         });

//         // First render — canvas is inside t-else so it may not be in DOM yet.
//         onMounted(() => this._renderChart());

//         // Every reactive re-render — catches the loading=true→false transition
//         // that inserts the canvas into the DOM.
//         onPatched(() => this._renderChart());
//     }

//     // ── Data ─────────────────────────────────────────────────────────────────

//     async _loadDashboard() {
//         const data = await this.orm.call("account.asset", "get_dashboard_data", []);
//         Object.assign(this.state, data, { loading: false });
//     }

//     // ── Chart ─────────────────────────────────────────────────────────────────

//     _renderChart() {
//         const canvas = this.canvasRef.el;
//         if (!canvas) return;                      // canvas not in DOM yet
//         if (!this.state.by_category.length) return;

//         // window.Chart is populated by loadBundle("web.chartjs_lib")
//         const ChartJS = window.Chart;
//         if (!ChartJS) return;

//         const labels  = this.state.by_category.map(x => x.category);
//         const values  = this.state.by_category.map(x => x.count);
//         const PALETTE = [
//             "#2563EB", "#059669", "#4F46E5", "#D97706",
//             "#0891B2", "#E11D48", "#7C3AED", "#0D9488",
//         ];

//         if (this._chart) {
//             this._chart.destroy();
//             this._chart = null;
//         }

//         this._chart = new ChartJS(canvas, {
//             type: "bar",
//             data: {
//                 labels,
//                 datasets: [{
//                     label: "Assets",
//                     data: values,
//                     backgroundColor: labels.map((_, i) => PALETTE[i % PALETTE.length]),
//                     borderRadius: 6,
//                     borderSkipped: false,
//                 }],
//             },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 plugins: {
//                     legend: { display: false },
//                     tooltip: {
//                         backgroundColor: "#1E293B",
//                         titleColor: "#F1F5F9",
//                         bodyColor: "#CBD5E1",
//                         padding: 12,
//                         cornerRadius: 8,
//                     },
//                 },
//                 scales: {
//                     x: {
//                         grid: { display: false },
//                         ticks: { color: "#64748B", font: { size: 12 } },
//                     },
//                     y: {
//                         grid: { color: "#F1F5F9" },
//                         ticks: { color: "#64748B", font: { size: 12 }, stepSize: 1 },
//                         beginAtZero: true,
//                     },
//                 },
//             },
//         });
//     }

//     // ── Helpers ───────────────────────────────────────────────────────────────

//     formatCurrency(value) {
//         return new Intl.NumberFormat(undefined, {
//             minimumFractionDigits: 2,
//             maximumFractionDigits: 2,
//         }).format(value || 0);
//     }

//     // ── Navigation ────────────────────────────────────────────────────────────

//     async openAllAssets() {
//         await this.action.doAction({
//             type: "ir.actions.act_window",
//             name: "All Assets",
//             res_model: "account.asset",
//             views: [[false, "list"], [false, "kanban"], [false, "form"]],
//         });
//     }

//     async openAvailableAssets() {
//         await this.action.doAction({
//             type: "ir.actions.act_window",
//             name: "Available Assets",
//             res_model: "account.asset",
//             views: [[false, "list"], [false, "kanban"], [false, "form"]],
//             domain: [["state", "=", "available"]],
//         });
//     }

//     async openAssignedAssets() {
//         await this.action.doAction({
//             type: "ir.actions.act_window",
//             name: "Assigned Assets",
//             res_model: "asset.assignment",
//             views: [[false, "list"], [false, "form"]],
//             domain: [["is_active", "=", true]],
//         });
//     }

//     async openScrappedAssets() {
//         await this.action.doAction({
//             type: "ir.actions.act_window",
//             name: "Scrapped / Disposed Assets",
//             res_model: "account.asset",
//             views: [[false, "list"], [false, "kanban"], [false, "form"]],
//             domain: [["state", "in", ["scrapped", "disposed"]]],
//         });
//     }

//     // async openPendingDepreciation() {
//     //     await this.action.doAction({
//     //         type: "ir.actions.act_window",
//     //         name: "Pending Depreciation",
//     //         res_model: "asset.depreciation.line",
//     //         views: [[false, "list"]],
//     //         domain: [["move_check", "=", false]],
//     //     });
//     // }

//     async refresh() {
//         this.state.loading = true;
//         await this._loadDashboard();
//     }
// }

// registry.category("actions").add(
//     "asset_management_bdcalling.AssetDashboard",
//     AssetDashboard
// );

/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import {
    Component,
    onWillStart,
    onMounted,
    onPatched,
    useState,
    useRef,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AssetDashboard extends Component {

    static template = "asset_management_bdcalling.AssetDashboard";

    setup() {
        this.orm       = useService("orm");
        this.action    = useService("action");
        this.canvasRef = useRef("categoryChart");
        this._chart    = null;

        this.state = useState({
            loading:              true,
            total:                0,
            available:            0,
            assigned:             0,
            scrapped_disposed:    0,
            total_value:          0,
            net_book_value:       0,
            total_depreciated:    0,
            pending_depreciation: 0,
            by_category:          [],
            recent_assignments:   [],
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this._loadDashboard();
        });

        onMounted(()  => this._renderChart());
        onPatched(()  => this._renderChart());
    }

    // ── Data ─────────────────────────────────────────────────────────────────

    async _loadDashboard() {
        const data = await this.orm.call("account.asset", "get_dashboard_data", []);
        Object.assign(this.state, data, { loading: false });
    }

    // ── Chart ─────────────────────────────────────────────────────────────────

    _renderChart() {
        const canvas = this.canvasRef.el;
        if (!canvas || !this.state.by_category.length) return;

        const ChartJS = window.Chart;
        if (!ChartJS) return;

        const labels  = this.state.by_category.map(x => x.category);
        const values  = this.state.by_category.map(x => x.count);
        const PALETTE = [
            "#2563EB", "#059669", "#4F46E5", "#D97706",
            "#0891B2", "#E11D48", "#7C3AED", "#0D9488",
        ];

        if (this._chart) {
            this._chart.destroy();
            this._chart = null;
        }

        this._chart = new ChartJS(canvas, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Assets",
                    data: values,
                    backgroundColor: labels.map((_, i) => PALETTE[i % PALETTE.length]),
                    borderRadius: 6,
                    borderSkipped: false,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#1E293B",
                        titleColor: "#F1F5F9",
                        bodyColor: "#CBD5E1",
                        padding: 12,
                        cornerRadius: 8,
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: "#64748B", font: { size: 12 } },
                    },
                    y: {
                        grid: { color: "#F1F5F9" },
                        ticks: { color: "#64748B", font: { size: 12 }, stepSize: 1 },
                        beginAtZero: true,
                    },
                },
            },
        });
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    formatCurrency(value) {
        return new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value || 0);
    }

    /** Percentage of assigned assets vs total (0–100). */
    get utilisationPct() {
        return this.state.total
            ? Math.round(this.state.assigned / this.state.total * 100)
            : 0;
    }

    // ── Navigation ────────────────────────────────────────────────────────────

    async openAllAssets() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "All Assets",
            res_model: "account.asset",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: [["lot_id", "!=", false]],
        });
    }

    async openAvailableAssets() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Available Assets",
            res_model: "account.asset",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: [["asset_state", "=", "available"]],
        });
    }

    async openAssignedAssets() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Active Assignments",
            res_model: "asset.assignment",
            views: [[false, "list"], [false, "form"]],
            domain: [["is_active", "=", true]],
        });
    }

    async openScrappedAssets() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Scrapped / Disposed Assets",
            res_model: "account.asset",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: [["asset_state", "in", ["scrapped", "disposed"]]],
        });
    }

    async openPendingDepreciation() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Pending Depreciation Entries",
            res_model: "account.move",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["asset_id", "!=", false],
                ["state",    "=",  "draft"],
                ["date",     "<=", new Date().toISOString().slice(0, 10)],
            ],
        });
    }

    async refresh() {
        this.state.loading = true;
        if (this._chart) {
            this._chart.destroy();
            this._chart = null;
        }
        await this._loadDashboard();
    }
}

registry.category("actions").add(
    "asset_management_bdcalling.AssetDashboard",
    AssetDashboard
);