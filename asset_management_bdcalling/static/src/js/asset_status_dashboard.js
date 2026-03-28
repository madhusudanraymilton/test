/** @odoo-module **/

import { registry }   from "@web/core/registry";
import { loadBundle }  from "@web/core/assets";
import {
    Component,
    onWillStart,
    onMounted,
    onPatched,
    useState,
    useRef,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// ─── Palette & helpers ────────────────────────────────────────────────────────

const STATE_META = {
    draft:     { label: "Draft",     color: "#64748B", bg: "#F1F5F9", icon: "fa-file-text-o",   light: "#E2E8F0" },
    available: { label: "Available", color: "#059669", bg: "#ECFDF5", icon: "fa-check-circle",  light: "#D1FAE5" },
    assigned:  { label: "Assigned",  color: "#4F46E5", bg: "#EEF2FF", icon: "fa-user-circle-o", light: "#C7D2FE" },
    scrapped:  { label: "Scrapped",  color: "#E11D48", bg: "#FFF1F2", icon: "fa-times-circle",  light: "#FECDD3" },
    disposed:  { label: "Disposed",  color: "#D97706", bg: "#FFF7ED", icon: "fa-archive",        light: "#FDE68A" },
};

const EVENT_COLOR = {
    register:   "#059669",
    unregister: "#D97706",
    assign:     "#4F46E5",
    return:     "#2563EB",
    scrap:      "#E11D48",
    dispose:    "#DC2626",
    depreciate: "#0891B2",
    note:       "#64748B",
};

function fmt(n) {
    return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(n || 0);
}

function fmtInt(n) {
    return new Intl.NumberFormat().format(n || 0);
}

// ─────────────────────────────────────────────────────────────────────────────

export class AssetStatusDashboard extends Component {
    static template = "asset_management_bdcalling.AssetStatusDashboard";

    setup() {
        this.orm    = useService("orm");
        this.action = useService("action");

        this.donutRef = useRef("donutCanvas");
        this._chart   = null;

        this.state = useState({
            loading:           true,
            error:             null,
            // filters
            productId:         null,
            productName:       "",
            assetId:           null,
            assetName:         "",
            // data
            counts:            { draft: 0, available: 0, assigned: 0, scrapped: 0, disposed: 0 },
            total:             0,
            total_value:       0,
            net_book_value:    0,
            total_depreciated: 0,
            currency:          "",
            history:           [],
            cards:             { draft: [], available: [], assigned: [], scrapped: [], disposed: [] },
            // ui
            activeTab:         "overview",  // overview | draft | available | assigned | scrapped | disposed
            searchQuery:       "",
        });

        // Expose helpers to template
        this.STATE_META  = STATE_META;
        this.EVENT_COLOR = EVENT_COLOR;

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this._load();
        });

        onMounted(()  => this._drawDonut());
        onPatched(()  => this._drawDonut());
    }

    // ── Data ─────────────────────────────────────────────────────────────────

    async _load() {
        this.state.loading = true;
        this.state.error   = null;
        try {
            const data = await this.orm.call(
                "asset.status.dashboard",
                "get_status_dashboard_data",
                [],
                {
                    product_id: this.state.productId || null,
                    asset_id:   this.state.assetId   || null,
                    company_id: null,
                }
            );
            Object.assign(this.state, data, { loading: false });
        } catch (e) {
            this.state.loading = false;
            this.state.error   = e.message || "Failed to load dashboard data.";
        }
    }

    // ── Donut chart ───────────────────────────────────────────────────────────

    _drawDonut() {
        const canvas = this.donutRef.el;
        if (!canvas) return;
        const ChartJS = window.Chart;
        if (!ChartJS) return;

        const c  = this.state.counts;
        const labels = ["Draft","Available","Assigned","Scrapped","Disposed"];
        const values = [c.draft, c.available, c.assigned, c.scrapped, c.disposed];
        const colors = ["#64748B","#059669","#4F46E5","#E11D48","#D97706"];

        if (this._chart) { this._chart.destroy(); this._chart = null; }

        this._chart = new ChartJS(canvas, {
            type: "doughnut",
            data: {
                labels,
                datasets: [{ data: values, backgroundColor: colors, borderWidth: 3, borderColor: "#fff", hoverOffset: 6 }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "68%",
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#0F172A",
                        titleColor: "#F1F5F9",
                        bodyColor: "#CBD5E1",
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: ctx => ` ${ctx.label}: ${ctx.parsed}`,
                        },
                    },
                },
            },
        });
    }

    // ── Navigation tabs ───────────────────────────────────────────────────────

    setTab(tab) {
        this.state.activeTab    = tab;
        this.state.searchQuery  = "";
    }

    // ── Card filter / search ──────────────────────────────────────────────────

    get filteredCards() {
        const tab = this.state.activeTab;
        if (tab === "overview") return [];
        const q = (this.state.searchQuery || "").toLowerCase();
        const cards = this.state.cards[tab] || [];
        if (!q) return cards;
        return cards.filter(c =>
            (c.code  || "").toLowerCase().includes(q) ||
            (c.name  || "").toLowerCase().includes(q) ||
            (c.serial || "").toLowerCase().includes(q) ||
            (c.employee || "").toLowerCase().includes(q)
        );
    }

    // ── Computed helpers ──────────────────────────────────────────────────────

    get utilisationPct() {
        const active = (this.state.counts.available || 0) + (this.state.counts.assigned || 0);
        if (!active) return 0;
        return Math.round((this.state.counts.assigned || 0) / active * 100);
    }

    statePct(s) {
        if (!this.state.total) return 0;
        return Math.round((this.state.counts[s] || 0) / this.state.total * 100);
    }

    // ── Open Odoo list view for a state ───────────────────────────────────────

    async openState(state) {
        this.setTab(state);
    }

    async navigateToList(state) {
        const domain = [];
        if (this.state.assetId) {
            domain.push(["id", "=", this.state.assetId]);
        } else if (this.state.productId) {
            domain.push(["product_id", "=", this.state.productId]);
            domain.push(["lot_id", "!=", false]);
        }
        if (state === "scrapped_disposed") {
            domain.push(["asset_state", "in", ["scrapped", "disposed"]]);
        } else {
            domain.push(["asset_state", "=", state]);
        }
        const names = {
            draft: "Draft Assets", available: "Available Assets",
            assigned: "Assigned Assets", scrapped: "Scrapped Assets",
            disposed: "Disposed Assets", scrapped_disposed: "Scrapped / Disposed",
        };
        await this.action.doAction({
            type:      "ir.actions.act_window",
            name:      names[state] || "Assets",
            res_model: "account.asset",
            views:     [[false, "list"], [false, "kanban"], [false, "form"]],
            domain,
        });
    }

    async navigateToAsset(assetId) {
        await this.action.doAction({
            type:      "ir.actions.act_window",
            name:      "Asset",
            res_model: "account.asset",
            res_id:    assetId,
            view_mode: "form",
            views:     [[false, "form"]],
        });
    }

    // ── Refresh ───────────────────────────────────────────────────────────────

    async refresh() {
        if (this._chart) { this._chart.destroy(); this._chart = null; }
        await this._load();
    }

    // ── Format helpers (exposed to template) ─────────────────────────────────

    fmt(n)    { return fmt(n); }
    fmtInt(n) { return fmtInt(n); }
    eventColor(type) { return EVENT_COLOR[type] || "#64748B"; }
    stateMeta(s)     { return STATE_META[s] || STATE_META.draft; }
}

registry.category("actions").add(
    "asset_management_bdcalling.AssetStatusDashboard",
    AssetStatusDashboard
);