from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import json

class HrFeesEarningXSLX(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.hr_payslip_fees_earning_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Fees Earning XLSX Report"

    def generate_xlsx_report(self, workbook, data, report_book):
        self = self.with_context(lang=self.env.user.lang)
        pdf_report_obj = self.env['report.l10n_hr_hr_payroll.report_fees_earnings']
        payslip_runs = self.env['hr.payslip.run'].search([('id', 'in', data['run_ids'])])
        company = payslip_runs[0].company_id
        if data['department_id']:
            department = [self.env['hr.department'].search([('id', '=', data['department_id'])]).id]
        else:
            department = str(self.env['hr.department'].search([]).ids)
        report_type = data['type']

        employees_data, sums = pdf_report_obj.get_payslip_lines(payslip_runs, report_type, department)
        company_lang = self.env.user.company_id.partner_id.lang
        company_data = pdf_report_obj.get_company_data(company)
        currency_precision = self.env.user.company_id.currency_id.decimal_places
        p_precision = '0'*currency_precision
        title = pdf_report_obj.get_title(report_type)

        document_header_center_bold_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'vcenter','text_wrap': True, 'font_size': 12})
        document_header_left_bold_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 12})
        document_header_left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 12})
        table_header_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 12, 'border': 1, 'left': 0, 'right': 0, 'bg_color': '#add8e6'})
        table_content_format = workbook.add_format({'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 12})
        table_content_bold_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 12, 'num_format':  f'#,##0.{p_precision}'})
        table_content_number_format = workbook.add_format({'align': 'right', 'valign': 'vcenter','text_wrap': True, 'font_size': 12, 'num_format':  f'#,##0.{p_precision}'})
        table_content_number_bold_format = workbook.add_format({'bold': 1, 'align': 'right', 'valign': 'vcenter','text_wrap': True, 'font_size': 12, 'num_format':  f'#,##0.{p_precision}'})
        table_row_number = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 12, 'border': 1, 'right': 0, 'bg_color': '#add8e6'})
        table_sum_header_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 12, 'border': 1, 'bg_color': '#add8e6'})
        table_heder_right_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 12, 'border': 1, 'left': 0, 'bg_color': '#add8e6'})

        
        worksheet = workbook.add_worksheet(title)
        worksheet.merge_range('B1:E1', company.name, document_header_left_bold_format)
        worksheet.merge_range('B2:I2', self._get_display_city_name(company), document_header_left_format)
        worksheet.merge_range('B3:E3', _('OIB: ') + company.company_registry, document_header_left_format)
        worksheet.merge_range('S3:V3', _('Financijski iznosi u ') + company.currency_id.name, document_header_left_format)
        worksheet.merge_range('J5:N5', title, document_header_center_bold_format)
        worksheet.merge_range('B7:D7', _('Obračuni plaće:'), document_header_left_bold_format)
        k = 8
        for slip in payslip_runs:
            worksheet.merge_range('B' + str(k) + ':F' + str(k), slip.name, document_header_left_format)
            worksheet.merge_range('P' + str(k) + ':R' + str(k), self._get_date_period(slip)[0], document_header_left_format)
            worksheet.merge_range('T' + str(k) + ':V' + str(k), self._get_date_period(slip)[1], document_header_left_format)
            k = k + 1
        i = 9 + len(payslip_runs)
        j = 1
        lang = False
        for emp in employees_data:  
            worksheet.merge_range('B' + str(i) + ':D' + str(i), str(j) + ".", table_row_number)
            worksheet.merge_range('E' + str(i) + ':S' + str(i), employees_data[emp]['name'], table_header_format)
            worksheet.merge_range('T' + str(i) + ':V' + str(i), "", table_heder_right_format)
            i=i+1
            j=j+1
            worksheet.merge_range('B' + str(i) + ':D' + str(i),  _('Šifra'), table_content_bold_format)
            worksheet.merge_range('E' + str(i) + ':L' + str(i),  _('Naziv stavke'), table_content_bold_format)
            worksheet.merge_range('M' + str(i) + ':P' + str(i),  _('Broj sati'), table_content_number_bold_format)
            worksheet.merge_range('Q' + str(i) + ':V' + str(i),  _('Iznos'), table_content_number_bold_format)
            worksheet.merge_range('B' + str(i+1) + ':D' + str(i+1),  employees_data[emp]['line'][0][0], table_content_format)
            i=i+1
            for line in employees_data[emp]['line']:
                if isinstance(line[2],dict):
                    if company_lang in line[2]:
                        lang = company_lang
                    elif 'en_US' in line[2]:
                        lang = 'en_US'
                    else:
                        lang = next(iter(line[2]))
                worksheet.merge_range('E' + str(i) + ':L' + str(i), line[2][lang] if isinstance(line[2], dict) and lang in line[2] else line[2], table_content_format) 
                worksheet.merge_range('M' + str(i) + ':P' + str(i), line[3], table_content_number_format)
                worksheet.merge_range('Q' + str(i) + ':V' + str(i), line[4], table_content_number_format)
                i=i+1
            worksheet.merge_range('E' + str(i) + ':L' + str(i), _('Ukupno'), table_content_bold_format)
            worksheet.merge_range('M' + str(i) + ':P' + str(i), sum(float(line[3] or 0) for line in employees_data[emp]['line']), table_content_number_bold_format)
            worksheet.merge_range('Q' + str(i) + ':V' + str(i), sum(float(line[4] or 0) for line in employees_data[emp]['line']), table_content_number_bold_format)
            i+=2

        worksheet.merge_range('B' + str(i) + ':V' + str(i), _('Suma po stavkama'), table_sum_header_format)
        i=i+1
        worksheet.merge_range('B' + str(i) + ':L' + str(i),  _('Naziv stavke'), table_content_bold_format)
        worksheet.merge_range('M' + str(i) + ':P' + str(i),  _('Broj sati'), table_content_number_bold_format)
        worksheet.merge_range('Q' + str(i) + ':V' + str(i),  _('Iznos'), table_content_number_bold_format)
        i=i+1
        total_hours_sum = 0.00
        total_amount_sum = 0.00
        for suma in sums:
            worksheet.merge_range('B' + str(i) + ':L' + str(i), suma, table_content_format)
            worksheet.merge_range('M' + str(i) + ':P' + str(i), sums[suma]['hours'], table_content_number_format)
            worksheet.merge_range('Q' + str(i) + ':V' + str(i), sums[suma]['amount'], table_content_number_format)
            total_hours_sum = total_hours_sum + sums[suma]['hours']
            total_amount_sum = total_amount_sum + sums[suma]['amount']
            i=i+1
        worksheet.merge_range('B' + str(i) + ':L' + str(i), _("Ukupno"), table_content_bold_format)
        worksheet.merge_range('M' + str(i) + ':P' + str(i), total_hours_sum, table_content_number_bold_format)
        worksheet.merge_range('Q' + str(i) + ':V' + str(i), total_amount_sum, table_content_number_bold_format)
            
    
    def _get_display_city_name(self, company_id):
        return f"{company_id.street}, {company_id.zip}, {company_id.city_id.name}, {company_id.country_id.name}"

    def _get_company_iban(self, company_id):
        if company_id.partner_id.bank_ids:
            return company_id.partner_id.bank_ids[0].acc_number
        return ""

    def _get_date_period(self, payslip):
        if payslip:
            from_date = _("Od datuma: ") + str(self._set_date_format(payslip.date_start))
            to_date = _("Do datuma: ") + str(self._set_date_format(payslip.date_end))
            return (from_date, to_date)
        return ""   

    def _set_date_format(self, date):
        datetime_object = datetime.strptime(str(date), '%Y-%m-%d')
        return datetime_object.strftime('%d.%m.%Y')