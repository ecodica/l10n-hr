from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from datetime import datetime


class HrEmployeeRecapReportXSLX(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_employee_recap_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Employee Recap XLSX Report"

    def generate_xlsx_report(self, workbook, data, report_book):
        self = self.with_context(lang=self.env.user.lang)
        pdf_report_obj = self.env['report.l10n_hr_hr_payroll.report_employee_recap']
        data['active_ids'] = data.get('run_ids') or [report_book.id]
        report_data = pdf_report_obj._get_report_values([], data)
        lines_total = report_data.get('emp_lines')
        company = report_data.get('company')
        period = report_data.get('period')
        Common = self.env['hr.hr.payroll.reports.common.xlsx']
        runs = self.env['hr.payslip.run'].browse(data.get('run_ids', report_book.ids))

        currency_precision = company.currency_id.decimal_places
        p_precision = '0'*currency_precision
        worksheet = workbook.add_worksheet(_('REKAPITULACIJA PLAĆA PO DJELATNICIMA ZA OBRAČUNE'))
        worksheet.set_column(4, 19, 11)
        worksheet.set_column(13, 14, 8)
        document_header_center_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'top','text_wrap': True, 'font_size': 12})
        document_header_left_format = workbook.add_format({'align': 'left', 'valign': 'top','text_wrap': True, 'font_size': 12})
        document_header_left_small_format = workbook.add_format({'align': 'left', 'valign': 'top','text_wrap': True, 'font_size': 9})
        document_period_format = workbook.add_format({'align': 'center', 'valign': 'top','text_wrap': True, 'font_size': 9})
        header_format = workbook.add_format({'bold': 1, 'align': 'right', 'valign': 'top','text_wrap': True, 'font_size': 9, 'border': 1, 'bg_color': '#D3D3D3'})
        content_format = workbook.add_format({'align': 'right', 'valign': 'top','text_wrap': True, 'font_size': 9, 'border': 1})
        currency_format = workbook.add_format({'font_size': 9, 'align': 'right', 'valign': 'top', 'border': 1, 'num_format':  f'#,##0.{p_precision}'})
        name_format = workbook.add_format({'align': 'center', 'valign': 'top', 'text_wrap': True, 'font_size': 9, 'border': 1})
        name_header_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'top','text_wrap': True, 'font_size': 9, 'border': 1, 'bg_color': '#D3D3D3'})
        total_amount_title_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'top','text_wrap': True, 'font_size': 9, 'border': 1})

        worksheet.merge_range('B1:E1', company.name, document_header_left_format)
        worksheet.merge_range('B2:E2', company.street, document_header_left_small_format)
        worksheet.merge_range('B3:E3', Common._get_display_city_name(company), document_header_left_small_format)
        worksheet.merge_range('B4:E4', company.country_id.name, document_header_left_small_format)
        worksheet.merge_range('B5:E5', _('OIB: ') + company.company_registry, document_header_left_small_format)
        worksheet.merge_range('B6:E6', _('IBAN: ') + self._get_company_iban(company), document_header_left_small_format)
        worksheet.merge_range('H1:N1', _('REKAPITULACIJA PLAĆA PO DJELATNICIMA ZA OBRAČUNE'), document_header_center_format)
        worksheet.merge_range('H2:N2', self._get_date_period(period), document_period_format)

        i = 3
        for run in runs:
            worksheet.merge_range('H' + str(i) + ':N' + str(i), run.display_name, document_period_format)
            i+=1

        j = 8
        if (i > j):
            j = i+1

        worksheet.write('B' + str(j), _('R.Br.'), header_format)
        worksheet.write('C' + str(j), _('Šifra'), name_header_format)
        worksheet.write('D' + str(j), _('Ime'), name_header_format)
        worksheet.write('E' + str(j), _('Prezime'), name_header_format)
        worksheet.merge_range(Common._get_range('F','G',j), _('Naziv'), name_header_format)
        worksheet.write('H' + str(j), _('Bruto plaća'), header_format)
        worksheet.write('I' + str(j), _('MIO I'), header_format)
        worksheet.write('J' + str(j), _('MIO II'), header_format)
        worksheet.write('K' + str(j), _('Prihod'), header_format)
        worksheet.write('L' + str(j), _('Por. osn.'), header_format)
        worksheet.write('M' + str(j), _('Porez'), header_format)
        worksheet.write('N' + str(j), _('Neto plaća'), header_format)
        worksheet.write('O' + str(j), _('Obustave'), header_format)
        worksheet.write('P' + str(j), _('Neto dodaci'), header_format)
        worksheet.write('Q' + str(j), _('Isplate'), header_format)
        worksheet.write('R' + str(j), _('Doprinosi na plaću'), header_format)
        worksheet.write('S' + str(j), _('Ukupni trošak plaće'), header_format)
        j+=1

        for line in lines_total:
            worksheet.write('B' + str(j), line['row'], content_format)
            worksheet.write('C' + str(j), line['emp_code'], name_format)
            worksheet.write('D' + str(j), line['emp_first_name'], name_format)
            worksheet.write('E' + str(j), line['emp_last_name'], name_format)
            worksheet.merge_range(Common._get_range('F','G',j), line['emp_name'], name_format)
            worksheet.write('H' + str(j), line['osnovica'], currency_format)
            worksheet.write('I' + str(j), line['mio1'], currency_format)
            worksheet.write('J' + str(j), line['mio2'], currency_format)
            worksheet.write('K' + str(j), line['doh'], currency_format)
            worksheet.write('L' + str(j), line['porosn'], currency_format)
            worksheet.write('M' + str(j), line['pdoh'], currency_format)
            worksheet.write('N' + str(j), line['neto'], currency_format)
            worksheet.write('O' + str(j), line['obs'], currency_format)
            worksheet.write('P' + str(j), line['dodn'], currency_format)
            worksheet.write('Q' + str(j), line['ispl'], currency_format)
            worksheet.write('R' + str(j), line['dopna'], currency_format)
            worksheet.write('S' + str(j), line['brutto2'], currency_format)
            j+=1
        
        worksheet.merge_range(Common._get_range('B','G',j), _('Total:'), total_amount_title_format)
        worksheet.write('H' + str(j), sum([line['osnovica'] for line in lines_total]), currency_format)
        worksheet.write('I' + str(j), sum([line['mio1'] for line in lines_total]), currency_format)
        worksheet.write('J' + str(j), sum([line['mio2'] for line in lines_total]), currency_format)
        worksheet.write('K' + str(j), sum([line['doh'] for line in lines_total]), currency_format)
        worksheet.write('L' + str(j), sum([line['porosn'] for line in lines_total]), currency_format)
        worksheet.write('M' + str(j), sum([line['pdoh'] for line in lines_total]), currency_format)
        worksheet.write('N' + str(j), sum([line['neto'] for line in lines_total]), currency_format)
        worksheet.write('O' + str(j), sum([line['obs'] for line in lines_total]), currency_format)
        worksheet.write('P' + str(j), sum([line['dodn'] for line in lines_total]), currency_format)
        worksheet.write('Q' + str(j), sum([line['ispl'] for line in lines_total]), currency_format)
        worksheet.write('R' + str(j), sum([line['dopna'] for line in lines_total]), currency_format)
        worksheet.write('S' + str(j), sum([line['brutto2'] for line in lines_total]), currency_format)
              
    def _get_company_iban(self, company_id):
        if company_id.partner_id.bank_ids:
            return company_id.partner_id.bank_ids[0].acc_number
        return ""

    def _get_date_period(self, period):
        ReportsCommon = self.env['hr.hr.payroll.reports.common']
        if not period:
            return ""
        date_format = ReportsCommon._date_format()
        date_from = datetime.strptime(period['date_from'], DF).strftime(date_format)
        date_to = datetime.strptime(period['date_to'], DF).strftime(date_format)
        return _('U RAZDOBLJU ') + date_from + ' - ' + date_to
