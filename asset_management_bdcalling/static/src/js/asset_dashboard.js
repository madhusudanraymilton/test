/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AssetDashboard extends Component {

    static template = "asset_management_bdcalling.AssetDashboard";

    setup(){

        this.orm = useService("orm");
        this.action = useService("action");

        this.chart = null;

        this.state = useState({
            loading: true,

            total: 0,
            available: 0,
            assigned: 0,
            scrapped_disposed: 0,

            by_category: [],
            recent_assignments: []
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });

        onMounted(() => {
            this.renderChart();
        });
    }


    async loadDashboard(){

        const data = await this.orm.call(
            "asset.asset",
            "get_dashboard_data",
            []
        );

        Object.assign(this.state, data);
        this.state.loading = false;
    }


    renderChart(){

        if (!this.state.by_category.length){
            return;
        }

        const labels = this.state.by_category.map(x => x.category);
        const values = this.state.by_category.map(x => x.count);

        const ctx = document.getElementById("categoryChart");

        if (!ctx){
            return;
        }

        // destroy previous chart
        if (this.chart){
            this.chart.destroy();
        }

        this.chart = new Chart(ctx,{
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Assets",
                    data: values,
                    backgroundColor: "#3b82f6"
                }]
            },
            options:{
                responsive:true,
                maintainAspectRatio:false
            }
        });
    }


    async openAllAssets(){

        await this.action.doAction({
            type:"ir.actions.act_window",
            name:"Assets",
            res_model:"asset.asset",
            view_mode:"list,form"
        });

    }


    async openAvailableAssets(){

        await this.action.doAction({
            type:"ir.actions.act_window",
            name:"Available Assets",
            res_model:"asset.asset",
            view_mode:"list,form",
            domain:[["state","=","available"]]
        });

    }


    async openAssignedAssets(){

        await this.action.doAction({
            type:"ir.actions.act_window",
            name:"Assigned Assets",
            res_model:"asset.asset",
            view_mode:"list,form",
            domain:[["state","=","assigned"]]
        });

    }


    async refresh(){

        this.state.loading = true;

        await this.loadDashboard();

        this.renderChart();

    }

}

registry.category("actions").add(
    "asset_management_bdcalling.AssetDashboard",
    AssetDashboard
);