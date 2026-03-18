/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillUnmount} from "@odoo/owl";
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { _t } from "@web/core/l10n/translation";

export class NotFiscalizedInvoicesSystray extends Component {
   setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.state = useState({
            counterInvoice: 0,
            counterTotal: 0
        });
        this.orm = useService("orm");
        this.isAlive = true;
        this.intervalInvoice = setInterval(() => {
            this.fetchCounter();
        }, 5000);
        onWillUnmount(() => {
            this.isAlive = false;
            clearInterval(this.intervalInvoice);
        });
   }

   _openNotFiscalizedInvoices() {
        const domain = [
            ['l10n_hr_zki', '!=', false],
            ['l10n_hr_jir', '=', false],
            ['state', '=', 'posted']
        ];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Not Fiscalized Invoices"),
            res_model: "account.move",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: domain,
        });
    }

    async fetchCounter() {
        const company_id = this.env.services.company.currentCompany.id
        const { count } = await this.orm.call(
            "account.move",
            "search_not_fiscalized_invoice_count",
            [],
            {company_id}
        );
        if (!this.isAlive) return;
        if(this.state.counterInvoice != count){
            this.state.counterTotal -= (this.state.counterInvoice-count)
            this.state.counterInvoice = count;
        }
    }

}
   NotFiscalizedInvoicesSystray.template = "not_fiscalized_invoices_systray";
   NotFiscalizedInvoicesSystray.components = {Dropdown, DropdownItem };
   export const systrayItem = { Component: NotFiscalizedInvoicesSystray,};
   registry.category("systray").add("NotFiscalizedInvoicesSystray", systrayItem, { sequence: 200 });
