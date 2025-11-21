from odoo import fields, models


class HrEmployeeRegistration(models.TransientModel):
    _name = "hr.employee.registration.wizard"
    _description = "Employee registration report wizard"

    date_from = fields.Date(required = True)
    date_to = fields.Date(required = True)

    include_application = fields.Boolean(string = "Include applications", default = False)
    include_termination = fields.Boolean(string = "Include terminations", default = False)
    include_expiration = fields.Boolean(string = "Include expirations", default = False)

    def print_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('l10n_hr_hr.employee_contracts_within_date').report_action(self, data=data)
