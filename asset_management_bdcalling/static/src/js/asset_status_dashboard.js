// /** @odoo-module **/

// import { registry }   from "@web/core/registry";
// import { loadBundle }  from "@web/core/assets";
// import {
//     Component,
//     onWillStart,
//     onMounted,
//     onPatched,
//     useState,
//     useRef,
//     useExternalListener,
// } from "@odoo/owl";
// import { useService } from "@web/core/utils/hooks";

// // ─── Palette & helpers ────────────────────────────────────────────────────────

// const STATE_META = {
//     draft:     { label: "Draft",     color: "#64748B", bg: "#F1F5F9", icon: "fa-file-text-o",   light: "#E2E8F0" },
//     available: { label: "Available", color: "#059669", bg: "#ECFDF5", icon: "fa-check-circle",  light: "#D1FAE5" },
//     assigned:  { label: "Assigned",  color: "#4F46E5", bg: "#EEF2FF", icon: "fa-user-circle-o", light: "#C7D2FE" },
//     scrapped:  { label: "Scrapped",  color: "#E11D48", bg: "#FFF1F2", icon: "fa-times-circle",  light: "#FECDD3" },
//     disposed:  { label: "Disposed",  color: "#D97706", bg: "#FFF7ED", icon: "fa-archive",        light: "#FDE68A" },
// };

// const EVENT_COLOR = {
//     register:   "#059669",
//     unregister: "#D97706",
//     assign:     "#4F46E5",
//     return:     "#2563EB",
//     scrap:      "#E11D48",
//     dispose:    "#DC2626",
//     depreciate: "#0891B2",
//     note:       "#64748B",
// };

// function fmt(n) {
//     return new Intl.NumberFormat(undefined, {
//         minimumFractionDigits: 2,
//         maximumFractionDigits: 2,
//     }).format(n || 0);
// }

// function fmtInt(n) {
//     return new Intl.NumberFormat().format(n || 0);
// }

// // ─────────────────────────────────────────────────────────────────────────────

// export class AssetStatusDashboard extends Component {
//     static template = "asset_management_bdcalling.AssetStatusDashboard";

//     setup() {
//         this.orm    = useService("orm");
//         this.action = useService("action");

//         this.donutRef        = useRef("donutCanvas");
//         this.productInputRef = useRef("productSearchInput");
//         this.assetInputRef   = useRef("assetSearchInput");
//         this._chart          = null;
//         this._searchTimer    = null;

//         this.state = useState({
//             loading:           true,
//             error:             null,
//             // ── filters ────────────────────────────────────────────────────
//             productId:         null,
//             productName:       "",
//             assetId:           null,
//             assetName:         "",
//             // ── search UI ─────────────────────────────────────────────────
//             productQuery:      "",
//             assetQuery:        "",
//             productResults:    [],
//             assetResults:      [],
//             showProductDrop:   false,
//             showAssetDrop:     false,
//             productSearching:  false,
//             assetSearching:    false,
//             // ── data ──────────────────────────────────────────────────────
//             counts:            { draft: 0, available: 0, assigned: 0, scrapped: 0, disposed: 0 },
//             total:             0,
//             total_value:       0,
//             net_book_value:    0,
//             total_depreciated: 0,
//             currency:          "",
//             history:           [],
//             cards:             { draft: [], available: [], assigned: [], scrapped: [], disposed: [] },
//             // ── ui ────────────────────────────────────────────────────────
//             activeTab:         "overview",
//             searchQuery:       "",
//         });

//         // Expose helpers to template
//         this.STATE_META  = STATE_META;
//         this.EVENT_COLOR = EVENT_COLOR;

//         // Close dropdowns when clicking outside
//         useExternalListener(document, "click", this._onDocumentClick.bind(this));

//         onWillStart(async () => {
//             await loadBundle("web.chartjs_lib");
//             await this._load();
//         });

//         onMounted(()  => this._drawDonut());
//         onPatched(()  => this._drawDonut());
//     }

//     // ── Data ─────────────────────────────────────────────────────────────────

//     async _load() {
//         this.state.loading = true;
//         this.state.error   = null;
//         try {
//             const data = await this.orm.call(
//                 "asset.status.dashboard",
//                 "get_status_dashboard_data",
//                 [],
//                 {
//                     product_id: this.state.productId || null,
//                     asset_id:   this.state.assetId   || null,
//                     company_id: null,
//                 }
//             );
//             Object.assign(this.state, data, { loading: false });
//         } catch (e) {
//             this.state.loading = false;
//             this.state.error   = e.message || "Failed to load dashboard data.";
//         }
//     }

