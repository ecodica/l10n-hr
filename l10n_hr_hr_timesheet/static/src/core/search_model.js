/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { SearchModel } from "@web/search/search_model";
import { patch } from "@web/core/utils/patch";

patch(SearchModel.prototype, {
    _getFacets() {
        const facets = super._getFacets();
        if (this.resModel == 'info3.timesheet') {
            for (const facet of facets) {
                if (facet.type === 'filter' && /date|employee_id|department_id/.test(facet.domain)) {
                    facet.class = 'hidden';
                }
            }
        }
        return facets;
    }
});
