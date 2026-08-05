/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class VacLeadStageButtons extends Component {
    static template = "vac_events.VacLeadStageButtons";
    
    // FIXED: Include all standard field props (including 'id')
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
    }

    /**
     * Parse and return stage data from the field
     */
    getStageData() {
        // Access the field value correctly
        const stageDataStr = this.props.record.data[this.props.name];
        
        console.log("Stage Data String:", stageDataStr); // Debug log
        
        if (!stageDataStr) {
            console.warn("No stage data available");
            return [];
        }
        
        try {
            const data = JSON.parse(stageDataStr);
            console.log("Parsed Stage Data:", data); // Debug log
            return Array.isArray(data) ? data : [];
        } catch (e) {
            console.error("Error parsing stage data:", e);
            return [];
        }
    }

    /**
     * Get icon based on stage sequence
     */
    getStageIcon(sequence) {
        const icons = {
            0: 'fa-user-plus',      // New Lead
            10: 'fa-user-plus',     // New Lead
            1: 'fa-phone',          // Contacted
            20: 'fa-phone',         // Follow-up
            2: 'fa-refresh',        // In Progress
            3: 'fa-check-circle',   // Qualified
            30: 'fa-check-circle',  // Converted
            4: 'fa-times-circle',   // Lost
            40: 'fa-times-circle',  // Lost
        };
        return icons[sequence] || 'fa-star';
    }

    /**
     * Open leads filtered by stage
     */
    async openLeadsByStage(stageId, stageName) {
        const recordId = this.props.record.resId;
        const eventTitle = this.props.record.data.title_name || 'Event';
        
        console.log("Opening leads for stage:", stageId, stageName); // Debug log
        
        if (!recordId) {
            console.warn("No record ID available");
            return;
        }
        
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'vac.event.lead',
            name: `${stageName} - ${eventTitle}`,
            view_mode: 'kanban,tree,form',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            domain: [
                ['event_id', '=', recordId],
                ['stage_id', '=', stageId]
            ],
            context: {
                default_event_id: recordId,
                default_stage_id: stageId,
            },
        });
    }
}

// Register the field widget
registry.category("fields").add("vac_lead_stage_buttons", {
    component: VacLeadStageButtons,
    supportedTypes: ["text"],
});