/** @odoo-module */

import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class LibraryDashboard extends Component {
    static template = "library_management.LibraryDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.dashboardData = {
            totalBooks: 0,
            availableBooks: 0,
            issuedBooks: 0,
            totalMembers: 0,
            overdueBooks: 0,
            unpaidFines: 0
        };

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            // Get total books
            this.dashboardData.totalBooks = await this.orm.searchCount("library.book", []);

            // Get available books
            this.dashboardData.availableBooks = await this.orm.searchCount("library.book", [
                ["available_copies", ">", 0]
            ]);

            // Get issued books (active borrowings)
            this.dashboardData.issuedBooks = await this.orm.searchCount("library.borrowing", [
                ["status", "=", "borrowed"]
            ]);

            // Get total members
            this.dashboardData.totalMembers = await this.orm.searchCount("library.member", []);

            // Get overdue books
            this.dashboardData.overdueBooks = await this.orm.searchCount("library.borrowing", [
                ["status", "=", "overdue"]
            ]);

            // Get unpaid fines count
            this.dashboardData.unpaidFines = await this.orm.searchCount("library.fine", [
                ["payment_status", "=", "unpaid"]
            ]);

        } catch (error) {
            console.error("Error loading dashboard data:", error);
        }
    }

    // Action handlers
    openBooks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.book",
            views: [[false, "list"], [false, "form"]],
            domain: [],
        });
    }

    openAvailableBooks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.book",
            views: [[false, "list"], [false, "form"]],
            domain: [["available_copies", ">", 0]],
        });
    }

    openIssuedBooks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.borrowing",
            views: [[false, "list"], [false, "form"]],
            domain: [["status", "=", "borrowed"]],
        });
    }

    openMembers() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.member",
            views: [[false, "list"], [false, "form"]],
            domain: [],
        });
    }

    openOverdueBooks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.borrowing",
            views: [[false, "list"], [false, "form"]],
            domain: [["status", "=", "overdue"]],
        });
    }

    openUnpaidFines() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.fine",
            views: [[false, "list"], [false, "form"]],
            domain: [["payment_status", "=", "unpaid"]],
        });
    }
}

registry.category("actions").add("library_dashboard", LibraryDashboard);