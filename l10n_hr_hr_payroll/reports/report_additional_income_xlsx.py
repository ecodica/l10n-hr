from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import json

class HrAdditionalIncomeReportXLSX(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.additional_income_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Additional Income XLSX Report"

    def generate_xlsx_report(self, workbook, data, report_book):
        self = self.with_context(lang=self.env.user.lang)
        obj_name = 'hr.employee'
        emp_obj = self.env[obj_name]
        pdf_report_obj = self.env['report.l10n_hr_hr_payroll.report_additional_income']
        employe_lines_obj = self.env['additional.income.report.wizard.employee.line']
        year_id = data['year_id']
        year = pdf_report_obj.env['account.fiscal.year'].browse(year_id)
        print_date = data['print_date']
        emp_ids = data['employee_ids']
        employee_ids = self.env['hr.employee'].browse(data['employee_ids'])
        company = self.env['res.company'].browse(data['company'])
        add_income_data = pdf_report_obj.get_additional_income_data(year, emp_ids)
        emp_lines = pdf_report_obj.group_data_by_employee(add_income_data)
        emp_data = {}
        emps = []
        for key in emp_lines:
            emp = emp_obj.browse(key)
            emp_data.update({
                key: {
                    'name': emp.name,
                    'address': pdf_report_obj.get_employee_address(emp),
                    'oib': emp.oib,
                    'slip_lines': emp_lines[key],
                }
            })
            emps.append(emp)
        
        currency_precision = self.env.user.company_id.currency_id.decimal_places
        p_precision = '0'*currency_precision
        header_center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'text_wrap': 1, 'font_size': 11})
        table_bold_left_bg_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'bg_color': '#BBBBBB'})
        table_center_bg_format = workbook.add_format({'align': 'center', 'text_wrap': 1, 'valign': 'vbottom', 'border': 1, 'bg_color': '#BBBBBB'})
        table_left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1})
        table_center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        table_right_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'border': 1})
        table_bold_right_format = workbook.add_format({'bold': 1, 'align': 'right', 'valign': 'vcenter', 'border': 1})
        table_bold_center_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        signature_top_format = workbook.add_format({'align': 'center', 'valign': 'vbottom', 'text_wrap': True, 'font_size': 9, 'top': 1})
        signature_line_center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 9, 'bottom': 1})
        signature_center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 9})
        num_table_right_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'border': 1, 'num_format':  f'#,##0.{p_precision}'})
        num_table_bold_right_format = workbook.add_format({'bold': 1, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'num_format':  f'#,##0.{p_precision}'})

        for e in employee_ids:
            worksheet = workbook.add_worksheet(_('Drugi dohodak ') + e.name)
            worksheet.merge_range('B1:G1', _('Payer\'s name'), table_bold_left_bg_format)
            worksheet.merge_range('H1:L1', company.name, table_left_format)
            worksheet.merge_range('B2:G2', _('Payer\'s address'), table_bold_left_bg_format)
            worksheet.merge_range('H2:L2', self._get_company_address(company), table_left_format)
            worksheet.merge_range('B3:G3', _('OIB'), table_bold_left_bg_format)
            worksheet.merge_range('H3:L3', company.company_registry, table_left_format)
            worksheet.merge_range('N1:S1', _('Tax payer\'s name'), table_bold_left_bg_format)
            worksheet.merge_range('T1:X1', e.name, table_left_format)
            worksheet.merge_range('N2:S2', _('Tax payer\'s address'), table_bold_left_bg_format)
            worksheet.merge_range('T2:X2', self._get_employee_address(e), table_left_format)
            worksheet.merge_range('N3:S3', _('OIB'), table_bold_left_bg_format)
            worksheet.merge_range('T3:X3', e.company_registry, table_left_format)
            worksheet.merge_range('B4:X5', _('CONFIRMATION OF PAID RECEIPT, INCOME, PAID CONTRIBUTION, INCOME TAX AND SURTAX IN ') + year.display_name + _('. YEAR'), header_center_format)
            worksheet.merge_range('B6:B8', _('Row No.'), table_center_bg_format)
            worksheet.merge_range('C6:D8',  _('Date of receipt payment'), table_center_bg_format)
            worksheet.merge_range('E6:F8', _('Basis of the receipt'), table_center_bg_format)
            worksheet.merge_range('G6:H8', _('Receipt amount'), table_center_bg_format)
            worksheet.merge_range('I6:J8', _('Outlay percentage'), table_center_bg_format)
            worksheet.merge_range('K6:L8', _('Outlay amount'), table_center_bg_format)
            worksheet.merge_range('M6:N8', _('Paid contribution from receipt amount'), table_center_bg_format)
            worksheet.merge_range('O6:P8', _('Income'), table_center_bg_format)
            worksheet.merge_range('Q6:R8', _('Date of tax and surtax contribution payment'), table_center_bg_format)
            worksheet.merge_range('S6:T8', _('Tax and surtax amount paid'), table_center_bg_format)
            worksheet.merge_range('U6:V8', _('Net payment'), table_center_bg_format)
            worksheet.merge_range('W6:X8', _('Receipt mark'), table_center_bg_format)

            worksheet.write('B9', _('1'), table_center_bg_format)
            worksheet.merge_range('C9:D9',  _('2'), table_center_bg_format)
            worksheet.merge_range('E9:F9', _('3'), table_center_bg_format)
            worksheet.merge_range('G9:H9', _('4'), table_center_bg_format)
            worksheet.merge_range('I9:J9', _('5'), table_center_bg_format)
            worksheet.merge_range('K9:L9', _('6'), table_center_bg_format)
            worksheet.merge_range('M9:N9', _('7'), table_center_bg_format)
            worksheet.merge_range('O9:P9', _('8 (4-6-7)'), table_center_bg_format)
            worksheet.merge_range('Q9:R9', _('9'), table_center_bg_format)
            worksheet.merge_range('S9:T9', _('10'), table_center_bg_format)
            worksheet.merge_range('U9:V9', _('11'), table_center_bg_format)
            worksheet.merge_range('W9:X9', _('12'), table_center_bg_format)
            i = 10
            row = 1
            for line in emp_data[e.id]['slip_lines']:
                worksheet.write('B' + str(i), str(row) + '.', table_center_format)
                worksheet.merge_range('C' + str(i) + ':D' + str(i), self._set_date_format(line['date_paid']), table_center_format)
                worksheet.merge_range('E' + str(i) + ':F' + str(i), _('SECOND INCOME'), table_center_format)
                worksheet.merge_range('G' + str(i) + ':H' + str(i), line['primitak'], num_table_right_format)
                worksheet.merge_range('I' + str(i) + ':J' + str(i), self._set_currency_decimal(line['izdatak_pct']), table_center_format)
                worksheet.merge_range('K' + str(i) + ':L' + str(i), line['izdatak'], num_table_right_format)
                worksheet.merge_range('M' + str(i) + ':N' + str(i), line['doprinosi'], num_table_right_format)
                worksheet.merge_range('O' + str(i) + ':P' + str(i), line['dohodak'], num_table_right_format)
                worksheet.merge_range('Q' + str(i) + ':R' + str(i), self._set_date_format(line['date_paid']), table_center_format)
                worksheet.merge_range('S' + str(i) + ':T' + str(i), line['porez'], num_table_right_format)
                worksheet.merge_range('U' + str(i) + ':V' + str(i), line['isplata'], num_table_right_format)
                worksheet.merge_range('W' + str(i) + ':X' + str(i), line['oznaka_primitka'], table_center_format)
                i+=1
                row+=1
            worksheet.merge_range('B' + str(i) + ':F' + str(i), _('Total'), table_bold_right_format)
            worksheet.merge_range('G' + str(i) + ':H' + str(i), sum([line['primitak'] for line in emp_data[e.id]['slip_lines']]), num_table_bold_right_format)
            worksheet.merge_range('I' + str(i) + ':J' + str(i), '', table_bold_right_format)
            worksheet.merge_range('K' + str(i) + ':L' + str(i), sum([line['izdatak'] for line in emp_data[e.id]['slip_lines']]), num_table_bold_right_format)
            worksheet.merge_range('M' + str(i) + ':N' + str(i), sum([line['doprinosi'] for line in emp_data[e.id]['slip_lines']]), num_table_bold_right_format)
            worksheet.merge_range('O' + str(i) + ':P' + str(i), sum([line['dohodak'] for line in emp_data[e.id]['slip_lines']]), num_table_bold_right_format)
            worksheet.merge_range('Q' + str(i) + ':R' + str(i), '', table_bold_right_format)
            worksheet.merge_range('S' + str(i) + ':T' + str(i), sum([line['porez'] for line in emp_data[e.id]['slip_lines']]), num_table_bold_right_format)
            worksheet.merge_range('U' + str(i) + ':V' + str(i), sum([line['isplata'] for line in emp_data[e.id]['slip_lines']]), num_table_bold_right_format)
            worksheet.merge_range('W' + str(i) + ':X' + str(i), '', table_bold_right_format)
            
            i+=3
            worksheet.merge_range('C' + str(i) + ':D' + str(i), _('DATE'), signature_center_format)
            worksheet.merge_range('E' + str(i) + ':G' + str(i), self._set_date_format(print_date), signature_line_center_format)
            i+=1
            worksheet.merge_range('Q' + str(i) + ':U' + str(i), _('PAYER\'S SIGNATURE'), signature_top_format)

    def _get_company_address(self, company):
        if(company.city_id):
            return(company.city_id.name + ', ' + company.street)
        return ''

    def _get_employee_address(self, emp):
        if(emp.city):
            return(emp.city.name + ', ' + emp.street)
        return ''

    def _set_currency_decimal(self, amount):
        amount = float(amount)
        amount = '{:,.2f}'.format(amount)
        maketrans = amount.maketrans
        final_amount = amount.translate(maketrans(',.', '.,'))
        return str(final_amount)

    def _set_date_format(self, date):
        datetime_object = datetime.strptime(str(date), '%Y-%m-%d')
        return datetime_object.strftime('%d.%m.%Y')