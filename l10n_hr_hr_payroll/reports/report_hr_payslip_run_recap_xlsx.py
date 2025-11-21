from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import json

class HrPayslipRunRecapXSLX(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.hr_payslip_run_recap_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Payslip Run Recap XLSX Report"

    def generate_xlsx_report(self, workbook, data, report_book):
        self = self.with_context(lang=self.env.user.lang)
        doc_ids = self.env.context.get('active_ids',report_book.ids)
        doc_model = self.env.context['active_model']
        docs = self.env[doc_model].browse(doc_ids)
        run_ids = data.get('run_ids',report_book.ids)
        run_obj = self.env['hr.payslip.run']
        runs = run_obj.browse(run_ids)
        dep_id = data.get('department_id')
        department_ids = data.get('department_ids', runs.mapped('slip_ids').mapped('employee_id').mapped('department_id').ids)
        company = self.env.user.company_id
        pdf_report_obj = self.env['report.l10n_hr_hr_payroll.report_hr_payslip_run_recap']
        company_lang= self.env.user.company_id.partner_id.lang
        lang= False
        dep_cond = pdf_report_obj.get_department_condition(department_ids)
        run_cond = pdf_report_obj.get_payslip_run_condition(run_ids)
        iban = self._get_company_iban(company)
        currency_precision = self.env.user.company_id.currency_id.decimal_places
        p_precision = '0'*currency_precision

        #getting report data
        number_of_employees = pdf_report_obj.get_employees(run_cond, dep_id, department_ids)
        run_names = pdf_report_obj.get_payslip_run_names(runs)
        payslip_totals = pdf_report_obj.get_payslip_totals(runs, dep_cond)
        contributions_from_salaries = pdf_report_obj.get_contributions_from_salaries(run_cond, dep_cond)
        work_abroad_hr = pdf_report_obj.get_work_abroad_hr(run_cond, dep_cond)
        income = pdf_report_obj.get_income(run_cond, dep_cond)
        admitted_cost = pdf_report_obj.get_admitted_cost(run_cond, dep_cond)
        taxes = pdf_report_obj.get_taxes(run_cond, dep_cond)
        neto = pdf_report_obj.get_neto(run_cond, dep_cond)
        work_abroad_ino = pdf_report_obj.get_work_abroad_ino(run_cond, dep_cond)
        payslip_lines_totals = pdf_report_obj.get_payslip_compensations(run_ids, dep_cond)
        suspensions = pdf_report_obj.get_suspensions(run_cond, dep_cond)
        payment = pdf_report_obj.get_payment(run_cond, dep_cond)
        contributions_on_salaries = pdf_report_obj.get_contributions_on_salaries(run_cond, dep_cond)
        brutto2 = pdf_report_obj.get_brutto2(run_cond, dep_cond)
        local_tax = pdf_report_obj.get_local_tax_totals(run_cond, dep_cond)
        local_tax_sum = pdf_report_obj.get_sum_local_tax(run_cond, dep_cond)

        document_header_center_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'vcenter','text_wrap': True, 'font_size': 14, 'border_color': '#FFFFFF'})
        document_header_left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 14})
        document_header_left_small_format = workbook.add_format({'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 9})
        document_header_left_small_bold_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 9})
        document_header_left_medium_format = workbook.add_format({'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 12})
        document_header_left_medium_bold_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 12})
        table_header_left_format = workbook.add_format({'align': 'left', 'text_wrap': True, 'font_size': 9, 'bg_color': '#BDBDBD', 'fg_color': '#424242', 'bottom': 1})
        table_header_center_format = workbook.add_format({'align': 'center', 'text_wrap': True, 'font_size': 9, 'bg_color': '#BDBDBD', 'fg_color': '#424242', 'bottom': 1})
        table_header_right_format = workbook.add_format({'align': 'right', 'text_wrap': True, 'font_size': 9, 'bg_color': '#BDBDBD', 'fg_color': '#424242', 'bottom': 1})
        table_content_left_format = workbook.add_format({'align': 'left', 'text_wrap': True, 'font_size': 9, 'num_format':  f'#,##0.{p_precision}'})
        table_content_center_format = workbook.add_format({'align': 'center', 'text_wrap': True, 'font_size': 9, 'num_format':  f'#,##0.{p_precision}'})
        table_content_right_format = workbook.add_format({'align': 'right', 'text_wrap': True, 'font_size': 9, 'num_format':  f'#,##0.{p_precision}'})
        table_content_left_bold_format = workbook.add_format({'bold': True, 'align': 'left', 'text_wrap': True, 'font_size': 9, 'top': 2})
        table_content_center_bold_format = workbook.add_format({'bold': True, 'align': 'center', 'text_wrap': True, 'font_size': 9, 'top': 2, 'num_format':  f'#,##0.{p_precision}'})
        table_content_right_bold_format = workbook.add_format({'bold': True, 'align': 'right', 'text_wrap': True, 'font_size': 9, 'top': 2, 'num_format':  f'#,##0.{p_precision}'})

        worksheet = workbook.add_worksheet(_('Rekapitulacija obračuna plaće'))
        worksheet.merge_range('I1:L1', _('Rekapitulacija obračuna plaće'), document_header_center_format)
        worksheet.merge_range('A1:D1', company.name, document_header_left_format)
        worksheet.merge_range('A2:D2', company.street, document_header_left_small_bold_format)
        worksheet.merge_range('A3:D3', self._get_display_city_name(company), document_header_left_small_bold_format)
        worksheet.merge_range('A4:D4', company.country_id.name, document_header_left_small_bold_format)
        worksheet.merge_range('T1:W1', _("IBAN: ") + company.partner_id.bank_ids[0].acc_number, document_header_left_small_bold_format)
        worksheet.merge_range('T2:W2', _("OIB: ") + company.company_registry, document_header_left_small_bold_format)
        worksheet.merge_range('T3:W3', _("Broj zaposlenika: ") + str(number_of_employees), document_header_left_small_format)

        worksheet.merge_range('A6:C6', _('Obračuni'), document_header_left_medium_bold_format)
        worksheet.merge_range('D6:L7', self._get_accountings(runs), document_header_left_medium_format)

        #print tables
        i=9
        worksheet.merge_range(self._get_range('A', 'S', i), _('Rekapitulacija sati'), table_header_left_format)
        worksheet.merge_range(self._get_range('T', 'U', i), _('Sati'), table_header_right_format)
        worksheet.merge_range(self._get_range('V', 'W', i), _('Bruto'), table_header_right_format)
        i=i+1
        for line in payslip_totals:
            if isinstance(line[0],dict):
                if company_lang in line[0]:
                    lang = company_lang
                elif 'en_US' in line[0]:
                    lang = 'en_US'
                else:
                    lang = next(iter(line[0]))

            if(line[5] == 'line'):
                worksheet.merge_range(self._get_range('A', 'S', i), line[0][lang] if isinstance(line[0], dict) and lang in line[0] else line[0], table_content_left_format)
                worksheet.merge_range(self._get_range('T', 'U', i), line[1], table_content_right_format)
                worksheet.merge_range(self._get_range('V', 'W', i), line[2], table_content_right_format)
            elif(line[5] == 'total'):
                worksheet.merge_range(self._get_range('A', 'S', i), line[0], table_content_left_bold_format)
                worksheet.merge_range(self._get_range('T', 'U', i), line[1], table_content_right_bold_format)
                worksheet.merge_range(self._get_range('V', 'W', i), line[2], table_content_right_bold_format)
            i=i+1
        i=i+1

        worksheet.merge_range(self._get_range('A', 'S', i), _('Doprinosi iz plaće'), table_header_left_format)
        worksheet.merge_range(self._get_range('T', 'U', i), _('Stopa'), table_header_right_format)
        worksheet.merge_range(self._get_range('V', 'W', i), _('Iznos'), table_header_right_format)
        i=i+1
        for line in contributions_from_salaries:
            if(line[4] == 'line'):
                worksheet.merge_range(self._get_range('A', 'S', i), line[0][lang] if isinstance(line[0], dict) and lang in line[0] else line[0], table_content_left_format)
                worksheet.merge_range(self._get_range('T', 'U', i), line[1], table_content_right_format)
                worksheet.merge_range(self._get_range('V', 'W', i), line[2], table_content_right_format)
            elif(line[4] == 'total'):
                worksheet.merge_range(self._get_range('A', 'S', i), line[0], table_content_left_bold_format)
                worksheet.merge_range(self._get_range('T', 'U', i), line[1], table_content_right_bold_format)
                worksheet.merge_range(self._get_range('V', 'W', i), line[2], table_content_right_bold_format)
            i=i+1
        i=i+1

        if(work_abroad_hr):
            worksheet.merge_range(self._get_range('A', 'S', i), _('Izaslani rad'), table_header_left_format)
            worksheet.merge_range(self._get_range('T', 'W', i), _('Iznos'), table_header_right_format)
            i=i+1
            for line in work_abroad_hr:
                worksheet.merge_range(self._get_range('A', 'S', i), line[0], table_content_left_format)
                worksheet.merge_range(self._get_range('T', 'W', i), line[2], table_content_right_format)
                i=i+1
            i=i+1

        worksheet.merge_range(self._get_range('A', 'S', i), _('Prihod'), table_header_left_format)
        worksheet.merge_range(self._get_range('T', 'W', i), _('Iznos'), table_header_right_format)
        i=i+1
        for line in income:
            if line[3] != 'IOOD':
                worksheet.merge_range(self._get_range('A', 'S', i), '', table_content_left_format)
                worksheet.merge_range(self._get_range('T', 'W', i), line[2], table_content_right_format)
                i=i+1
        i=i+1

        worksheet.merge_range(self._get_range('A', 'S', i), _('Umanjenje porezne osnovice'), table_header_left_format)
        worksheet.merge_range(self._get_range('T', 'W', i), _('Iznos'), table_header_right_format)
        i=i+1
        for line in income:
            if line[3] != 'DOH':
                worksheet.merge_range(self._get_range('A', 'S', i), line[0][lang] if isinstance(line[0], dict) and lang in line[0] else line[0], table_content_left_bold_format)
                worksheet.merge_range(self._get_range('T', 'W', i), line[2], table_content_right_format)
                i=i+1
        i=i+1

        if(admitted_cost):
            worksheet.merge_range(self._get_range('A', 'S', i), _('Priznati izdatak'), table_header_left_format)
            worksheet.merge_range(self._get_range('T', 'W', i), _('Iznos'), table_header_right_format)
            i=i+1
            for line in admitted_cost:
                worksheet.merge_range(self._get_range('A', 'S', i), line[0], table_content_left_format)
                worksheet.merge_range(self._get_range('T', 'W', i), line[2], table_content_right_format)
                i=i+1
            worksheet.merge_range(self._get_range('A', 'S', i), 'Ukupno', table_content_left_bold_format)
            worksheet.merge_range(self._get_range('T', 'W', i), sum(line[2] for line in admitted_cost), table_content_right_bold_format)
            i=i+1

        worksheet.merge_range(self._get_range('A', 'S', i), _('Porezi'), table_header_left_format)
        worksheet.merge_range(self._get_range('T', 'W', i), _('Iznos'), table_header_right_format)
        i=i+1
        for line in taxes:
            worksheet.merge_range(self._get_range('A', 'S', i), line[0], table_content_left_format)
            worksheet.merge_range(self._get_range('T', 'W', i), line[2], table_content_right_format)
            i=i+1
        for line in neto:
            worksheet.merge_range(self._get_range('A', 'S', i), line[0], table_content_left_bold_format)
            worksheet.merge_range(self._get_range('T', 'W', i), line[2], table_content_right_bold_format)
            i=i+1
        i=i+1

        if(work_abroad_ino):
            worksheet.merge_range(self._get_range('A', 'S', i), _('Izaslani rad'), table_header_left_format)
            worksheet.merge_range(self._get_range('T', 'U', i), _(''), table_header_right_format)
            worksheet.merge_range(self._get_range('V', 'W', i), _('Iznos'), table_header_right_format)
            i=i+1
            for line in work_abroad_ino:
                worksheet.merge_range(self._get_range('A', 'S', i), line[0], table_content_left_format)
                worksheet.merge_range(self._get_range('T', 'W', i), line[2], table_content_right_format)
                i=i+1
            i=i+1

        worksheet.merge_range(self._get_range('A', 'S', i), _('Nadoknade'), table_header_left_format)
        worksheet.merge_range(self._get_range('T', 'U', i), _('Sati'), table_header_right_format)
        worksheet.merge_range(self._get_range('V', 'W', i), _('Iznos'), table_header_right_format)
        i=i+1
        for line in payslip_lines_totals:
            if(line[4] == 'line'):
                worksheet.merge_range(self._get_range('A', 'S', i), line[0][lang] if isinstance(line[0], dict) and lang in line[0] else line[0], table_content_left_format)
                worksheet.merge_range(self._get_range('T', 'U', i), line[1], table_content_right_format)
                worksheet.merge_range(self._get_range('V', 'W', i), line[2], table_content_right_format)
            elif(line[4] == 'total'):
                worksheet.merge_range(self._get_range('A', 'S', i), line[0], table_content_left_bold_format)
                worksheet.merge_range(self._get_range('T', 'U', i), line[1], table_content_right_bold_format)
                worksheet.merge_range(self._get_range('V', 'W', i), line[2], table_content_right_bold_format)
            i=i+1
        i=i+1

        worksheet.merge_range(self._get_range('A', 'S', i), _('Obustave'), table_header_left_format)
        worksheet.merge_range(self._get_range('T', 'W', i), _('Iznos'), table_header_right_format)
        i=i+1
        for line in suspensions:
            if(line[4] == 'line'):
                worksheet.merge_range(self._get_range('A', 'S', i), line[0][lang] if isinstance(line[0], dict) and lang in line[0] else line[0], table_content_left_format)
                worksheet.merge_range(self._get_range('T', 'W', i), line[2], table_content_right_format)
            elif(line[4] == 'total'):
                worksheet.merge_range(self._get_range('A', 'S', i), line[0], table_content_left_bold_format)
                worksheet.merge_range(self._get_range('T', 'W', i), line[2], table_content_right_bold_format)
            i=i+1
        i=i+1

        if payment:
            worksheet.merge_range(self._get_range('A', 'S', i), _('Isplate'), table_header_left_format)
            worksheet.merge_range(self._get_range('T', 'W', i), _('Iznos'), table_header_right_format)
            i=i+1
            for line in payment:
                if(line[4] == 'line'):
                    worksheet.merge_range(self._get_range('A', 'S', i), '', table_content_left_format)
                    worksheet.merge_range(self._get_range('T', 'W', i), line[2], table_content_right_format)
                i=i+1
            i=i+1

        worksheet.merge_range(self._get_range('A', 'S', i), _('Doprinosi na plaće'), table_header_left_format)
        worksheet.merge_range(self._get_range('T', 'U', i), _('Stopa'), table_header_right_format)
        worksheet.merge_range(self._get_range('V', 'W', i), _('Iznos'), table_header_right_format)
        i=i+1
        for line in contributions_on_salaries:
            if(line[4] == 'line'):
                worksheet.merge_range(self._get_range('A', 'S', i), line[0][lang] if isinstance(line[0], dict) and lang in line[0] else line[0], table_content_left_format)
                if line[1] != 0:
                    worksheet.merge_range(self._get_range('T', 'U', i), line[1], table_content_right_format)
                else:
                    worksheet.merge_range(self._get_range('T', 'U', i), '', table_content_right_format)
                worksheet.merge_range(self._get_range('V', 'W', i), line[1], table_content_right_format)

            elif(line[4] == 'total'):
                worksheet.merge_range(self._get_range('A', 'S', i), line[0], table_content_left_bold_format)
                worksheet.merge_range(self._get_range('T', 'U', i), line[1], table_content_right_bold_format)
                worksheet.merge_range(self._get_range('V', 'W', i), line[2], table_content_right_bold_format)
            i=i+1
        i=i+1

        if brutto2:
            worksheet.merge_range(self._get_range('A', 'S', i), _('Ukupni trošak plaće'), table_header_left_format)
            worksheet.merge_range(self._get_range('T', 'W', i), _('Iznos'), table_header_right_format)
            i=i+1
            for line in brutto2:
                worksheet.merge_range(self._get_range('A', 'S', i), '', table_content_left_format)
                worksheet.merge_range(self._get_range('T', 'W', i), line[0], table_content_right_format)
                i=i+1
            i=i+1

        worksheet.merge_range(self._get_range('A', 'W', i), _('Rekapitulacija poreza'), table_header_left_format)
        i=i+1
        worksheet.merge_range(self._get_range('A', 'U', i), _('Općina/Grad'), table_header_left_format)
        worksheet.merge_range(self._get_range('V', 'W', i), _('Ukupno'), table_header_right_format)
        i=i+1
        for line in local_tax:
            worksheet.merge_range(self._get_range('A', 'U', i), line['city_name'], table_content_left_bold_format)
            worksheet.merge_range(self._get_range('V', 'W', i), line['amount'], table_content_right_bold_format)
            i=i+1
        for line in local_tax_sum:
            worksheet.merge_range(self._get_range('A', 'S', i), _('Ukupno'), table_content_left_bold_format)
            worksheet.merge_range(self._get_range('T', 'W', i), line[0], table_content_right_bold_format)
            i=i+1

    def _get_display_city_name(self, company):
        return (f"{company.city_id.zipcode} {company.city_id.name}")

    def _get_company_iban(self, company):
        if company.partner_id.bank_ids:
            return company.partner_id.bank_ids[0].acc_number

    def _get_accountings(self, runs):
        name = runs[0].name
        for run in runs[1:]:
            name = f"{name}, {run.name}"
        return name

    def _get_range(self, first_column, second_column, row_no):
        return f"{first_column}{row_no}:{second_column }{row_no}"
