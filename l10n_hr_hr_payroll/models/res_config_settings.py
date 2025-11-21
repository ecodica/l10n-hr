from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    i3_config_max_apprenticeship_amount = fields.Float(
        related='company_id.i3_config_max_apprenticeship_amount', readonly=False)
    i3_config_max_scholarship_amount = fields.Float(
        related='company_id.i3_config_max_scholarship_amount', readonly=False)
    i3_config_max_child_birth_fee = fields.Float(related='company_id.i3_config_max_child_birth_fee', readonly=False)
    i3_config_taxless_bonus_amount = fields.Float(
        related='company_id.i3_config_taxless_bonus_amount', readonly=False)
    i3_config_max_taxless_reward_amount = fields.Float(
        related='company_id.i3_config_max_taxless_reward_amount', readonly=False)
    i3_config_max_undocumented_lunch_fee_amount = fields.Float(
        related='company_id.i3_config_max_undocumented_lunch_fee_amount', readonly=False)
    i3_config_max_documented_lunch_fee_amount = fields.Float(
        related='company_id.i3_config_max_documented_lunch_fee_amount', readonly=False)
    i3_config_max_vacation_amount = fields.Float(
        related='company_id.i3_config_max_vacation_amount', readonly=False)
    i3_config_max_remote_work_fee_amount = fields.Float(
        related='company_id.i3_config_max_remote_work_fee_amount', readonly=False)
    i3_config_max_supplementary_insurance = fields.Float(
        related='company_id.i3_config_max_supplementary_insurance', readonly=False)
    i3_config_average_wage = fields.Float(
        related='company_id.i3_config_average_wage', readonly=False)
    i3_config_minimal_wage = fields.Float(related='company_id.i3_config_minimal_wage', readonly=False)
    i3_config_min_contributions_base = fields.Float(
        related='company_id.i3_config_min_contributions_base', readonly=False)
    i3_config_min_contributions_base_directors = fields.Float(
        related='company_id.i3_config_min_contributions_base_directors', readonly=False)
    i3_config_max_contributions_base = fields.Float(
        related='company_id.i3_config_max_contributions_base', readonly=False)
    i3_config_disability_fee_percentage = fields.Float(
        related='company_id.i3_config_disability_fee_percentage', readonly=False)
    i3_config_disability_quota_percentage = fields.Float(
        related='company_id.i3_config_disability_quota_percentage', readonly=False)
    i3_config_osnovica = fields.Float(related='company_id.i3_config_osnovica', readonly=False)
    i3_config_osnovica_uzdrzavani = fields.Float(related='company_id.i3_config_osnovica_uzdrzavani', readonly=False)
    i3_config_razred_1 = fields.Float(related='company_id.i3_config_razred_1', readonly=False)
    i3_config_razred_1_posto = fields.Float(related='company_id.i3_config_razred_1_posto', readonly=False)
    i3_config_razred_2_posto = fields.Float(related='company_id.i3_config_razred_2_posto', readonly=False)
    i3_config_capital_gain_1_pct = fields.Float(related='company_id.i3_config_capital_gain_1_pct', readonly=False)
    i3_config_min_sick_leave_fee_net = fields.Float(
        related='company_id.i3_config_min_sick_leave_fee_net', readonly=False)
    i3_config_max_sick_leave_fee_net = fields.Float(
        related='company_id.i3_config_max_sick_leave_fee_net', readonly=False)
    i3_config_batch_booking = fields.Boolean(related='company_id.i3_config_batch_booking', readonly=False)
    i3_config_use_end_to_end = fields.Boolean(related='company_id.i3_config_use_end_to_end', readonly=False)
    i3_config_sepa_pain_type = fields.Selection(related='company_id.i3_config_sepa_pain_type', readonly=False)
    i3_config_sick_hours_travel = fields.Boolean(related='company_id.i3_config_sick_hours_travel', readonly=False)
    i3_config_payslip_transport_amount_manual_input = fields.Boolean(
        related='company_id.i3_config_payslip_transport_amount_manual_input', readonly=False)
    i3_config_print_work_exp_on_payslip = fields.Boolean(
        related='company_id.i3_config_print_work_exp_on_payslip', readonly=False)
    i3_config_show_nonpaid_salary_options = fields.Boolean(
        related='company_id.i3_config_show_nonpaid_salary_options', readonly=False)
    i3_config_send_contract_expiration = fields.Boolean(
        related='company_id.i3_config_send_contract_expiration', readonly=False)
    i3_config_send_contract_expiration_time = fields.Float(
        related='company_id.i3_config_send_contract_expiration_time', readonly=False)
    i3_config_account_credit_disability = fields.Many2one(
        'account.account', related='company_id.i3_config_account_credit_disability', readonly=False)
    i3_config_account_debit_disability = fields.Many2one(
        'account.account', related='company_id.i3_config_account_debit_disability', readonly=False)
    i3_config_disability_fee_min_number_of_employees = fields.Integer(
        readonly=False, related='company_id.i3_config_disability_fee_min_number_of_employees')
    i3_config_sick_leave_number_of_months = fields.Integer(
        readonly=False,related='company_id.i3_config_sick_leave_number_of_months')
    i3_config_sick_leave_company_percentage = fields.Float(
        readonly=False, related='company_id.i3_config_sick_leave_company_percentage')
    i3_config_disability_fee_crediting = fields.Boolean(
        related='company_id.i3_config_disability_fee_crediting', readonly=False)
    i3_config_health_insurance_contribution_pct = fields.Float(
        related='company_id.i3_config_health_insurance_contribution_pct', readonly=False)
    i3_config_health_insurance_contribution_pct_additional_income = fields.Float(
        related='company_id.i3_config_health_insurance_contribution_pct_additional_income', readonly=False)
    i3_config_calculate_salary_by_coefficient = fields.Boolean(
        related='company_id.i3_config_calculate_salary_by_coefficient', readonly=False)
    i3_config_base_salary = fields.Float(related='company_id.i3_config_base_salary', readonly=False)
    i3_config_use_avg_hourly_wage_for_annual_leave_calculation = fields.Boolean(
        related='company_id.i3_config_use_avg_hourly_wage_for_annual_leave_calculation', readonly=False)
    i3_config_annual_leave_wage_number_of_months = fields.Integer(
        related='company_id.i3_config_annual_leave_wage_number_of_months', readonly=False)
    i3_config_analytic_distribution_account_type_ids = fields.Many2many(
        related='company_id.i3_config_analytic_distribution_account_type_ids', readonly=False)
    hr_config_send_payslips_by_email = fields.Boolean(
        related='company_id.hr_config_send_payslips_by_email', readonly=False)
    hr_config_print_brutto2_on_payslip = fields.Boolean(
        related='company_id.hr_config_print_brutto2_on_payslip', readonly=False)
    hr_config_print_nonpaid_netto_fees_on_payslip_report = fields.Boolean(
        related='company_id.hr_config_print_nonpaid_netto_fees_on_payslip_report', readonly=False)
    hr_config_contributions_base_deduction_limit_1 = fields.Float(
        related='company_id.hr_config_contributions_base_deduction_limit_1', readonly=False)
    hr_config_contributions_base_deduction_limit_2 = fields.Float(
        related='company_id.hr_config_contributions_base_deduction_limit_2', readonly=False)
    hr_config_contributions_base_deduction_fixed_amount = fields.Float(
        related='company_id.hr_config_contributions_base_deduction_fixed_amount', readonly=False)
    i3_config_min_sickleave_min_base = fields.Float(
        default=474.24, related='company_id.i3_config_min_sickleave_min_base', readonly=False)
    hr_config_sick_leave_company_calc_method = fields.Selection(
        related='company_id.hr_config_sick_leave_company_calc_method', readonly=False)
    i3_config_max_annual_leave = fields.Float(related='company_id.i3_config_max_annual_leave', readonly=False)

    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Radno vrijeme tvrtke',
        related='company_id.resource_calendar_id', readonly=False)
    module_hr_org_chart = fields.Boolean(string="Prikaži organizacijski dijagram")

    i3_config_calculate_experiance_allowance = fields.Selection([('internal_experience','Staž kod poslodavca'),('total_experience','Ukupan staž')], default="internal_experience", config_parameter='l10n_hr_hr_payroll.i3_config_calculate_experiance_allowance')

    def i3_config_send_contract_expiration_email(self):
        # self.env["hr.contract"].send_contract_expiration()
        return True

    def set_l10n_hr_payroll_defaults(self):
        #write only on current company on Reload button click
        company = self.company_id
        res = company.write(company.return_config_params())
        return res
