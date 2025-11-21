from odoo import api, fields, models, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

class Info3PayslipConfirmationForm(models.TransientModel):
    _name = 'info3.payslip.confirmation.form'
    _description = "Čarobnjak za ispis potvrde o plaći"

    
    date =  fields.Date('Datum', help="Datum za koji je potvrda o plaći napravljena, mjesec dana nakon što se dogodila.", required=True, default=fields.Date.context_today)
    employee =  fields.Many2one('hr.employee', 'Zaposlenik', required=True)


    def print_report(self):
        data = {}
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['employee_id'] = self.employee.id
        data['date'] = self.date

        return self.env.ref('l10n_hr_hr_payroll.payslip_confirmation_report').report_action(self, data=data)
        