# -*- coding: utf-8 -*-

from odoo import api, models, _
from ..models import payroll_common as paycom
from odoo.tools import float_is_zero
from odoo.tools.misc import formatLang, format_date


class Ip1FormReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_ip1_form'
    _description = 'IP1 report'
  
    @api.model
    def _get_report_values(self, doc_ids, data=None):
        doc_model = 'hr.payslip'
        Config = self.env['res.config.settings']
        docs = self.env[doc_model].browse(doc_ids)
        lang = self.env.context.get('lang')
        report_data = {}
        currency_precision = self.env.user.company_id.currency_id.decimal_places
        # expecting exactly one active configuration
        config = self.env['ip1.form.report.config'].search([], limit=1)
        for payslip in docs:
            section_vi = self.section_vi(payslip, config)
            section_x = self.section_x(payslip, config)
            section_xiii = self.section_xiii(payslip, config)
            payslip_data = {
                'title': self.report_title(),
                'section_i_ii': self.section_i_ii(payslip),
                'section_iii': self.section_iii(payslip),
                'section_iv': self.section_iv(payslip),
                'section_v': self.section_v(payslip),
                'section_vi': section_vi,
                'section_vii': self.section_vii(payslip),
                'section_viii': self.section_viii(payslip),
                'section_ix': self.section_ix(payslip),
                'section_x': section_x,
                'section_xi': self.section_xi(payslip),
                'section_xii': self.section_xii(payslip),
                'section_xiii': section_xiii,
                'section_xiv': self.section_xiv(payslip, section_vi, section_x, section_xiii),
                'section_xv': self.section_xv(payslip),
                'signature': self.signature(),
                'display_secondary_currency': self._display_secondary_currency(payslip),
            }
            report_data[payslip.id] = payslip_data
        return {
            'doc_ids': doc_ids,
            'doc_model': doc_model,
            'docs': docs,
            'report_data': report_data,
            'lang':lang,
            'currency_precision': currency_precision,
            'secondary_currency': Config._get_secondary_currency(),
            'secondary_currency_rate_text': Config._secondary_currency_rate_text(),
            'secondary_currency_amount_column_label': Config._secondary_currency_amount_text(),
        }
    
    def format_address(self, street, zip, city):
        return u"{}, {} {}".format(street or '', zip or '', city or '')

    def report_title(self):
        return {
            'name': u"OBRAČUN ISPLAĆENE PLAĆE/NAKNADE PLAĆE/PRIMITAKA NA TEMELJU RADNOG ODNOSA",
            'code': u"Obrazac IP1"
        }

    def section_i_ii(self, payslip):
        employee = payslip.employee_id
        company = payslip.company_id
        title = {
            'i': u"I. PODACI O RADNIKU",
            'ii': u"II. PODACI O POSLODAVCU",
        }
        data = [
            {
                'i': u"1. Ime i Prezime:   {}".format(
                    employee._get_display_name_format('first_name_first').format(employee.first_name, employee.last_name)
                ),
                'ii': u"1. Tvrtka / Ime i Prezime:   {}".format(company.name),
            },
            {
                'i': u"2. Adresa:   {}".format(
                    self.format_address(employee.street, employee.zip, employee.city.name)
                ),
                'ii': u"2. Adresa:   {}".format(
                    self.format_address(company.street, company.zip, company.city_id.name)
                ),
            },
            {
                'i': u"3. Osobni identifikacijski broj:   {}".format(employee.oib),
                'ii': u"3. Osobni identifikacijski broj:   {}".format(company.company_registry),
            },
            {
                'i': u"4. IBAN broj računa: {} kod {}".format(
                    payslip.bank_account_id.acc_number or '____________________',
                    payslip.bank_account_id.bank_id.name or '____________________',
                ),
                'ii': u"4. IBAN broj računa:   {}".format(
                    payslip.payslip_run_id.bank_account_id.acc_number or '____________________'
                ),
            },
            {
                'i': u"5. IBAN broj računa iz članka 212. Ovršnog zakona: {} kod {}".format(
                    payslip.protected_bank_account_id.acc_number or '____________________',
                    payslip.protected_bank_account_id.bank_id.name or '____________________',
                ),
                'ii': "",
            }
        ]
        return {
            'title': title,
            'data': data,
        }
    
    def section_iii(self, payslip):
        """ Add all elements used for salary computation."""
        payroll_conf = self.env['hr.payroll.salary.rule.configuration'] 
        sick_leave_fund = payroll_conf.get_rules('bolovanje_fond')
        sick_leave_company = payroll_conf.get_rules('sick_leave_company_without_injury_at_work')
        has_sick_leave_fund = bool(payslip.worked_days_line_ids.filtered(lambda wd: wd.code in sick_leave_fund))
        has_sick_leave_company = bool(payslip.worked_days_line_ids.filtered(lambda wd: wd.code in sick_leave_company))
        has_annual_leave_with_avg_hourly_wage = bool(payslip.worked_days_line_ids.filtered(lambda wd: wd.code in ['GO'])) \
            and payslip.use_avg_hourly_wage_for_annual_leave_calculation
        payslip_run = payslip.payslip_run_id
        sequence = 0
        data = []
        res = {
            'title': u"III. OPĆI PODACI POTREBNI ZA OBRAČUN PLAĆE",
            'data': data
        }
        prec = self.env['decimal.precision'].precision_get('Payroll Rate')
        # no salary-based calculation in these cases so nothing to display here
        if payslip_run.salary_in_kind or payslip_run.i3_add_only_inputs:
            return res
        if payslip.salary_calculation_type == 'hourly_wage':
            # contracted hourly wage
            sequence += 1
            data.append(u"1.{} Bruto satnica: {}".format(
                sequence, formatLang(self.env, payslip.hourly_wage, digits=prec)
            ))
        else:
            # contracted salary
            sequence += 1
            data.append(u"1.{} Bruto plaća: {}".format(sequence, formatLang(self.env, payslip.wage)))
            if payslip.salary_calculation_type != 'fixed_salary':
                # hourly wage which is actually used in the calculation
                month_work_hours = payslip.month_work_hours
                if payslip.salary_calculation_type == 'month_work_hours':
                    month_work_hours = payslip.payslip_run_id.period_work_hours
                sequence += 1
                data.append(u"1.{} Bruto satnica: {}".format(
                    sequence, formatLang(self.env, payslip.wage / month_work_hours, digits=prec)
                ))
        if has_sick_leave_company:
            hourly_wage = 0
            if payslip.hr_config_sick_leave_company_calc_method == 'average_hourly_wage':
                hourly_wage = payslip.sick_leave_average_hourly_wage_gross
            elif payslip.hr_config_sick_leave_company_calc_method == 'contract_hourly_wage':
                hourly_wage = payslip.hourly_wage
            elif payslip.hr_config_sick_leave_company_calc_method == 'contract_salary':
                total_month_hours = payslip.payslip_run_id.period_work_hours
                hourly_wage = payslip.wage / total_month_hours
            sequence += 1
            data.append(u"1.{} Bruto satnica za izračun bolovanja na teret poslodavca: {}".format(
                sequence, formatLang(self.env, hourly_wage, digits=prec)
            ))
        if has_sick_leave_fund:
            sequence += 1
            data.append(u"1.{} Neto satnica za izračun bolovanja na teret HZZO-a: {}".format(
                sequence, formatLang(self.env, payslip.sick_leave_average_hourly_wage_net, digits=prec)
            ))
        if has_annual_leave_with_avg_hourly_wage:
            sequence += 1
            data.append(u"1.{} Prosječna satnica za izračun naknade za godišnji odmor: {}".format(
                sequence, formatLang(self.env, payslip.unused_leave_average_hourly_wage, digits=prec)
            ))
        if payslip.experience_coef:
            sequence += 1
            data.append(u"1.{} Koeficijent za izračun dodatka na staž: {}".format(
                sequence, formatLang(self.env, (payslip.experience_coef * payslip.internship_total_years)/100, digits=prec)
            ))
        res['data'] = data
        return res

    def section_iv(self, payslip):
        sequence = 1
        data = [
            {
                'label': u"1.{}. Datum isplate".format(sequence),
                'value': format_date(self.env, payslip.payslip_run_id.pay_date),
            },
        ]
        # TODO: NP1 obrazac i djelomicna isplata
        partial_payment = False
        if partial_payment:
            sequence += 1
            data.append({
                'label': u"1.{}. Datum djelomične isplate plaće/naknade plaće (ispunjava se uz obrazac NP1)".format(sequence),
                'value': '',
            })
        no_payment = False
        if no_payment:
            sequence += 1
            data.append({
                'label': u"1.{}. Datum obračuna u slučaju neisplate plaće/naknade plaće (ispunjava se uz obrazac NP1)".format(sequence),
                'value': '',
            })
        return {
            'title': u"IV. DATUM ISPLATE/OBRAČUNA",
            'data': data
        }

    def section_v(self, payslip):
        return {
            'label': u"V. RAZDOBLJE NA KOJE SE PLAĆA ODNOSI:",
            'value': u"GODINA {}, MJESEC {}, DANI U MJESECU OD {} DO {}".format(
                payslip.date_from.year or '________',
                payslip.date_from.month or '____',
                payslip.date_from.day or '____',
                payslip.date_to.day or '____',
            )
        }

    def section_vi(self, payslip, config):
        vi_2_data = self.section_vi_2_data(payslip, config)
        vi_2_hours = sum([item['hours_worked'] for item in vi_2_data])
        vi_2_amount = sum([item['amount'] for item in vi_2_data])
        vi_2_amount_paid = sum([item['amount_paid'] for item in vi_2_data])
        vi_3_data = self.section_vi_3_data(payslip)
        vi_3_hours = sum([item['hours_worked'] for item in vi_3_data])
        vi_3_amount = sum([item['amount'] for item in vi_3_data])
        vi_header = {
            'name': u"OPIS",
            'hours': u"SATI",
            'compute': u"ELEMENT OBRAČUNA",
            'amount': u"IZNOS",
        }
        vi_1 = {
            'name': u"1. REDOVNI MJESEČNI FOND SATI I UKUPAN IZNOS PLAĆE/NAKNADE PLAĆE/PRIMITAKA NA TEMELJU RADNOG ODNOSA",
            'hours': vi_2_hours + vi_3_hours,
            'compute': u"",
            'amount': vi_2_amount + vi_3_amount,
        }
        vi_2 = {
            'name': u"2. PODACI O VRSTI I IZNOSIMA OSTVARENE PLAĆE/NAKNADE PLAĆE/ I BROJU OSTVARENIH SATI RADA/NAKNADE NA TERET POSLODAVCA",
            'hours': vi_2_hours,
            'compute': u"",
            'amount': vi_2_amount,
            'amount_paid': vi_2_amount_paid,
        }
        vi_3 = {
            'name': u"3. PODACI O VRSTI I IZNOSIMA OSTVARENE NAKNADE I BROJU OSTVARENIH SATI NAKNADE NA TERET HZZO",
            'hours': vi_3_hours,
            'compute': u"",
            'amount': vi_3_amount,
        }
        vi_4 = {
            # nije podrzano
            'header': {},
            'data': []
        }
        return {
            'vi_title': u"VI. PODACI O RADNOM VREMENU I OSTVARENOJ PLAĆI/NAKNADI PLAĆE/PRIMICIMA NA TEMELJU RADNOG ODNOSA",
            'vi_header': vi_header,
            'vi_1': vi_1,
            'vi_2': vi_2,
            'vi_2_data': vi_2_data,
            'vi_3': vi_3,
            'vi_3_data': vi_3_data,
            'vi_4': vi_4,
        }
    
    def section_vi_2_data(self, payslip, config):
        not_paid = self.env['hr.payroll.salary.rule.configuration'].get_rules('not_paid')
        data = []
        sequence = 0
        last_subsection = 0
        positions = config.position_ids.filtered(lambda p: p.section == '062')
        for position in positions.sorted(key=lambda p: (p.subsection, p.sequence)):
            codes = position.rule_ids.mapped('code')
            current_subsection = int(position.subsection)
            if current_subsection != last_subsection:
                sequence = 0
            last_subsection = current_subsection
            payslip_lines = [line for line in payslip.line_ids if line.code in codes]
            amount = sum(line.total for line in payslip_lines)
            # for not_paid categories we compute BASIC rule as is it was normal salary
            # in fact only contributions are paid on that base, and the base itself is not
            amount_paid = sum(line.total for line in payslip_lines if line.code not in not_paid)
            wd_lines = payslip.worked_days_line_ids.filtered(lambda l: l.code in codes)
            # not all categories are considered for total hours fund
            # e.g. for 8h of night work we add 8h of RR & 8h of NOC
            # -> the employee worked 8h effectively, but for calculation purposes it's 16h
            # in the report all hours are displayed per category, but not all of them are summed into the total hours fund
            hours_total = sum(wd_lines.mapped('number_of_hours'))
            hours_worked = sum(wd_lines.filtered(lambda l: not l.category_id.skip_hours).mapped('number_of_hours'))
            if hours_total or amount or position.print_always:
                sequence += 1
                data.append({
                    'name': u"{}.{}. {}".format(current_subsection, sequence, position.name),
                    'hours': hours_total,
                    'compute': ', '.join([str(formatLang(self.env, line.salary_rule_id.ip1_form_coef)) for line in payslip_lines]),
                    'amount': amount,
                    'amount_paid': amount_paid,
                    'hours_worked': hours_worked,
                })
        return data
    
    def section_vi_3_data(self, payslip):
        data = []
        sequence = 0
        for wd_line in payslip.worked_days_line_ids.filtered(lambda l: l.code in self.env['hr.payroll.salary.rule.configuration'].get_rules('bolovanje_fond')):
            payslip_lines = payslip.line_ids.filtered(lambda l: l.code == wd_line.code)
            amount = sum(payslip_lines.mapped('total'))
            hours_total = sum(wd_line.mapped('number_of_hours'))
            hours_worked = sum(wd_line.filtered(lambda l: not l.category_id.skip_hours).mapped('number_of_hours'))
            if hours_total or amount:
                sequence += 1
                data.append({
                    'name': u"3.{}. {}".format(sequence, wd_line.name),
                    'hours': hours_total,
                    'compute': ', '.join([str(formatLang(self.env, line.salary_rule_id.ip1_form_coef)) for line in payslip_lines]),
                    'amount': amount,
                    'hours_worked': hours_worked,
                })
        return data
    
    def section_vii(self, payslip):
        payroll_conf = self.env['hr.payroll.salary.rule.configuration'] 
        contributions_base = payroll_conf.get_rules('contributions_base')
        contributions_base_deducted = payroll_conf.get_rules('contributions_base_deducted')
        doprinosi_mio1 = paycom.get_mio_stup('1')
        doprinosi_mio2 = paycom.get_mio_stup('2')
        header = {
            'name': u"Opis",
            'amount': u"IZNOS",
        }
        total = [
            {
                'name': u"OSNOVICA ZA UTVRĐIVANJE DOPRINOSA PREMA OPOREZIVIM NAKNADAMA",
                'amount': sum(payslip.line_ids.filtered(lambda l: l.code in contributions_base).mapped('total')),
            },
            {
                'name': u"OSNOVICA ZA UTVRĐIVANJE DOPRINOSA ZA MIROVINSKO OSIGURANJE NA TEMELJU GENERACIJSKE SOLIDARNOSTI",
                'amount': sum(payslip.line_ids.filtered(lambda l: l.code in contributions_base_deducted).mapped('total')),
            }
        ]
        data = [
            {
                'name': u"1. doprinos za mirovinsko osiguranje na temelju generacijske solidarnosti",
                'amount': sum(payslip.line_ids.filtered(lambda l: l.code in doprinosi_mio1).mapped('total')),
            },
            {
                'name': u"2. doprinos za mirovinsko osiguranje na temelju individualne kapitalizirane štednje",
                'amount': sum(payslip.line_ids.filtered(lambda l: l.code in doprinosi_mio2).mapped('total')),
            },
        ]
        return {
            'title': u"VII. UTVRĐIVANJE DOPRINOSA IZ OSNOVICE",
            'header': header,
            'total': total,
            'data': data
        }

    def section_viii(self, payslip):
        sequence = 0
        data = []
        sequence, data = self.section_viii_taxable_receipt(payslip, data, sequence)
        sequence, data = self.section_viii_expenses(payslip, data, sequence)
        sequence, data = self.section_viii_income(payslip, data, sequence)
        sequence, data = self.section_viii_tax_deduction(payslip, data, sequence)
        sequence, data = self.section_viii_tax_base(payslip, data, sequence)
        sequence, data = self.section_viii_tax(payslip, data, sequence)
        sequence, data = self.section_viii_war_disability(payslip, data, sequence)
        sequence, data = self.section_viii_tax_correction(payslip, data, sequence)
        sequence, data = self.section_viii_total_tax(payslip, data, sequence)
        return {
            'title': u"VIII. UTVRĐIVANJE POREZA NA DOHODAK",
            'data': data,
        }
    
    def section_viii_taxable_receipt(self, payslip, data, sequence):
        sequence += 1
        data.append({
            'name': u"{}. IZNOS OSTVARENOG OPOREZIVOG PRIMITKA".format(sequence),
            'amount': sum(payslip.line_ids.filtered(lambda l: l.code in ['BASIC']).mapped('total')),
        }),
        return sequence, data
    
    def section_viii_expenses(self, payslip, data, sequence):
        doprinosi_iz_place = self.env['hr.payroll.salary.rule.configuration'].get_rules('doprinosi_iz_place')
        doprinosi_mio1 = paycom.get_mio_stup('1')
        doprinosi_mio2 = paycom.get_mio_stup('2')
        sequence += 1
        data.append({
            'name': u"{}. IZDACI (VIII.2.1. + VIII.2.2.)".format(sequence),
            'amount': sum(payslip.line_ids.filtered(lambda l: l.code in doprinosi_iz_place).mapped('total')),
            'type': 'expenses',
            'lines': [{
                'name': u"{}.1. plaćeni iznos doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti".format(sequence),
                'amount': sum(payslip.line_ids.filtered(lambda l: l.code in doprinosi_mio1).mapped('total')),
            },
            {
                'name': u"{}.2. plaćeni iznos doprinosa za mirovinsko osiguranje na temelju individualne kapitalizirane štednje".format(sequence),
                'amount': sum(payslip.line_ids.filtered(lambda l: l.code in doprinosi_mio2).mapped('total')),
            }]
        })
        return sequence, data

    def section_viii_income(self, payslip, data, sequence):
        sequence += 1
        data.append({
            'name': u"{}. DOHODAK".format(sequence),
            'amount': sum(payslip.line_ids.filtered(lambda l: l.code in ['DOH']).mapped('total')),
        })
        return sequence, data
    
    def section_viii_tax_deduction(self, payslip, data, sequence):
        sequence += 1
        data.append({
            'name': u"{}. NEOPOREZIVI ODBITAK (UKUPAN FAKTOR OSOBNOG ODBITKA)".format(sequence),
            'amount': sum(payslip.line_ids.filtered(lambda l: l.code in ['OOD']).mapped('total')),
        })
        return sequence, data
    
    def section_viii_tax_base(self, payslip, data, sequence):
        sequence += 1
        data.append({
            'name': u"{}. POREZNA OSNOVICA".format(sequence),
            'amount': sum(payslip.line_ids.filtered(lambda l: l.code in ['POROSN']).mapped('total')),
        })
        return sequence, data

    def section_viii_tax(self, payslip, data, sequence):
        viii_6_header = {
            'pct': u"STOPA (%)",
            'base': u"OSNOVICA",
            'amount': u"",
        }
        viii_6_data = self.section_viii_tax_data(payslip)
        sequence += 1
        data.append({
            'name': u"{}. UKUPAN IZNOS POREZA".format(sequence),
            'amount': sum(payslip.line_ids.filtered(lambda l: l.code in ['PDOH']).mapped('total')),
            'type': 'taxes',
            'lines': {
                'header': viii_6_header,
                'data': viii_6_data,
            },
        })
        return sequence, data

    def section_viii_tax_data(self, payslip):
        data = []
        sequence = 0
        payroll_conf = self.env['hr.payroll.salary.rule.configuration'] 
        for tax_level in ['income_tax_1', 'income_tax_2']:
            tax_level_base = tax_level + '_base'
            codes = payroll_conf.get_rules(tax_level)
            pct_field = paycom.get_tax_percentage_fields()[tax_level]
            base_codes = payroll_conf.get_rules(tax_level_base)
            amount = sum(payslip.line_ids.filtered(lambda l: l.code in codes).mapped('total'))
            if amount:
                sequence += 1
                data.append({
                    'pct': u"6.{}. {} %".format(sequence, formatLang(self.env, payslip[pct_field])),
                    'base': sum(payslip.line_ids.filtered(lambda l: l.code in base_codes).mapped('total')),
                    'amount': amount
                })
        return data
    
    def section_viii_war_disability(self, payslip, data, sequence):
        war_disability_tax_relief_codes = self.env['hr.payroll.salary.rule.configuration'].get_rules('war_disability_tax_relief')
        war_disability_tax_relief_pct_field = paycom.get_tax_percentage_fields()['war_disability_tax_relief']
        relief_amount = sum(payslip.line_ids.filtered(lambda l: l.code in war_disability_tax_relief_codes).mapped('total'))
        if float_is_zero(relief_amount, precision_digits=payslip.company_id.currency_id.decimal_places):
            return sequence, data
        sequence += 1
        data.append({
            'name': u"{}. IZNOS UMANJENJA OBVEZE POREZA ZA POSTOTAK INVALIDNOSTI HRVI-a ({} %)".format(sequence, payslip[war_disability_tax_relief_pct_field]),
            'amount': relief_amount,
        })
        return sequence, data

    def section_viii_tax_correction(self, payslip, data, sequence):
        viii_9_data = self.section_viii_9_data(payslip)
        if not viii_9_data:
            return sequence, data
        sequence += 1
        data.append({
            'name': u"{}. KOREKCIJE POREZA +/-".format(sequence),
            'amount': 0,
            'data': viii_9_data
        })
        return sequence, data

    def section_viii_9_data(self, payslip):
        # nije podrzano
        return []
    
    def section_viii_total_tax(self, payslip, data, sequence):
        total_tax_codes = paycom.get_categories()['total_tax']
        sequence += 1
        data.append({
            'name': u"{}. UKUPNO POREZ".format(sequence),
            'amount': sum(payslip.line_ids.filtered(lambda l: l.code in total_tax_codes).mapped('total')),
        })
        return sequence, data

    def section_ix(self, payslip):
        return {
            'name': u"IX. IZNOS PLAĆE",
            'amount': sum(payslip.line_ids.filtered(lambda l: l.code in ['NETO']).mapped('total')),
        }
    
    def section_x(self, payslip, config):
        data = self.section_x_data(payslip, config)
        title = {
            'name': u"X. VRSTE I IZNOSI NEOPOREZIVIH PRIMITAKA",
            'amount': sum([item['amount'] for item in data])
        }
        header = {
            'sequence': u"",
            'name': u"VRSTA NEOPOREZIVOG PRIMITKA",
            'period': u"RAZDOBLJE (GODINA/MJESEC/VIŠE MJESECI)",
            'amount': u"IZNOS",
        }
        return {
            'title': title,
            'header': header,
            'data': data,
        }

    def section_x_data(self, payslip, config):
        data = []
        sequence = 0
        positions = config.position_ids.filtered(lambda p: p.section == '10')
        for position in positions.sorted(key=lambda p: p.sequence):
            for rule in position.rule_ids:
                codes = rule.mapped('code')
                amount = sum(payslip.line_ids.filtered(lambda l: l.code in codes).mapped('total'))
                if amount or position.print_always:
                    sequence += 1
                    data.append({
                        'sequence': u"{}.".format(sequence),
                        'name': u"{} - {}".format(position.name or '', rule.name or ''),
                        'period': "{}.{}.".format(payslip.payslip_run_id.pay_date.month, payslip.payslip_run_id.pay_date.year),
                        'amount': amount,
                    })
        return data

    def section_xi(self, payslip):
        data = []
        suspension_lines = [x for x in payslip.line_ids if x.code in ['TOPOB','MSPORT'] and x.amount > 0]
        sequence = 0   
        for suspension_line in payslip.suspension_lines:
            sequence += 1
            data.append({
                'name': u"{}. {}".format(sequence, suspension_line.description or 'Obustave'),
                'amount': suspension_line.amount
            })
        for line in suspension_lines:
            sequence += 1
            data.append({
                'name':u"{}. {}".format(sequence, line.name or 'Obustave'),
                'amount': line.amount
            })
        total_sum = round(sum([item.get('amount') for item in data]),2)

        title = {
            'name': u"XI. VRSTE I IZNOSI OBUSTAVA IZ PLAĆE",
            'amount': total_sum,
        }
        return {
            'title': title,
            'data': data,
        }


    def get_payment(self, slip):
        bank_lines = self.group_payslip_bank_lines(slip)
        payment = {
            'amount': sum(line['amount'] for line in bank_lines),
            'amount_sccy': sum(line['amount_sccy'] for line in bank_lines)
        }
        return [payment]

    def group_payslip_bank_lines(self, slip):
        """
        There are (possibly) multiple entries for same bank account on hr_payslip_bank_line object and we want them grouped on report.
        """
        Config = self.env['res.config.settings']
        lines = {}
        for bank_line in slip.bank_lines:
            if float_is_zero(bank_line.amount, precision_digits=slip.company_id.currency_id.decimal_places) == False:
                # group by bank accounts, and payment methods
                if bank_line.bank_account_id:
                    key = bank_line.bank_account_id
                    if key not in lines:
                        lines.update({
                            bank_line.bank_account_id: {
                                'iban': bank_line.bank_account_id.acc_number,
                                'bank': bank_line.bank_account_id.bank_id and bank_line.bank_account_id.bank_id.name or '',
                                'type': (bank_line.acc_type and bank_line.acc_type == 'normal' and u'Redovni račun'
					                    or bank_line.acc_type == 'protected' and u'Zaštićeni račun' or u'Žiro račun'),
                                'amount': 0,
                                'amount_sccy': 0,
                            }
                        })
                    lines[key]['amount'] += bank_line.amount
                    lines[key]['amount_sccy'] += Config._convert_secondary_currency_amount(bank_line.amount)
                elif bank_line.payment_method_id:
                    key = bank_line.payment_method_id.id
                    if key not in lines:
                        lines.update({
                            key: {
                                'iban': bank_line.payment_method_id.description,
                                'bank': '',
                                'type': False,
                                'amount': 0,
                                'amount_sccy': 0,
                            }
                        })
                    lines[key]['amount'] += bank_line.amount
                    lines[key]['amount_sccy'] += Config._convert_secondary_currency_amount(bank_line.amount)
        res = []
        for key in lines:
            res.append(lines[key])
        return res

    def section_xii(self, payslip):
        payslip_report_payment = self.get_payment(payslip)[0]
        title = {
            'name': u"XII. IZNOS ZA ISPLATU NAKON OBUSTAVA IZ PLAĆE",
            'amount': payslip_report_payment['amount'],
            'amount_sccy': payslip_report_payment['amount_sccy'],
        }
        payment_lines = self.group_payslip_bank_lines(payslip)
        data = []
        sequence = 0
        for line in payment_lines:
            sequence += 1
            data.append({
                'name': u"{}. {} {}".format(sequence, line.get('iban'), line.get('bank')),
                'amount': line.get('amount', 0),
                'amount_sccy': line.get('amount_sccy', 0),
            })
        return {
            'title': title,
            'data': data,
        }

    def section_xiii(self, payslip, config):
        contributions_base_codes = self.env['hr.payroll.salary.rule.configuration'].get_rules('contributions_base')
        structures_without_contributions_on = paycom.get_structures()['without_contributions_on']
        if payslip.struct_id.code in structures_without_contributions_on:
            contributions_base = 0
        else:
            contributions_base = sum(payslip.line_ids.filtered(lambda l: l.code in contributions_base_codes).mapped('total'))
        xiii_2_data = self.section_xiii_2_data(payslip, config)
        data = {
            'title': u"XIII. DOPRINOSI NA OSNOVICU",
            'xiii_1': {
                'name': u"1. OSNOVICA ZA UTVRĐIVANJE DOPRINOSA NA OSNOVICU",
                'amount': contributions_base,
            },
            'xiii_2': {
                'name': u"2. IZNOS DOPRINOSA NA OSNOVICU",
                'amount': sum([item['amount'] for item in xiii_2_data]),
            },
            'xiii_2_data' : xiii_2_data,
        }
        return data

    def section_xiii_2_data(self, payslip, config):
        data = []
        sequence = 0
        positions = config.position_ids.filtered(lambda p: p.section == '132')
        for position in positions.sorted(key=lambda p: p.sequence):
            codes = position.rule_ids.mapped('code')
            amount = sum(payslip.line_ids.filtered(lambda l: l.code in codes).mapped('total'))
            if amount or position.print_always:
                sequence += 1
                data.append({
                    'name': u"2.{} {}.".format(sequence, position.name),
                    'amount': amount,
                })
        return data
    
    def section_xiv(self, payslip, section_vi, section_x, section_xiii):
        vi_2 = section_vi['vi_2']['amount_paid']
        x = sum([item['amount'] for item in section_x['data']])
        xiii = section_xiii['xiii_2']['amount']
        return {
            'title': u"XIV. UKUPAN TROŠAK RADA",
            'amount': vi_2 + x + xiii,
        }

    def section_xv(self, payslip):
        return {
            'title': u"XV. NAPOMENA",
        }

    def signature(self):
        return {
            'name': u"Ovlaštena osoba poslodavca",
            'label': u"(IME I PREZIME)",
        }

    def _display_secondary_currency(self, slip):
        Config = self.env['res.config.settings']
        display_seconary_currency = Config._display_secondary_currency()
        secondary_currency_apply_date = Config._get_secondary_currency_apply_date()
        report_date = slip.payslip_run_id.date_end
        return (
            display_seconary_currency and
            not slip.salary_in_kind and
            (not secondary_currency_apply_date or report_date >= secondary_currency_apply_date) or
            False
        )
