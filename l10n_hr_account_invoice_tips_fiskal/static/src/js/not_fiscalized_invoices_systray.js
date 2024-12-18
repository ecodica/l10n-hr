/** @odoo-module **/
import { NotFiscalizedInvoicesSystray } from "@l10n_hr_account_fiskal/js/not_fiscalized_invoices_systray";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(NotFiscalizedInvoicesSystray.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.state.counterTips = 0;
        this.fetchTipsCounter();
        this.interval = setInterval(() => {
            this.fetchTipsCounter();
        }, 5000);
    },

    _openNotFiscalizedTips() {
        const domain = [
            ['l10n_hr_zki', '!=', false],
            ['l10n_hr_jir', '!=', false],
            ['l10n_hr_napojnica_iznos', '>', 0],
            ['l10n_hr_napojnica_is_fiscalized', '!=', true],
        ];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Not Fiscalized Tips"),
            res_model: "account.move",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: domain,
        });
    },

    async fetchTipsCounter() {
        const company_id = this.env.services.company.currentCompany.id
        const { count } = await this.orm.call(
            "account.move",
            "search_not_fiscalized_tips_count",
            [],
            {company_id}
        );
        if(this.state.counterTips != count){
            this.state.counterTotal = this.state.counterInvoice + count
            this.state.counterTips = count;
        }
    }
})
