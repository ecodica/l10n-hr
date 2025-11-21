from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import json

class HrIPFormReportXSLX(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_ip_form_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "IP Form XLSX Report"

    def generate_xlsx_report(self, workbook, data, report_book):
        self = self.with_context(lang=self.env.user.lang)
        self.model = self.env.context.get('active_model')
        pdf_report_obj = self.env['report.report_ip_form']
        reports_common_obj = self.env['hr.hr.payroll.reports.common']
        year = data['year']
        date = data['date']
        company_id = self.env['res.company'].browse(data['company_id'])
        emp_list = self.env['hr.employee'].browse(data['employee_ids'])
        report_data = {}
        for emp in emp_list:
            report_data.update({
                emp.id: {
                    'report_data': pdf_report_obj.get_report_data(emp, year, date),
                    'address': reports_common_obj.get_employee_address(emp),
                }
            })

        i = 1

        currency_precision = self.env.user.company_id.currency_id.decimal_places
        p_precision = '0'*currency_precision
        document_header_left_large_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 12})
        document_header_left_small_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 9})
        table_left_bold_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 9, 'border': 1})
        table_left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter','text_wrap': True, 'font_size': 9, 'border': 1})
        table_center_bold_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'vcenter','text_wrap': True, 'font_size': 9, 'border': 1})
        table_center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter','text_wrap': True, 'font_size': 9, 'border': 1})
        table_right_bold_format = workbook.add_format({'bold': 1, 'align': 'right', 'valign': 'vcenter','text_wrap': True, 'font_size': 9, 'border': 1, 'num_format':  f'#,##0.{p_precision}'})
        table_right_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 9, 'border': 1, 'num_format':  f'#,##0.{p_precision}'})
        signature_top_format = workbook.add_format({'align': 'center', 'valign': 'vtop', 'text_wrap': True, 'font_size': 9, 'top': 1})
        signature_left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 9})
        signature_center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 9, 'bottom': 1})


        for emp in emp_list:
            e = report_data[emp.id]
            data = e['report_data']
            worksheet = workbook.add_worksheet(_('IP obrazac - ') + emp.name)

            worksheet.merge_range('B1:D1', company_id.name, document_header_left_large_format)
            worksheet.merge_range('B2:D2', _('IP obrazac'), document_header_left_small_format)

            worksheet.merge_range('B3:J3', _('I. PODACI O POSLODAVCU, ISPLATITELJU PLAĆE ILI MIROVINE'), table_left_bold_format)
            worksheet.merge_range('K3:S3', _('II. Info about employee, pensioner, person receiving salary'), table_left_bold_format)

            worksheet.merge_range('B4:J4', _('IME I PREZIME: ') + company_id.name, table_left_format)
            worksheet.merge_range('K4:S4', _('1. NAZIV/IME I PREZIME: ') + emp.name, table_left_format)

            worksheet.merge_range('B5:J5', _('2. ADRESA: ') + self._get_company_address(company_id), table_left_format)
            worksheet.merge_range('K5:S5', _('2. ADRESA: ') + self._get_employee_address(emp), table_left_format)

            worksheet.merge_range('B6:J6', _('3. OIB: ') + company_id.company_registry, table_left_format)
            worksheet.merge_range('K6:S6', _('3. OIB: ') + emp.oib, table_left_format)
            
            worksheet.merge_range('B7:M7', _('III. Info about salary, pension, contributions, tax and surtax for ') + str(year) + _('. year'), table_left_bold_format)
            worksheet.merge_range('N7:S7', _('Identifier'), table_left_bold_format)

            worksheet.merge_range('B8:C8', _('Payment month'), table_center_bold_format)
            worksheet.merge_range('D8:E8', _('Šifra grada'), table_center_bold_format)
            worksheet.merge_range('F8:G8', _('Paid salary'), table_center_bold_format)
            worksheet.merge_range('H8:J8', _('Salary contributions paid'), table_center_bold_format)
            worksheet.write('K8', _('Prihod'), table_center_bold_format)
            worksheet.merge_range('L8:M8', _('Personal deduction'), table_center_bold_format)
            worksheet.merge_range('N8:O8', _('Por. osn.'), table_center_bold_format)
            worksheet.merge_range('P8:Q8', _('Porez i prirez'), table_center_bold_format)
            worksheet.merge_range('R8:S8', _('Net payment'), table_center_bold_format)
            i=9

            for line in data:
                worksheet.merge_range('B' + str(i) + ':C' + str(i), line[0], table_center_format)
                worksheet.merge_range('D' + str(i) + ':E' + str(i), line[1], table_center_format)
                worksheet.merge_range('F' + str(i) + ':G' + str(i), line[2], table_right_format)
                worksheet.merge_range('H' + str(i) + ':J' + str(i), line[3], table_right_format)
                worksheet.write('K' + str(i),  line[4], table_right_format)
                worksheet.merge_range('L' + str(i) + ':M' + str(i), line[5], table_right_format)
                worksheet.merge_range('N' + str(i) + ':O' + str(i), line[6], table_right_format)
                worksheet.merge_range('P' + str(i) + ':Q' + str(i), line[7], table_right_format)
                worksheet.merge_range('R' + str(i) + ':S' + str(i), line[8], table_right_format)
                i+=1

            worksheet.merge_range('B' + str(i) + ':E' + str(i), _('Total'), table_center_bold_format)
            worksheet.merge_range('F' + str(i) + ':G' + str(i), sum([line[2] for line in data]), table_right_bold_format)
            worksheet.merge_range('H' + str(i) + ':J' + str(i), sum([line[3] for line in data]), table_right_bold_format)
            worksheet.write('K' + str(i), sum([line[4] for line in data]), table_right_bold_format)
            worksheet.merge_range('L' + str(i) + ':M' + str(i), sum([line[5] for line in data]), table_right_bold_format)
            worksheet.merge_range('N' + str(i) + ':O' + str(i), sum([line[6] for line in data]), table_right_bold_format)
            worksheet.merge_range('P' + str(i) + ':Q' + str(i), sum([line[7] for line in data]), table_right_bold_format)
            worksheet.merge_range('R' + str(i) + ':S' + str(i), sum([line[8] for line in data]), table_right_bold_format)

            i+=4

            worksheet.merge_range('B' + str(i) + ':D' + str(i), _('COMPILATION DATE:'), signature_left_format)
            worksheet.merge_range('E' + str(i) + ':F' + str(i), self._set_date_format(date), signature_center_format)
            i+=1
            worksheet.merge_range('K' + str(i) + ':M' + str(i), _('Payer signature'), signature_top_format)


    def _get_company_address(self, company):
        return str(company.city_id.name) + ', ' + str(company.street)

    def _get_employee_address(self, employee):
        return str(employee.city.name) + ', ' + str(employee.street)

    def _set_date_format(self, date):
        datetime_object = datetime.strptime(date, '%Y-%m-%d')
        return datetime_object.strftime('%d.%m.%Y')