//     // ── Product search ────────────────────────────────────────────────────────

//     async onProductInput(ev) {
//         const q = ev.target.value;
//         this.state.productQuery = q;
//         this.state.showProductDrop = true;

//         if (this._searchTimer) clearTimeout(this._searchTimer);

//         if (!q.trim()) {
//             this.state.productResults = [];
//             return;
//         }

//         this.state.productSearching = true;
//         this._searchTimer = setTimeout(async () => {
//             try {
//                 const results = await this.orm.searchRead(
//                     "product.product",
//                     [["is_asset", "=", true], ["name", "ilike", q]],
//                     ["id", "name"],
//                     { limit: 8 }
//                 );
//                 this.state.productResults   = results;
//                 this.state.productSearching = false;
//             } catch {
//                 this.state.productSearching = false;
//             }
//         }, 250);
//     }

//     async onProductFocus() {
//         this.state.showProductDrop = true;
//         if (!this.state.productResults.length && !this.state.productQuery) {
//             // Pre-load first few asset products
//             const results = await this.orm.searchRead(
//                 "product.product",
//                 [["is_asset", "=", true]],
//                 ["id", "name"],
//                 { limit: 8 }
//             );
//             this.state.productResults = results;
//         }
//     }

//     selectProduct(id, name) {
//         this.state.productId       = id;
//         this.state.productName     = name;
//         this.state.productQuery    = name;
//         this.state.showProductDrop = false;
//         this.state.productResults  = [];
//         // Reset asset filter when product changes
//         this.clearAsset();
//         this._load();
//     }

//     clearProduct() {
//         this.state.productId       = null;
//         this.state.productName     = "";
//         this.state.productQuery    = "";
//         this.state.productResults  = [];
//         this.state.showProductDrop = false;
//         this.clearAsset();
//         this._load();
//     }

//     // ── Asset search ──────────────────────────────────────────────────────────

//     async onAssetInput(ev) {
//         const q = ev.target.value;
//         this.state.assetQuery = q;
//         this.state.showAssetDrop = true;

//         if (this._searchTimer) clearTimeout(this._searchTimer);

//         if (!q.trim()) {
//             this.state.assetResults = [];
//             return;
//         }

//         this.state.assetSearching = true;
//         this._searchTimer = setTimeout(async () => {
//             try {
//                 const domain = [
//                     ["lot_id", "!=", false],
//                     ["asset_state", "!=", "draft"],
//                     "|",
//                     ["name", "ilike", q],
//                     ["code", "ilike", q],
//                 ];
//                 if (this.state.productId) {
//                     domain.push(["product_id", "=", this.state.productId]);
//                 }
//                 const results = await this.orm.searchRead(
//                     "account.asset",
//                     domain,
//                     ["id", "name", "code"],
//                     { limit: 8 }
//                 );
//                 this.state.assetResults   = results;
//                 this.state.assetSearching = false;
//             } catch {
//                 this.state.assetSearching = false;
//             }
//         }, 250);
//     }

//     async onAssetFocus() {
//         this.state.showAssetDrop = true;
//         if (!this.state.assetResults.length && !this.state.assetQuery) {
//             // Pre-load first few registered assets
//             const domain = [["lot_id", "!=", false], ["asset_state", "!=", "draft"]];
//             if (this.state.productId) {
//                 domain.push(["product_id", "=", this.state.productId]);
//             }
//             const results = await this.orm.searchRead(
//                 "account.asset",
//                 domain,
//                 ["id", "name", "code"],
//                 { limit: 8 }
//             );
//             this.state.assetResults = results;
//         }
//     }

//     selectAsset(id, name, code) {
//         this.state.assetId       = id;
//         this.state.assetName     = code ? `${code} — ${name}` : name;
//         this.state.assetQuery    = this.state.assetName;
//         this.state.showAssetDrop = false;
//         this.state.assetResults  = [];
//         this._load();
//     }

//     clearAsset() {
//         this.state.assetId       = null;
//         this.state.assetName     = "";
//         this.state.assetQuery    = "";
//         this.state.assetResults  = [];
//         this.state.showAssetDrop = false;
//         if (arguments.length === 0) {
//             // Only reload if called standalone (not as part of clearProduct chain)
//             this._load();
//         }
//     }

