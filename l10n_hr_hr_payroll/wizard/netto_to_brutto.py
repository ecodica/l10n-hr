# -*- coding: utf-8 -*-
##############################################################################

##############################################################################

from odoo import fields, _, models, api

SALARY_MIO_PCT = 20.0
SALARY_MIO_PCT_2 = 15.0
ADDITIONAL_INCOME_MIO_PCT = 10.0


class HrPayslipInputNettoToBrutto(models.TransientModel):
    """ Convert netto -> brutto.
        Supported cases:
            1. Payslip input:
                - with or without work exp bonus
                - yearly or monthly tax base / deduction
            2. Salary parameters:
                - with or without work exp bonus
                - yearly data makes no sense here for multiple reasons:
                    - we are not in a fixed month but (usually) in a longer period of time
                    - parameters are supposed to define data for monthly calculation anyway
    """
    _name ='hr.payslip.input.netto.to.brutto'
    _description = 'Calculate brutto from netto'

    calc_type = fields.Selection([
        ('salary', 'Plaća'),
        ('additional_income', 'Drugi dohodak')], 'Način izračuna', required=True)
    work_exp_bonus_coef = fields.Float('Koeficijent dodatka na staž', required=True, digits=('Payroll Rate'))
    use_work_exp_bonus = fields.Boolean('Koristi dodatak na staž')
    netto = fields.Float('Neto iznos', required=True, help="Enter wanted netto amount.")
    tax_deduction = fields.Float('Osobni odbitak', required=True, readonly=True)
    tax_1_pct = fields.Float('1. porezni razred (%)', required=True, readonly=True)
    tax_2_pct = fields.Float('2. porezni razred (%)', required=True, readonly=True)
    tax_1_limit = fields.Float('Granica 1. poreznog razreda', required=True)
    brutto = fields.Float('Bruto iznos', help="Bruto iznos izračunat od strane kalkulatora.")
    brutto_without_work_exp_bonus = fields.Float('Bruto bez dodatka na staž')
    expenditure_pct = fields.Float('Priznati izdatak (%)')
    use_yearly_data = fields.Boolean('Koristi podatke na razini godine')
    payslip_netto_fees = fields.Float('Neto dodaci', help="Ukupni iznos neto dodataka unesenih na listić.", readonly=True)
    payslip_brutto_salary = fields.Float('Bruto plaća', help="Bruto plaća upisana na listiću.")
    brutto_difference = fields.Float('Bruto razlika', help="Razlika između izračunatog bruto iznosa i bruto plaće na listiću.")
    use_manual_contributions_base_deduction = fields.Boolean('Koristi ručno unešeni iznos umanjenja osnovice')
    contributions_base_deduction_amount = fields.Float('Umanjenje osnovice za doprinose')
    mio2 = fields.Boolean('MIO II stup', readonly=True)
    lower_brutto_contributions_base_deduction_limit = fields.Float('Donja bruto granica za umanjenje osnovice za doprinose', readonly=True)
    upper_brutto_contributions_base_deduction_limit = fields.Float('Gornja bruto granica za umanjenje osnovice za doprinose', readonly=True)
    contribution_base_deduction = fields.Float('Fiksni iznos umanjenja osnovice za doprinose', readonly=True)


    @api.onchange('payslip_brutto_salary', 'brutto')
    def update_brutto_difference(self):
        if self.brutto:
            self.brutto_difference = self.brutto_without_work_exp_bonus - self.payslip_brutto_salary
    
    @api.onchange('use_yearly_data')
    def onchange_yearly_data(self):
        """ The checkbox is basically only used in case of hr.payslip.input and not even visible for hr.salary.parameters.
        """
        company = self.env.user.company_id
        if self._context.get('from_salary_parameters'):
            parameters = self.env['hr.salary.parameters'].browse(self._context.get('salary_parameters_id'))
            tax_deduction = parameters.tax_deduction_amount
        if self._context.get('from_payslip_input'):
            input = self.env['hr.payslip.input'].browse(self._context.get('input_id'))
            pay_date = input.payslip_id.payslip_run_id.pay_date
            date_from = pay_date.replace(month=1, day=1)
            date_to = pay_date.replace(month=12, day=31)
            employee = input.payslip_id.employee_id
            tax_deduction = input.payslip_id.tax_deduction_amount - input.payslip_id.total_tax_deduction - input.payslip_id.amount_on_payslip_run('IOOD')
        if not self.use_yearly_data:
            used_on_this_payslip_run = input.payslip_id.amount_on_payslip_run('POROSN')
            donos_osnovice = input.payslip_id.total_tax_base + used_on_this_payslip_run
            self.tax_1_limit = max(company.i3_config_razred_1 / 12 - donos_osnovice, 0)
            self.tax_deduction = tax_deduction
        else:
            used_tax_base = employee._payslip_lines_total(date_from, date_to, ['POROSN']).get(employee.id)
            planned_tax_deduction = employee._planned_tax_deduction(date_from, date_to).get(employee.id)
            used_tax_deduction = employee._payslip_lines_total(date_from, date_to, ['IOOD']).get(employee.id)
            self.tax_1_limit = max(company.i3_config_razred_1 - used_tax_base, 0)
            self.tax_deduction = planned_tax_deduction - used_tax_deduction

    def action_compute(self):
        if self.calc_type == 'additional_income':
            mio_pct = ADDITIONAL_INCOME_MIO_PCT / 100.0
        else:
            #20 ili 15 posto, ovisno postoji li MIO2
            mio_pct = SALARY_MIO_PCT_2 / 100.0 if self.mio2 else SALARY_MIO_PCT / 100.0
        netto = self.netto
        deduction = self.tax_deduction
        # granica prvog poreznog razreda
        tax_1_limit = self.tax_1_limit
        # koeficijent za mio koji se mnozi s dohotkom da se dobije bruto
        # dohodak = bruto * (1 - mio_pct)  =>  bruto = dohodak / (1 - mio_pct), odnosno dohodak * mio_coef
        mio_coef = 1 / (1 - (SALARY_MIO_PCT / 100.0))
        # koeficijent prireza koji ce se mnoziti s porezom, tj.
        # umjesto osnovica * porez (1 + prirez) koristimo osnovica * porez * kpr
        tax_1 = self.tax_1_pct / 100.0
        tax_2 = self.tax_2_pct / 100.0
        income = 0
        expenditure = self.expenditure_pct / 100.0
        use_manual_deduction = self.use_manual_contributions_base_deduction

        if self.calc_type=='salary':
            if netto <= deduction:
                income = netto
            # neto = dohodak - (dohodak - odbitak) * porez_1 * kpr
            # neto = dohodak - dohodak * porez_1 * kpr + odbitak * porez_1 * kpr
            # dohodak (1 - porez_1) = neto - odbitak * porez_1 * kpr
            # dohodak = (neto - odbitak * porez_1 * kpr) / (1 - porez_1)
            elif netto <= (tax_1_limit - tax_1_limit * tax_1 + deduction):
                income = (netto - deduction * tax_1) / (1 - tax_1)
            # porezna_osnovica_1 = granica
            # porezna_osnovica_2 = dohodak - odbitak - granica
            # neto = dohodak - (granica * porez_1 * kpr + (dohodak - odbitak - granica) * porez_2 * kpr)
            # neto = dohodak - granica * porez_1 * kpr - dohodak * porez_2 * kpr + odbitak * porez_2 * kpr + granica * porez_2 * kpr
            # dohodak * (1 - porez_2 * kpr) = neto + granica * porez_1 * kpr - granica * porez_2 * kpr
            # dohodak = (neto + granica * porez_1 * kpr - granica * porez_2 * kpr) / (1 - porez_2 * kpr)
            elif netto > (tax_1_limit - tax_1_limit * tax_1 + deduction):
                income = (netto + (tax_1_limit * tax_1 - tax_1_limit * tax_2 - deduction * tax_2)) / (1 - tax_2)

            if use_manual_deduction:
                deduction = self.contributions_base_deduction_amount
                self.brutto = 1.25 * income - 1.25 * mio_pct * deduction
            else:
                lower_netto_limit = 605 if self.mio2 else 620
                if income <= lower_netto_limit:
                    low_income_brutto = (1.25 * income) / (1 + 1.25 * mio_pct)
                    if low_income_brutto < self.contribution_base_deduction:
                        self.brutto = low_income_brutto
                    else:
                        self.brutto = 1.25 * income - 1.25 * mio_pct * self.contribution_base_deduction
                elif income > lower_netto_limit and income < 1040:
                    if self.mio2:
                        self.brutto = (40 * income) / 29 - (3 * self.upper_brutto_contributions_base_deduction_limit) / 29
                    else:
                        self.brutto = (10 * income) / 7 - (1 * self.upper_brutto_contributions_base_deduction_limit) / 7
                else: #dohodak veći od 1040   
                    self.brutto = income * mio_coef
                # nedostaje slucaj za max doprinose
        else:
            self.brutto = netto / (1 - (1 - expenditure) * (mio_pct + (1 - mio_pct) * tax_1))

        work_exp_bonus_coef = self.work_exp_bonus_coef if self.use_work_exp_bonus else 0
        self.brutto_without_work_exp_bonus = self.brutto /  (1 + work_exp_bonus_coef)

        self.update_brutto_difference()
        action_rec = self.env['ir.model.data']._xmlid_to_res_model_res_id('l10n_hr_hr_payroll.action_netto_to_brutto_wizard')
        
        if action_rec:
            action = self.env['ir.binary']._find_record(res_model=action_rec[0],res_id=action_rec[1]).read([])[0]
            action['res_id'] = self.id
            return action

    def action_save_brutto(self):
        if self._context.get('from_payslip_input'):
            self._update_payslip_input(self.brutto_without_work_exp_bonus)
            self._update_payslip_parameters()
        if self._context.get('from_salary_parameters'):
            self._update_salary_parameters()
        return True
    
    def action_save_brutto_and_compute(self):
        self.action_save_brutto()
        payslip = self.env['hr.payslip'].browse(self._context.get('payslip_id'))
        return payslip.compute_sheet()

    def action_save_difference(self):
        self._update_payslip_input(self.brutto_difference)
        return True

    def action_save_difference_and_compute(self):
        self.action_save_difference()
        payslip = self.env['hr.payslip'].browse(self._context.get('payslip_id'))
        return payslip.compute_sheet()

    def _update_salary_parameters(self):
        parameters = self.env['hr.salary.parameters'].browse(self._context.get('salary_parameters_id'))
        wage = self.brutto_without_work_exp_bonus
        parameters.wage = self.env.user.company_id.currency_id.round(wage)
        return True

    def _update_payslip_input(self, amount):
        input = self.env['hr.payslip.input'].browse(self._context.get('input_id'))
        # round to avoid possible differences between input and calculated payslip line(s)
        input.amount = self.env.user.company_id.currency_id.round(amount)

    def _update_payslip_parameters(self):
            """
                Updating payslip parameters because it should be in sync with netto/brutto calculator
            """
            payslip = self.env['hr.payslip.input'].browse(self._context.get('input_id')).payslip_id
            payslip.use_manual_contributions_base_deduction = self.use_manual_contributions_base_deduction
            payslip.contributions_base_deduction_amount = self.contributions_base_deduction_amount
