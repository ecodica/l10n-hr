# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

class ContributionBaseDistribution(models.TransientModel):
    _name = 'contribution.base.distribution'
    _description = 'Raspodjela umanjenja osnovice za doprinose'


    date_from = fields.Date('Date from')
    date_to = fields.Date('Date to')
    payslip_run_ids = fields.Many2many('hr.payslip.run', 'payslip_run_group_rel', 'wizard_id', 'run_id', 'Obračuni plaće', required=True)
    employees_selection = fields.Selection([('all_employees','Svi zaposlenici'), ('multiple_payslips','Zaposlenici s više platnih lista')], string="Filter Zaposlenika", default="multiple_payslips", required=True)
    employees_with_salary = fields.One2many('contribution.base.distribution.line', 'wizard_id', 'Zaposlenici s plaćom')

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        first_of_month = datetime.today().replace(day=1)
        last_of_month = first_of_month + relativedelta(months=1, days=-1)
        defaults['date_from'] = first_of_month
        defaults['date_to'] = last_of_month
        return defaults

    def get_employees_with_salary(self, payslip_run_ids, emp_selection):
        """
        Return list of employees with total salary.
        """
        emp_list = []
        slip_ids = [slip for run in payslip_run_ids for slip in run.slip_ids]
        employee_ids = list(set(slip.employee_id for slip in slip_ids if slip.employee_id))

        for emp in employee_ids:
            emp_slips = [slip for slip in slip_ids if slip.employee_id == emp]
            if emp_selection == 'multiple_payslips' and len(emp_slips) <= 1:
                continue
            total_osnumosndop = 0
            iskoristeno_umosndop = 0
            ukupno_umanjenje = 0
            # ovo je ukupni iznos osnovice za umanjenje osnovice za doprinose
            for slip in emp_slips:
                total_osnumosndop += sum([line.amount for line in slip.line_ids.filtered(lambda x: x.code == 'OSNUMOSNDOP')])
                if slip.payslip_run_id.state != 'draft':
                    iskoristeno_umosndop += sum([line.amount for line in slip.line_ids.filtered(lambda x: x.code == 'UMOSNDOP')])
            # ovdje treba izračunati koliko je ukupni iznos umanjenja (formula iz calculate_deduction)
            ukupno_umanjenje += self.calculate_deduction(slip, total_osnumosndop)
            umanjenje_za_raspodijeliti = ukupno_umanjenje - iskoristeno_umosndop
            for slip in emp_slips:
                state_is_draft = slip.payslip_run_id.state == 'draft'
                # ukupni iznos umanjenja se raspodjeljuje po stavkama
                brutto = [line.amount for line in slip.line_ids.filtered(lambda x: x.code == 'BASIC')]  
                brutto = brutto and brutto[0] or 0.0 
                amount_osnumosndop = sum([line.amount for line in slip.line_ids.filtered(lambda x: x.code == 'OSNUMOSNDOP')])
                umanjenje_obracunato = sum([line.amount for line in slip.line_ids.filtered(lambda x: x.code == 'UMOSNDOP')])
                # ako je listić već obračunat, ne diramo ga
                umanjenje = min(amount_osnumosndop, umanjenje_za_raspodijeliti) if state_is_draft else umanjenje_obracunato
                emp_list.append((0, 0, {
                    'emp_id': slip.employee_id.id,
                    'salary': brutto,
                    'payslip_id': slip.id,
                    'pay_date': slip.payslip_run_id.pay_date,
                    'amount_osnumosndop': amount_osnumosndop,
                    'amount_umosndop': umanjenje_obracunato,
                    'amount_osnumosndop_monthly': total_osnumosndop,
                    'joppd_b72': self.set_joppd_b72(slip, total_osnumosndop),
                    'manual_deduction': umanjenje,
                }))
                # ovo nam vjerojatno treba samo za slučaj kad je kompletno umanjenje već iskorišteno
                if state_is_draft:
                    umanjenje_za_raspodijeliti -= umanjenje
        return emp_list

    def set_joppd_b72(self, slip, total_osnumosndop, deduction):
        if slip.joppd_b72 in ['2','3']:
            return slip.joppd_b72
        return '0' if total_osnumosndop > slip.hr_config_contributions_base_deduction_limit_2 or deduction == 0 else '1'

    def calculate_deduction(self, payslip, deductable_base):
        limit_1 = payslip.hr_config_contributions_base_deduction_limit_1
        limit_2 = payslip.hr_config_contributions_base_deduction_limit_2
        fixed_deduction = payslip.hr_config_contributions_base_deduction_fixed_amount
        amount = 0
        if deductable_base <= limit_1:
            amount = min(fixed_deduction, deductable_base)
        elif deductable_base > limit_1 and deductable_base <= limit_2:
            amount = 0.5 * (limit_2 - deductable_base)
        return amount

    def fetch_data(self):
        self.employees_with_salary = None
        emp_list = self.get_employees_with_salary(self.payslip_run_ids, self.employees_selection)
        self.employees_with_salary = emp_list
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'contribution.base.distribution',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.onchange('date_from', 'date_to')
    def onchange_period(self):
        if self.date_from and self.date_to:
            payslip_run_ids = self.env['hr.payslip.run'].search([('pay_date', '>=', self.date_from), ('pay_date', '<=', self.date_to)]).ids
            self.payslip_run_ids = payslip_run_ids

    def compute_distribution(self):
        slips_to_update = self.employees_with_salary.filtered(lambda line: line.run_state == 'draft')
        slips_to_update.mapped('payslip_id').clear_payslip_lines()
        for line in slips_to_update:
            slip = line.payslip_id
            slip.use_manual_contributions_base_deduction = True
            slip.contributions_base_deduction_amount = line.manual_deduction
            slip.joppd_b72 = line.joppd_b72
            slip.compute_sheet()
        return {'type': 'ir.actions.act_window_close'}

class ContributionBaseDistributionLine(models.TransientModel):
    _name = 'contribution.base.distribution.line'
    _description = 'Employee line for contribution base distribution wizard'

    def _joppd_b72_sel(self):
        return self.env['hr.joppd.form.b']._b72_sel()

    wizard_id = fields.Many2one('contribution.base.distribution', 'Wizard')
    # employee_id is used to show as readonly on form, emp_id is the "actual" field
    # if we only use readonly field, then it can not be read from wizard for some reason so this is a workaround
    employee_id = fields.Many2one(related='emp_id', string='Zaposlenik')
    emp_id = fields.Many2one('hr.employee', 'Emp')
    payslip_id = fields.Many2one('hr.payslip', 'Isplatni listić', readonly=True)
    pay_date = fields.Date('Datum isplate', readonly=True)
    run_state = fields.Selection(related='payslip_id.payslip_run_id.state')
    amount_osnumosndop = fields.Float('Obračunati iznos OSNUMOSNDOP', readonly=True)
    amount_umosndop = fields.Float('Obračunati iznos UMOSNDOP', readonly=True)
    amount_osnumosndop_monthly = fields.Float('Suma OSNUMOSNDOP', readonly=True)
    salary = fields.Float(string='Bruto plaća', readonly=True)
    joppd_b72 = fields.Selection(_joppd_b72_sel, 'Tip umanjenenja osnovice')
    manual_deduction = fields.Float(string='Umanjenje osnovice za doprinose')