//     // ── Close dropdowns on outside click ─────────────────────────────────────

//     _onDocumentClick(ev) {
//         const productWrap = this.el && this.el.querySelector(".asd-search-field-wrap[data-field='product']");
//         const assetWrap   = this.el && this.el.querySelector(".asd-search-field-wrap[data-field='asset']");

//         if (productWrap && !productWrap.contains(ev.target)) {
//             this.state.showProductDrop = false;
//             // Restore display name if a product is selected
//             if (this.state.productId && !this.state.productQuery) {
//                 this.state.productQuery = this.state.productName;
//             }
//         }
//         if (assetWrap && !assetWrap.contains(ev.target)) {
//             this.state.showAssetDrop = false;
//             if (this.state.assetId && !this.state.assetQuery) {
//                 this.state.assetQuery = this.state.assetName;
//             }
//         }
//     }

//     // ── Donut chart ───────────────────────────────────────────────────────────

//     _drawDonut() {
//         const canvas = this.donutRef.el;
//         if (!canvas) return;
//         const ChartJS = window.Chart;
//         if (!ChartJS) return;

//         const c  = this.state.counts;
//         const labels = ["Draft","Available","Assigned","Scrapped","Disposed"];
//         const values = [c.draft, c.available, c.assigned, c.scrapped, c.disposed];
//         const colors = ["#64748B","#059669","#4F46E5","#E11D48","#D97706"];

//         if (this._chart) { this._chart.destroy(); this._chart = null; }

//         this._chart = new ChartJS(canvas, {
//             type: "doughnut",
//             data: {
//                 labels,
//                 datasets: [{ data: values, backgroundColor: colors, borderWidth: 3, borderColor: "#fff", hoverOffset: 6 }],
//             },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 cutout: "68%",
//                 plugins: {
//                     legend: { display: false },
//                     tooltip: {
//                         backgroundColor: "#0F172A",
//                         titleColor: "#F1F5F9",
//                         bodyColor: "#CBD5E1",
//                         padding: 12,
//                         cornerRadius: 8,
//                         callbacks: {
//                             label: ctx => ` ${ctx.label}: ${ctx.parsed}`,
//                         },
//                     },
//                 },
//             },
//         });
//     }

//     // ── Navigation tabs ───────────────────────────────────────────────────────

//     setTab(tab) {
//         this.state.activeTab   = tab;
//         this.state.searchQuery = "";
//     }

//     // ── Card filter / search ──────────────────────────────────────────────────

//     get filteredCards() {
//         const tab = this.state.activeTab;
//         if (tab === "overview") return [];
//         const q = (this.state.searchQuery || "").toLowerCase();
//         const cards = this.state.cards[tab] || [];
//         if (!q) return cards;
//         return cards.filter(c =>
//             (c.code     || "").toLowerCase().includes(q) ||
//             (c.name     || "").toLowerCase().includes(q) ||
//             (c.serial   || "").toLowerCase().includes(q) ||
//             (c.employee || "").toLowerCase().includes(q)
//         );
//     }

//     // ── Computed helpers ──────────────────────────────────────────────────────

//     get utilisationPct() {
//         const active = (this.state.counts.available || 0) + (this.state.counts.assigned || 0);
//         if (!active) return 0;
//         return Math.round((this.state.counts.assigned || 0) / active * 100);
//     }

//     statePct(s) {
//         if (!this.state.total) return 0;
//         return Math.round((this.state.counts[s] || 0) / this.state.total * 100);
//     }

//     // ── Navigation ────────────────────────────────────────────────────────────

//     async openState(state) {
//         this.setTab(state);
//     }

//     async navigateToList(state) {
//         const domain = [];
//         if (this.state.assetId) {
//             domain.push(["id", "=", this.state.assetId]);
//         } else if (this.state.productId) {
//             domain.push(["product_id", "=", this.state.productId]);
//             domain.push(["lot_id", "!=", false]);
//         }
//         if (state === "scrapped_disposed") {
//             domain.push(["asset_state", "in", ["scrapped", "disposed"]]);
//         } else {
//             domain.push(["asset_state", "=", state]);
//         }
//         const names = {
//             draft: "Draft Assets", available: "Available Assets",
//             assigned: "Assigned Assets", scrapped: "Scrapped Assets",
//             disposed: "Disposed Assets", scrapped_disposed: "Scrapped / Disposed",
//         };
//         await this.action.doAction({
//             type:      "ir.actions.act_window",
//             name:      names[state] || "Assets",
//             res_model: "account.asset",
//             views:     [[false, "list"], [false, "kanban"], [false, "form"]],
//             domain,
//         });
//     }

