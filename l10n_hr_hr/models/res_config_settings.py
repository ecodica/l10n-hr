from odoo import fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hr_config_employee_display_name = fields.Selection(
        related='company_id.hr_config_employee_display_name', default='first_name_first', readonly=False,
        help="Setup employee display name")
    hr_config_hr_contract_wage_visible = fields.Boolean(related='company_id.hr_config_hr_contract_wage_visible',
        help='Wage visible in HR Contract Form',
        default=False, readonly=False)
    hr_config_display_employee_code_in_name = fields.Boolean(related='company_id.hr_config_display_employee_code_in_name',
        help="Display employee code in name",
        default=False, readonly=False)
    hr_config_manually_input_employee_code = fields.Boolean(related='company_id.hr_config_manually_input_employee_code',
        help="Instead of being genrated by a seqeunce, manually input employee code",
        default=False, readonly=False)
