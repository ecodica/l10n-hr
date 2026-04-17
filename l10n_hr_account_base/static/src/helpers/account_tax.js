import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { session } from "@web/session";

patch(accountTaxHelpers, {
    distribute_delta_amount_smoothly(precision_digits, delta_amount, target_factors) {
        // Same as on .py of this method - override until it is fixed by odoo
        const skipSmooth = session.skip_distribute_delta_amount_smoothly;

        if (skipSmooth) {
            return target_factors.map(() => 0.0);
        }

        return super.distribute_delta_amount_smoothly(...arguments);
    },
});
