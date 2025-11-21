from odoo import api, fields, models, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from ..models import payroll_common as paycom
from odoo.exceptions import ValidationError


class AdditionalIncomeReportWizardEmployeeLine(models.TransientModel):
    _name = 'additional.income.report.wizard.employee.line'
    _description = "Stavka zaposlenika za formu za ispis potvrde o drugom dohotku"

    wizard_id = fields.Many2one('additional.income.report.wizard', 'Wizard parent')
    # employee_id is used to show as readonly on form, emp_id is the "actual" field
    # if we only use readonly field, then it can not be read from wizard for some reason so this is a workaround
    employee_id = fields.Many2one(related='emp_id', string='Zaposlenik')
    emp_id = fields.Many2one('hr.employee', 'Emp')
    print_report = fields.Boolean('Ispiši potvrdu', default=False)


class AdditionalIncomeReportWizard(models.TransientModel):
    _name = 'additional.income.report.wizard'
    _description = "Forma za ispis potvrde o drugom dohotku"

    def _get_default_year(self):
        """
        Get current year.
        """
        today_date = fields.Date.today()
        domain = [('date_from', '<=', today_date), ('date_to', '>=', today_date)]
        return self.env['account.fiscal.year'].search(domain, limit=1)

    year_id = fields.Many2one('account.fiscal.year', 'Godina', required=True, default=_get_default_year)
    print_date = fields.Date('Datum ispisa', required=True, default=fields.Date.context_today)
    employee_line_ids = fields.One2many('additional.income.report.wizard.employee.line', 'wizard_id', 'Zaposlenici')

    @api.onchange('year_id')
    def onchange_year_id(self):
        """
        Get all employees with payslips for additional income in selected year.
    """
        company = self.env.user.company_id
        date_from = self.year_id.date_from
        date_to = self.year_id.date_to
        emp_ids =[]
        self.employee_line_ids = [(5, 0, 0)] 
        struct_codes = paycom.get_structures()['additional_income']
        query = """
            SELECT DISTINCT(employee_id) AS id
            FROM hr_payslip AS slip
            LEFT JOIN hr_payroll_structure AS struct ON struct.id = slip.struct_id
            WHERE slip.paid_date >= '{0}'
            AND slip.paid_date <= '{1}'
            AND struct.code IN {2}
            AND slip.company_id = {3}
        """.format(date_from, date_to, struct_codes, company.id)
        self.env.cr.execute(query)
        emp_ids = self.env.cr.dictfetchall()
        employee_lines = [(0, 0, {'emp_id': emp['id'], 'print_report': False}) for emp in emp_ids]
        self.employee_line_ids = employee_lines

    def print_report(self):
        data = {}
        data['year_id'] = self.year_id.id
        data['print_date'] = self.print_date
        data['employee_ids'] = [line.emp_id.id for line in self.employee_line_ids if line.print_report]
        if not data['employee_ids']:
            raise ValidationError(u'Potrebno je odabrati barem jednog zaposlenika kako bi se izvještaj mogao ispisati!')
        return self.env.ref('l10n_hr_hr_payroll.additional_income_report').report_action(self, data=data)
        