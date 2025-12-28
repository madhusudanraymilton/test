import { Component, onWillStart, useState } from '@odoo/owl';
import { useService } from "@web/core/utils/hooks";

export class CustomDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            stats: {
                totalBooks: 0,
                availableBooks: 0,
                borrowedBooks: 0,
                totalMembers: 0,
                activeMembers: 0,
                overdueBooks: 0,
                unpaidFines: 0,
                totalFineAmount: 0,
                todayBorrowings: 0,
                dueTodayBooks: 0,
            },
            topBooks: [],
            recentBorrowings: [],
            categoryDistribution: [],
            membershipDistribution: [],
            monthlyTrends: [],
            loading: true,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            await Promise.all([
                this.loadStatistics(),
                this.loadTopBooks(),
                this.loadRecentBorrowings(),
                this.loadCategoryDistribution(),
                this.loadMembershipDistribution(),
                this.loadMonthlyTrends(),
            ]);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async loadStatistics() {
        const today = new Date().toISOString().split('T')[0];

        // Total Books
        this.state.stats.totalBooks = await this.orm.searchCount("library.book", []);

        // Available Books
        this.state.stats.availableBooks = await this.orm.searchCount("library.book", [
            ["available_copies", ">", 0],
            ["state", "=", "available"]
        ]);

        // Borrowed Books
        this.state.stats.borrowedBooks = await this.orm.searchCount("library.borrowing", [
            ["status", "=", "borrowed"]
        ]);

        // Total Members
        this.state.stats.totalMembers = await this.orm.searchCount("library.member", [
            ["active", "=", true]
        ]);

        // Active Members (with current borrowings)
        this.state.stats.activeMembers = await this.orm.searchCount("library.member", [
            ["active_borrowings", ">", 0]
        ]);

        // Overdue Books
        this.state.stats.overdueBooks = await this.orm.searchCount("library.borrowing", [
            ["status", "=", "overdue"]
        ]);

        // Unpaid Fines Count
        this.state.stats.unpaidFines = await this.orm.searchCount("library.fine", [
            ["payment_status", "=", "unpaid"]
        ]);

        // Total Unpaid Fine Amount
        const fines = await this.orm.searchRead(
            "library.fine",
            [["payment_status", "=", "unpaid"]],
            ["fine_amount"]
        );
        this.state.stats.totalFineAmount = fines.reduce((sum, f) => sum + f.fine_amount, 0);

        // Today's Borrowings
        this.state.stats.todayBorrowings = await this.orm.searchCount("library.borrowing", [
            ["borrow_date", "=", today]
        ]);

        // Books Due Today
        this.state.stats.dueTodayBooks = await this.orm.searchCount("library.borrowing", [
            ["due_date", "=", today],
            ["status", "=", "borrowed"]
        ]);
    }

    async loadTopBooks() {
        const borrowings = await this.orm.readGroup(
            "library.borrowing",
            [["status", "in", ["borrowed", "returned"]]],
            ["book_id"],
            ["book_id"],
            { limit: 5, orderby: "book_id_count DESC" }
        );

        const bookIds = borrowings.map(b => b.book_id[0]);
        if (bookIds.length > 0) {
            const books = await this.orm.searchRead(
                "library.book",
                [["id", "in", bookIds]],
                ["id", "title", "isbn"]
            );

            this.state.topBooks = borrowings.map(b => {
                const book = books.find(bk => bk.id === b.book_id[0]);
                return {
                    id: b.book_id[0],
                    title: book ? book.title : "Unknown",
                    count: b.book_id_count,
                };
            });
        }
    }

    async loadRecentBorrowings() {
        this.state.recentBorrowings = await this.orm.searchRead(
            "library.borrowing",
            [],
            ["id", "name", "member_id", "book_id", "borrow_date", "due_date", "status"],
            { limit: 5, order: "borrow_date DESC" }
        );
    }

    async loadCategoryDistribution() {
        const books = await this.orm.searchRead(
            "library.book",
            [["category_ids", "!=", false]],
            ["category_ids"]
        );

        const categoryCount = {};
        for (const book of books) {
            for (const catId of book.category_ids) {
                categoryCount[catId] = (categoryCount[catId] || 0) + 1;
            }
        }

        const categoryIds = Object.keys(categoryCount).map(id => parseInt(id));
        if (categoryIds.length > 0) {
            const categories = await this.orm.searchRead(
                "library.category",
                [["id", "in", categoryIds]],
                ["id", "name"]
            );

            this.state.categoryDistribution = categories
                .map(cat => ({
                    name: cat.name,
                    count: categoryCount[cat.id],
                }))
                .sort((a, b) => b.count - a.count)
                .slice(0, 6);
        }
    }

    async loadMembershipDistribution() {
        const groups = await this.orm.readGroup(
            "library.member",
            [["active", "=", true]],
            ["membership_type"],
            ["membership_type"]
        );

        this.state.membershipDistribution = groups.map(g => ({
            type: g.membership_type,
            count: g.membership_type_count,
        }));
    }

    async loadMonthlyTrends() {
        const groups = await this.orm.readGroup(
            "library.borrowing",
            [],
            ["borrow_date"],
            ["borrow_date:month"],
            { limit: 6, orderby: "borrow_date:month DESC" }
        );

        this.state.monthlyTrends = groups.reverse().map(g => ({
            month: g["borrow_date:month"],
            count: g.borrow_date_count,
        }));
    }

    // Action Handlers
    openBooks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.book",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [],
        });
    }

    openAvailableBooks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.book",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["available_copies", ">", 0], ["state", "=", "available"]],
        });
    }

    openBorrowedBooks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.borrowing",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["status", "=", "borrowed"]],
        });
    }

    openMembers() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.member",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["active", "=", true]],
        });
    }

    openActiveMembers() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.member",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["active_borrowings", ">", 0]],
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

    openTodayBorrowings() {
        const today = new Date().toISOString().split('T')[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.borrowing",
            views: [[false, "list"], [false, "form"]],
            domain: [["borrow_date", "=", today]],
        });
    }

    openDueTodayBooks() {
        const today = new Date().toISOString().split('T')[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.borrowing",
            views: [[false, "list"], [false, "form"]],
            domain: [["due_date", "=", today], ["status", "=", "borrowed"]],
        });
    }

    openBook(bookId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.book",
            res_id: bookId,
            views: [[false, "form"]],
        });
    }

    openBorrowing(borrowingId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.borrowing",
            res_id: borrowingId,
            views: [[false, "form"]],
        });
    }

    getStatusBadgeClass(status) {
        const classes = {
            draft: "badge-secondary",
            borrowed: "badge-primary",
            overdue: "badge-danger",
            returned: "badge-success",
        };
        return classes[status] || "badge-secondary";
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString();
    }

    formatCurrency(amount) {
        return `৳${amount.toFixed(2)}`;
    }
}
CustomDashboard.template = 'library_management.CustomDashboard';

