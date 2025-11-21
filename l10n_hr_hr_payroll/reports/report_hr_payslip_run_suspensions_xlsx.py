from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import json

class HrPayslipRunSuspensionsReportXSLX(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_run_suspensions_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Payslip Run Suspensions XLSX Report"

    def generate_xlsx_report(self, workbook, data, report_book):
        self = self.with_context(lang=self.env.user.lang)
        doc_ids = data.get('run_ids', report_book.ids)
        this_model = self.env.context.get('active_model')
        docs = self.env[this_model].browse(doc_ids)
        dep_ids = data.get('department_ids')
        if not dep_ids:
            active_payslip_run = self.env['hr.payslip.run'].search([('id', 'in', report_book.ids)])
            dep_ids = active_payslip_run.mapped('slip_ids').mapped('employee_id').mapped('department_id').ids

        pdf_report_obj = self.env['report.l10n_hr_hr_payroll.report_hr_payslip_run_suspensions']
        # dep_ids = data['department_ids']
        city = self._get_display_city_name(docs[0])
        dep_cond = pdf_report_obj.get_conds(dep_ids)
        run_cond = pdf_report_obj.get_conds(doc_ids)

        susp_lines = dict()
        susp_lines = pdf_report_obj.get_suspension_lines(run_cond, dep_cond)

        currency_precision = self.env.user.company_id.currency_id.decimal_places
        p_precision = '0'*currency_precision
        document_header_center_format = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'vtop', 'font_size': 12, 'border_color': '#FFFFFF'})
        document_header_right_format = workbook.add_format({'align': 'right', 'valign': 'vtop', 'font_size': 12, 'border_color': '#FFFFFF'})
        document_header_left_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vtop', 'font_size': 12, 'border_color': '#FFFFFF'})
        document_content_left_format = workbook.add_format({'bold': 0, 'align': 'left', 'valign': 'vtop', 'font_size': 10, 'border_color': '#FFFFFF'})
        header_format = workbook.add_format({'bold': 1, 'align': 'left', 'valign': 'vtop', 'font_size': 12, 'border': 1, 'bg_color': '#D3D3D3'})
        content_format = workbook.add_format({'align': 'left', 'valign': 'vtop', 'font_size': 9, 'border': 1})
        total_amount_format = workbook.add_format({'align': 'left', 'bold': 1, 'valign': 'vtop', 'border': 1})
        currency_format = workbook.add_format({'font_size': 9, 'align': 'right', 'valign': 'vtop', 'border': 1, 'num_format':  f'#,##0.{p_precision}'})

        worksheet = workbook.add_worksheet(_('Suspensions'))
        worksheet.merge_range('B1:D1', docs[0].company_id.name, document_header_left_format)
        worksheet.merge_range('B2:D2', docs[0].company_id.street, document_header_left_format)
        worksheet.merge_range('B3:D3', city, document_header_left_format)
        worksheet.merge_range('B4:D4', docs[0].company_id.country_id.name, document_header_left_format)
        worksheet.merge_range('B5:D5', _('OIB: ') + docs[0].company_id.company_registry, document_header_left_format)
        worksheet.merge_range('F1:I1', _('Suspensions'), document_header_center_format)
        worksheet.merge_range('B7:C7', _('Payslip runs:'), document_header_left_format)

        i = 8
        for slip in docs:
            worksheet.merge_range('B' + str(i) + ':F' + str(i), slip.name, document_content_left_format)
            worksheet.merge_range('H' + str(i) + ':J' + str(i), self._get_date_period(slip)[0], document_content_left_format)
            worksheet.merge_range('K' + str(i) + ':M' + str(i), self._get_date_period(slip)[1], document_content_left_format)
            i+=1

        i+=1
        worksheet.write('B'+ str(i), _('Row no.'), header_format)
        worksheet.merge_range('C'+ str(i) + ':D' + str(i), _('Employee'), header_format)
        worksheet.merge_range('E'+ str(i) + ':H' + str(i), _('Suspension name'), header_format)
        worksheet.merge_range('I'+ str(i) + ':K' + str(i), _('IBAN'), header_format)
        worksheet.merge_range('L'+ str(i) + ':M' + str(i), _('Amount'), header_format)
        i+=1
        total_amount = 0.0
        line_counter = 1
        for line in susp_lines:
            worksheet.write('B' + str(i), str(line_counter) + '.', content_format)
            worksheet.merge_range('C' + str(i) + ':D' + str(i), line[0], content_format)
            worksheet.merge_range('E' + str(i) + ':H' + str(i), line[1], content_format)
            worksheet.merge_range('I' + str(i) + ':K' + str(i), line[2], content_format)
            worksheet.merge_range('L' + str(i) + ':M' + str(i), line[3], currency_format)
            total_amount += line[3]
            i+=1
            line_counter += 1
        worksheet.merge_range('B' + str(i) + ':K' + str(i), _('Total amount:'), total_amount_format)
        worksheet.merge_range('L' + str(i) + ':M' + str(i), total_amount, currency_format)
        
    def _get_display_city_name(self, run_id):
        zipcode = run_id[0].company_id.city_id.zipcode or ''
        name = run_id[0].company_id.city_id.name or ''
        res = zipcode + ' ' + name
        return res

    def _get_date_period(self, payslip):
        if payslip:
            from_date = _("From date: ") + str(self._set_date_format(payslip.date_start))
            to_date = _("To date: ") + str(self._set_date_format(payslip.date_end))
            return (from_date, to_date)
        return ""   
    
    def _set_date_format(self, date):
        datetime_object = datetime.strptime(str(date), '%Y-%m-%d')
        return datetime_object.strftime('%d.%m.%Y')
