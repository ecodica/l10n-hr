from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import json

class HrTaxCityReportXSLX(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_tax_city_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Tax City XLSX Report"

    def generate_xlsx_report(self, workbook, data, report_book):
        self = self.with_context(lang=self.env.user.lang)
        pdf_report_obj = self.env['report.l10n_hr_hr_payroll.report_tax_city']
        payslip_runs = self.env['hr.payslip.run'].search([('id', 'in', data.get('run_ids',report_book.ids))])
        if data.get('department_id',False):
            department = [self.env['hr.department'].search([('id', '=', data['department_id'])]).id]
        else:
            department = str(self.env['hr.department'].search([]).ids)
        company = payslip_runs[0].company_id
        payslips = pdf_report_obj.group_data(pdf_report_obj.get_lines(payslip_runs, department))
        payslips_sums = pdf_report_obj.get_lines_sum(payslip_runs, department)
        company_data = pdf_report_obj.get_company_data(company)

        worksheet = workbook.add_worksheet(_('Tax city'))
        currency_precision = self.env.user.company_id.currency_id.decimal_places
        p_precision = '0'*currency_precision
        document_header_name_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 9, 'bg_color': '#cee6f2'})
        document_header_left_small_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 9, 'bg_color': '#cee6f2'})
        date_left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 8})
        document_header_right_small_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 9, 'bg_color': '#cee6f2'})
        document_header_blank_format = workbook.add_format({'bg_color': '#cee6f2'})
        name_center_bold_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9})
        left_bold_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 9})
        name_center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_size': 8})
        table_blue_header_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9, 'bg_color': '#ADD8E6'})
        table_left_bold_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 9, 'border': 1})
        table_left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 9, 'border': 1})
        table_right_bold_format = workbook.add_format({'bold': 1, 'align': 'right', 'valign': 'vcenter','text_wrap': True, 'font_size': 9, 'border': 1, 'num_format':  f'#,##0.{p_precision}'})
        table_right_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 9, 'border': 1, 'num_format':  f'#,##0.{p_precision}'})
        
        worksheet.merge_range('B1:E1', company_data['name'], document_header_name_format)
        worksheet.merge_range('F1:M1', '', document_header_blank_format)
        worksheet.merge_range('B2:M2', company_data['address'], document_header_left_small_format)
        worksheet.merge_range('B3:E3', _('OIB: ') + company_data['oib'], document_header_left_small_format)
        worksheet.merge_range('F3:J3', '', document_header_blank_format)
        worksheet.merge_range('K3:M3', _('Financijski iznosi u ') + company.currency_id.name, document_header_left_small_format)
        worksheet.merge_range('E4:J4', _('Porezi po općinama'), name_center_bold_format)
        worksheet.merge_range('B6:D6', _('Obračuni plaće:'), left_bold_format)
        k = 7
        for slip in payslip_runs:
            worksheet.merge_range('B' + str(k) + ':G' + str(k), slip.display_name, date_left_format)
            worksheet.merge_range('I' + str(k) + ':J' + str(k), _('Od datuma: ') + self._set_date_format(str(slip.date_start)), date_left_format)
            worksheet.merge_range('L' + str(k) + ':M' + str(k), _('Do datuma: ') + self._set_date_format(str(slip.date_end)), date_left_format)
            k+=1
        i = 8 + len(payslip_runs) 
        for city, slip in payslips.items():
            rowNo = 1
            worksheet.merge_range('B' + str(i) + ':M' + str(i), city, table_blue_header_format)
            i+=1
            worksheet.write('B' + str(i), _('Row no.'), table_left_bold_format)
            worksheet.merge_range('C' +str(i) + ':E' + str(i), _('Prezime i ime'), table_left_bold_format)
            worksheet.merge_range('F' +str(i) + ':G' + str(i), _('OIB'), table_left_bold_format)
            worksheet.merge_range('H' +str(i) + ':K' + str(i), _('Porez'), table_right_bold_format)
            worksheet.merge_range('L' +str(i) + ':M' + str(i), _('Ukupno'), table_right_bold_format)
            i+=1
            for line in slip['line']:
                worksheet.write('B' + str(i), str(rowNo), table_left_format)
                worksheet.merge_range('C' +str(i) + ':E' + str(i), line[1], table_left_format)
                worksheet.merge_range('F' +str(i) + ':G' + str(i), line[2], table_left_format)
                worksheet.merge_range('H' +str(i) + ':K' + str(i), line[3], table_right_format)
                worksheet.merge_range('L' +str(i) + ':M' + str(i), line[5], table_right_format)
                rowNo+=1
                i+=1
            worksheet.write('B' + str(i), '', table_left_bold_format)
            worksheet.merge_range('C' +str(i) + ':G' + str(i), _('Total'), table_left_bold_format)
            worksheet.merge_range('H' +str(i) + ':K' + str(i), slip['total'][3], table_right_bold_format)
            worksheet.merge_range('L' +str(i) + ':M' + str(i), slip['total'][5], table_right_bold_format)
            i+=1
        
        i+=1
        worksheet.merge_range('B' + str(i) + ':M' + str(i), _('Suma svih gradova'), table_blue_header_format)
        i+=1
        worksheet.merge_range('B' + str(i) + ':I' + str(i), _('Porez'), table_right_bold_format)
        worksheet.merge_range('J' + str(i) + ':M' + str(i), _('Ukupono'), table_right_bold_format)
        i+=1
        worksheet.merge_range('B' + str(i) + ':I' + str(i),  payslips_sums[0][0], table_right_format)
        worksheet.merge_range('J' + str(i) + ':M' + str(i),  payslips_sums[0][2], table_right_format)

    def _set_date_format(self, date):
        datetime_object = datetime.strptime(date, '%Y-%m-%d')
        return datetime_object.strftime('%d.%m.%Y')