//     async navigateToAsset(assetId) {
//         await this.action.doAction({
//             type:      "ir.actions.act_window",
//             name:      "Asset",
//             res_model: "account.asset",
//             res_id:    assetId,
//             view_mode: "form",
//             views:     [[false, "form"]],
//         });
//     }

//     // ── Refresh ───────────────────────────────────────────────────────────────

//     async refresh() {
//         if (this._chart) { this._chart.destroy(); this._chart = null; }
//         await this._load();
//     }

//     // ── Format helpers (exposed to template) ─────────────────────────────────

//     fmt(n)    { return fmt(n); }
//     fmtInt(n) { return fmtInt(n); }
//     eventColor(type) { return EVENT_COLOR[type] || "#64748B"; }
//     stateMeta(s)     { return STATE_META[s] || STATE_META.draft; }
// }

// registry.category("actions").add(
//     "asset_management_bdcalling.AssetStatusDashboard",
//     AssetStatusDashboard
// );
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
    useExternalListener,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// ─── Palette & helpers ────────────────────────────────────────────────────────

const STATE_META = {
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

        this.donutRef        = useRef("donutCanvas");
        this.productInputRef = useRef("productSearchInput");
        this.assetInputRef   = useRef("assetSearchInput");
        this._chart          = null;
        this._searchTimer    = null;

        this.state = useState({
            loading:           true,
            error:             null,
            // ── filters ────────────────────────────────────────────────────
            productId:         null,
            productName:       "",
            assetId:           null,
            assetName:         "",
            // ── search UI ─────────────────────────────────────────────────
            productQuery:      "",
            assetQuery:        "",
            productResults:    [],
            assetResults:      [],
            showProductDrop:   false,
            showAssetDrop:     false,
            productSearching:  false,
            assetSearching:    false,
            // ── data ──────────────────────────────────────────────────────
            counts:            { available: 0, assigned: 0, scrapped: 0, disposed: 0 },
            total:             0,
            total_value:       0,
            net_book_value:    0,
            total_depreciated: 0,
            currency:          "",
            history:           [],
            cards:             { available: [], assigned: [], scrapped: [], disposed: [] },
            // ── ui ────────────────────────────────────────────────────────
            activeTab:         "overview",
            searchQuery:       "",
        });

        // Expose helpers to template
        this.STATE_META  = STATE_META;
        this.EVENT_COLOR = EVENT_COLOR;

        // Close dropdowns when clicking outside
        useExternalListener(document, "click", this._onDocumentClick.bind(this));

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

    // ── Product search ────────────────────────────────────────────────────────

    async onProductInput(ev) {
        const q = ev.target.value;
        this.state.productQuery = q;
        this.state.showProductDrop = true;

        if (this._searchTimer) clearTimeout(this._searchTimer);

        if (!q.trim()) {
            this.state.productResults = [];
            return;
        }

        this.state.productSearching = true;
        this._searchTimer = setTimeout(async () => {
            try {
                const results = await this.orm.searchRead(
                    "product.product",
                    [["is_asset", "=", true], ["name", "ilike", q]],
                    ["id", "name"],
                    { limit: 8 }
                );
                this.state.productResults   = results;
                this.state.productSearching = false;
            } catch {
                this.state.productSearching = false;
            }
        }, 250);
    }

    async onProductFocus() {
        this.state.showProductDrop = true;
        if (!this.state.productResults.length && !this.state.productQuery) {
            // Pre-load first few asset products
            const results = await this.orm.searchRead(
                "product.product",
                [["is_asset", "=", true]],
                ["id", "name"],
                { limit: 8 }
            );
            this.state.productResults = results;
        }
    }

    selectProduct(id, name) {
        this.state.productId       = id;
        this.state.productName     = name;
        this.state.productQuery    = name;
        this.state.showProductDrop = false;
        this.state.productResults  = [];
        // Reset asset filter when product changes
        this.clearAsset();
        this._load();
    }

    clearProduct() {
        this.state.productId       = null;
        this.state.productName     = "";
        this.state.productQuery    = "";
        this.state.productResults  = [];
        this.state.showProductDrop = false;
        this.clearAsset();
        this._load();
    }

    // ── Asset search ──────────────────────────────────────────────────────────

    async onAssetInput(ev) {
        const q = ev.target.value;
        this.state.assetQuery = q;
        this.state.showAssetDrop = true;

        if (this._searchTimer) clearTimeout(this._searchTimer);

        if (!q.trim()) {
            this.state.assetResults = [];
            return;
        }

        this.state.assetSearching = true;
        this._searchTimer = setTimeout(async () => {
            try {
                const domain = [
                    ["lot_id", "!=", false],
                    ["asset_state", "!=", "draft"],
                    "|",
                    ["name", "ilike", q],
                    ["code", "ilike", q],
                ];
                if (this.state.productId) {
                    domain.push(["product_id", "=", this.state.productId]);
                }
                const results = await this.orm.searchRead(
                    "account.asset",
                    domain,
                    ["id", "name", "code"],
                    { limit: 8 }
                );
                this.state.assetResults   = results;
                this.state.assetSearching = false;
            } catch {
                this.state.assetSearching = false;
            }
        }, 250);
    }

    async onAssetFocus() {
        this.state.showAssetDrop = true;
        if (!this.state.assetResults.length && !this.state.assetQuery) {
            // Pre-load first few registered assets
            const domain = [["lot_id", "!=", false], ["asset_state", "!=", "draft"]];
            if (this.state.productId) {
                domain.push(["product_id", "=", this.state.productId]);
            }
            const results = await this.orm.searchRead(
                "account.asset",
                domain,
                ["id", "name", "code"],
                { limit: 8 }
            );
            this.state.assetResults = results;
        }
    }

    selectAsset(id, name, code) {
        this.state.assetId       = id;
        this.state.assetName     = code ? `${code} — ${name}` : name;
        this.state.assetQuery    = this.state.assetName;
        this.state.showAssetDrop = false;
        this.state.assetResults  = [];
        this._load();
    }

    clearAsset() {
        this.state.assetId       = null;
        this.state.assetName     = "";
        this.state.assetQuery    = "";
        this.state.assetResults  = [];
        this.state.showAssetDrop = false;
        if (arguments.length === 0) {
            // Only reload if called standalone (not as part of clearProduct chain)
            this._load();
        }
    }

    // ── Close dropdowns on outside click ─────────────────────────────────────

    _onDocumentClick(ev) {
        const productWrap = this.el && this.el.querySelector(".asd-search-field-wrap[data-field='product']");
        const assetWrap   = this.el && this.el.querySelector(".asd-search-field-wrap[data-field='asset']");

        if (productWrap && !productWrap.contains(ev.target)) {
            this.state.showProductDrop = false;
            // Restore display name if a product is selected
            if (this.state.productId && !this.state.productQuery) {
                this.state.productQuery = this.state.productName;
            }
        }
        if (assetWrap && !assetWrap.contains(ev.target)) {
            this.state.showAssetDrop = false;
            if (this.state.assetId && !this.state.assetQuery) {
                this.state.assetQuery = this.state.assetName;
            }
        }
    }

    // ── Donut chart ───────────────────────────────────────────────────────────

    _drawDonut() {
        const canvas = this.donutRef.el;
        if (!canvas) return;
        const ChartJS = window.Chart;
        if (!ChartJS) return;

        const c  = this.state.counts;
        const labels = ["Available","Assigned","Scrapped","Disposed"];
        const values = [c.available, c.assigned, c.scrapped, c.disposed];
        const colors = ["#059669","#4F46E5","#E11D48","#D97706"];

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
        this.state.activeTab   = tab;
        this.state.searchQuery = "";
    }

    // ── Card filter / search ──────────────────────────────────────────────────

    get filteredCards() {
        const tab = this.state.activeTab;
        if (tab === "overview") return [];
        const q = (this.state.searchQuery || "").toLowerCase();
        const cards = this.state.cards[tab] || [];
        if (!q) return cards;
        return cards.filter(c =>
            (c.code     || "").toLowerCase().includes(q) ||
            (c.name     || "").toLowerCase().includes(q) ||
            (c.serial   || "").toLowerCase().includes(q) ||
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

    // ── Navigation ────────────────────────────────────────────────────────────

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