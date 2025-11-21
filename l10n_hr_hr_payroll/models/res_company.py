# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = "res.company"


    i3_config_max_child_birth_fee = fields.Float('Maksimalni iznos naknade za rođenje djeteta')
    i3_config_taxless_bonus_amount = fields.Float('PN22 - Prigodne nagrade')
    i3_config_max_taxless_reward_amount = fields.Float('NAG - Nagrade za radne rezultate')
    i3_config_max_undocumented_lunch_fee_amount = fields.Float('Pausalna naknada za prehranu')
    i3_config_max_documented_lunch_fee_amount = fields.Float('Naknada za prehranu na temelju dokumentacije')
    i3_config_max_vacation_amount = fields.Float('ODM - Odmor radnika')
    i3_config_max_remote_work_fee_amount = fields.Float('RADIZDVMJ - mjesečna naknada za rad na izdvojenom mjestu')
    i3_config_max_supplementary_insurance = fields.Float('PREMZDROSIG - Premije dodatnog i dopunskog zdravstvenog osiguranja')
    i3_config_average_wage = fields.Float('Prosječna plaća za izračun obustava')
    i3_config_minimal_wage = fields.Float('Minimalna plaća')
    i3_config_min_contributions_base = fields.Float('Minimalna mjesečna osnovica za doprinose')
    i3_config_min_contributions_base_directors = fields.Float('Minimalna mjesečna osnovica za doprinose za članove uprave')
    i3_config_max_contributions_base = fields.Float('Maksimalna mjesečna osnovica za doprinose')
    i3_config_disability_fee_percentage = fields.Float('Udio minimalne plaće za izračun naknade')
    i3_config_disability_quota_percentage = fields.Float('Potrebna kvota zaposlenih OSI (%)')
    i3_config_osnovica = fields.Float('Osnovica osobnog odbitka')
    i3_config_osnovica_uzdrzavani = fields.Float('Osnovica za uzdržavane članove i djecu')
    i3_config_razred_1 = fields.Float('Raspon prvog poreznog razreda')
    i3_config_razred_1_posto = fields.Float('Postotak poreza za 1. porezni razred')
    i3_config_razred_2_posto = fields.Float('Postotak poreza za 2. porezni razred')
    i3_config_capital_gain_1_pct = fields.Float('Postotak za 1. razred poreza na dohodak od kapitala', help='Koristi se za isplatu dobiti kroz obračun plaće')
    i3_config_min_sick_leave_fee_net = fields.Float('Minimalni neto iznos naknade za bolovanje')
    i3_config_max_sick_leave_fee_net = fields.Float('Maksimalni neto iznos naknade za bolovanje')
    i3_config_batch_booking = fields.Boolean('Koristi batch booking za SEPA')
    i3_config_use_end_to_end = fields.Boolean('Nemoj koristiti end to end za SEPA')
    _sepa_pain_type_sel = [
        ('pain.001.001.03', 'pain.001.001.03'),
        ('pain.001.001.09', 'pain.001.001.09'),
    ]
    i3_config_sepa_pain_type = fields.Selection(_sepa_pain_type_sel, 'SEPA Pain format')
    i3_config_sick_hours_travel = fields.Boolean('Nemoj uračunati bolovanje za putne troškove')
    i3_config_payslip_transport_amount_manual_input = fields.Boolean('Ručni unos na isplatnom listiću')
    i3_config_print_work_exp_on_payslip = fields.Boolean('Ispiši staž na listić')
    i3_config_show_nonpaid_salary_options = fields.Boolean('Prikaži opcije za neisplaćenu plaću', help='Koristi se za prikazivanje ili sakrivanje opcije za neisplaćenu plaću na formi obračuna i JOPPD-u, te tipki za NP1 i ZPN1 na listiću i obračunu.')
    i3_config_send_contract_expiration = fields.Boolean('Šalji mail o ugovorima u isteku')
    i3_config_send_contract_expiration_time = fields.Float('Broj dana prije isteka ugovora')
    i3_config_account_credit_disability = fields.Many2one('account.account', 'Potražni konto')
    i3_config_account_debit_disability = fields.Many2one('account.account', 'Dugovni konto')
    i3_config_disability_fee_min_number_of_employees = fields.Integer('Minimalni broj zaposlenika')
    i3_config_sick_leave_number_of_months = fields.Integer('Broj mjeseci za izračun prosječne satnice za bolovanje')
    i3_config_sick_leave_company_percentage = fields.Float('Postotak za izračun bolovanja na teret poslodavca')
    i3_config_disability_fee_crediting = fields.Boolean('Knjiži naknadu za OSI')
    i3_config_health_insurance_contribution_pct = fields.Float('Doprinos za zdravstveno osiguranje (%)')
    i3_config_health_insurance_contribution_pct_additional_income = fields.Float('Doprinos za zdravstveno osiguranje - drugi dohodak (%)')
    i3_config_use_avg_hourly_wage_for_annual_leave_calculation = fields.Boolean('Računaj godišnji odmor prema satnici')
    i3_config_annual_leave_wage_number_of_months = fields.Integer('Broj mjeseci za izračun prosječne satnice za godišnji')
    i3_config_analytic_distribution_account_type_ids = fields.Many2many('account.account', 'company_account_account_rel', 'company_id', 'account_type_id',
                                                                string='Vrste konta za analitičku raspodjelu')
    hr_config_send_payslips_by_email = fields.Boolean('Šalji platne liste mailom')
    hr_config_print_brutto2_on_payslip = fields.Boolean('Ispiši ukupni trošak plaće na listić')
    hr_config_print_nonpaid_netto_fees_on_payslip_report = fields.Boolean('Ispiši neto naknade bez isplate na isplatni listić')

    hr_config_contributions_base_deduction_limit_1 = fields.Float(
        'Donja granica za umanjenje osnovice za doprinose',
        help='Donja granica bruto plaće za primjenu umanjenja osnovice za doprinose.\n'\
'Ako je plaća zaposlenika niža od donje granice, osnovica se umanjuje za fiksni iznos.')

    hr_config_contributions_base_deduction_limit_2 = fields.Float(
        'Gornja granica za umanjenje osnovice za doprinose',
        help='Gornja granica bruto plaće za primjenu umanjenja osnovice za doprinose.\n'\
'Ako je plaća zaposlenika viša od gornje granice, nema umanjenja osnovice.')
    
    hr_config_contributions_base_deduction_fixed_amount = fields.Float(
        'Fiksni iznos umanjenja osnovice za doprinose',
        help='Ako je plaća zaposlenika niža od donje granice za umanjenje osnovice za doprinose, onda je ovo iznos za koji se osnovica umanjuje.')

    i3_config_min_sickleave_min_base = fields.Float('Minimum monthly base for sick leave when there is no two salaries average', default=474.24)

    resource_calendar_ids = fields.One2many(
        'resource.calendar', 'company_id', 'Radni sati')
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Zadani radni sati', ondelete='restrict')

    i3_config_max_apprenticeship_amount = fields.Float('PRAKSA - naknade učenicima', help="Najveći dozvoljeni iznos naknada učenicima za vrijeme naukovanja i praktičnog rada")
    i3_config_base_salary = fields.Float('Osnovica za plaću')
    i3_config_max_scholarship_amount = fields.Float('SKOL - Stipendije i potpora djetetu', help="Najveći dozvoljeni iznos stipendija i potpora djetetu do 15. godine života")
    i3_config_calculate_salary_by_coefficient = fields.Boolean('Izračun plaće na temelju koeficijenta')
    hr_config_sick_leave_company_calc_method = fields.Selection([
    ('average_hourly_wage', 'Prosječna satnica'),
    ('contract_hourly_wage', 'Ugovorena satnica'),
    ('contract_salary', 'Ugovorena plaća')], 
    'Bolovanje - Način izračuna'
    )
    i3_config_max_annual_leave = fields.Float('Maksimalna količina godišnjeg odmora')


    def set_defaults_on_install(self):
        #write defaults on all companies when installing payroll   
        for company in self:
            company.write(self.return_config_params())
        return True

    def return_config_params(self):
        return {
            'i3_config_max_apprenticeship_amount': 3600.00,
            'i3_config_base_salary': 0.00,
            'i3_config_max_scholarship_amount': 7200.00,
            'i3_config_calculate_salary_by_coefficient': True,
            'i3_config_max_child_birth_fee': 1500,
            'i3_config_taxless_bonus_amount': 700,
            'i3_config_max_taxless_reward_amount': 1200,
            'i3_config_max_undocumented_lunch_fee_amount': 1200,
            'i3_config_max_documented_lunch_fee_amount': 1800,
            'i3_config_max_vacation_amount': 400,
            'i3_config_max_remote_work_fee_amount': 70,
            'i3_config_max_supplementary_insurance': 500,
            'i3_config_average_wage': 1302,
            'i3_config_minimal_wage': 970,
            'i3_config_min_contributions_base': 683.24,
            'i3_config_min_contributions_base_directors': 1168.70,
            'i3_config_max_contributions_base': 10788,
            'i3_config_disability_fee_percentage': 20,
            'i3_config_disability_quota_percentage': 3,
            'i3_config_osnovica': 600,
            'i3_config_osnovica_uzdrzavani': 600,
            'i3_config_razred_1': 60000,
            'i3_config_razred_1_posto': 20,
            'i3_config_razred_2_posto': 30,
            'i3_config_capital_gain_1_pct': 12,
            'i3_config_min_sick_leave_fee_net': 353.15,
            'i3_config_max_sick_leave_fee_net': 995.45,
            'i3_config_batch_booking': True,
            'i3_config_use_end_to_end': False,
            'i3_config_sepa_pain_type': "pain.001.001.09",
            'i3_config_sick_hours_travel': False,
            'i3_config_payslip_transport_amount_manual_input': False,
            'i3_config_print_work_exp_on_payslip': False,
            'i3_config_show_nonpaid_salary_options': False,
            'i3_config_send_contract_expiration': False,
            'i3_config_send_contract_expiration_time': 7,
            'i3_config_disability_fee_min_number_of_employees': 20,
            'i3_config_sick_leave_number_of_months': 6,
            'i3_config_sick_leave_company_percentage': 80,
            'i3_config_disability_fee_crediting': True,
            'i3_config_health_insurance_contribution_pct': 16.50,
            'i3_config_health_insurance_contribution_pct_additional_income': 7.50,
            'i3_config_use_avg_hourly_wage_for_annual_leave_calculation': True,
            'i3_config_annual_leave_wage_number_of_months': 3,
            'hr_config_send_payslips_by_email': False,
            'hr_config_print_brutto2_on_payslip': False,
            'hr_config_print_nonpaid_netto_fees_on_payslip_report': False,
            'hr_config_contributions_base_deduction_limit_1': 700,
            'hr_config_contributions_base_deduction_limit_2': 1300,
            'hr_config_contributions_base_deduction_fixed_amount': 300,
            'i3_config_max_annual_leave': 26,
        }
