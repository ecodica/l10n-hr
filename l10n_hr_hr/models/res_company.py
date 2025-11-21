from odoo import fields, models, _


class Company(models.Model):
    _inherit = 'res.company'

    is_contract_sequence = fields.Boolean(string="Sequence generated Contract number",
                                          help="If this option is enabled, an automatic counter is used to "
                                               "assign the contract number.")
    hr_config_employee_display_name = fields.Selection([
        ('first_name_first', 'First_name Last_Name'),
        ('last_name_first', 'Last_name First_name')], 'Employee display name', default='first_name_first')

    hr_config_hr_contract_wage_visible = fields.Boolean('Wage visible in HR Contract Form')
    hr_config_display_employee_code_in_name = fields.Boolean("Display employee code in name")
    hr_config_manually_input_employee_code = fields.Boolean("Manually input employee code")

    def write(self, vals):
        self.update_employee_display_name(vals)
        return super().write(vals)

    def update_employee_display_name(self, vals):
        """
        Update ALL employees and related partners and users for given companies.
        """
        if 'hr_config_employee_display_name' not in vals:
            return True
        emp_obj = self.env['hr.employee']
        emp_domain = [
            ('active', 'in', [True, False]),
            ('company_id', 'in', self.ids)
        ]
        emps = emp_obj.search(emp_domain)
        name_format = emp_obj._get_display_name_format(vals.get('hr_config_employee_display_name'))
        for employee in emps:
            new_name = employee._get_display_name(name_format)
            employee.name = new_name
            if employee.partner_id:
                employee.partner_id.name = new_name
            if employee.user_id:
                employee.user_id.partner_id.name = new_name
        return True
