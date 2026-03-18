from odoo import models, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _distribute_delta_amount_smoothly(self, precision_digits, delta_amount, target_factors):
        ''' We have added this config paramater to temporarily fix rounding errors on invoices,
        causing differences on printing and failing FINA checks.
        https://github.com/odoo/odoo/issues/250035 - Follow this issue for possible fixes. '''
        skip_delta_distribution = bool(self.env['ir.config_parameter'].sudo().get_param('skip_distribute_delta_amount_smoothly'))

        if skip_delta_distribution:
            return [0.0] * len(target_factors)

        return super()._distribute_delta_amount_smoothly(precision_digits, delta_amount, target_factors)
