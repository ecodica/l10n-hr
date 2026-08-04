/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillUnmount, status } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

const REFRESH_INTERVAL = 5 * 60 * 1000;

export class NotFiscalizedInvoicesSystray extends Component {
    static template = "not_fiscalized_invoices_systray";
    static components = { Dropdown, DropdownItem };
    static props = {};

    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.orm = useService("orm");
        this.hasAccess = false;
        this.state = useState({
            counterInvoice: 0,
            counterTotal: 0,
        });
        onWillStart(async () => {
            // Users without invoicing rights make no RPC and render nothing.
            this.hasAccess = await user.hasGroup("account.group_account_invoice");
            await this.fetchCounter();
        });
        this.intervalInvoice = setInterval(() => {
            this.fetchCounter();
        }, REFRESH_INTERVAL);
        onWillUnmount(() => {
            clearInterval(this.intervalInvoice);
        });
    }

    _openNotFiscalizedInvoices() {
        const domain = [
            ["l10n_hr_zki", "!=", false],
            ["l10n_hr_jir", "=", false],
            ["state", "=", "posted"],
        ];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Not Fiscalized Invoces"),
            res_model: "account.move",
            view_mode: "tree,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
            domain: domain,
        });
    }

    async fetchCounter() {
        if (!this.hasAccess || status(this) === "destroyed") return;
        if (document.visibilityState !== "visible") return;
        try {
            const { count } = await this.orm.call(
                "account.move",
                "search_not_fiscalized_invoice_count",
                []
            );
            if (status(this) === "destroyed") return;
            if (this.state.counterInvoice != count) {
                this.state.counterTotal -= this.state.counterInvoice - count;
                this.state.counterInvoice = count;
            }
        } catch {
            // Component may have been destroyed while awaiting the ORM call
        }
    }
}

export const systrayItem = { Component: NotFiscalizedInvoicesSystray };
registry.category("systray").add("NotFiscalizedInvoicesSystray", systrayItem, { sequence: 200 });
