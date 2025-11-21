from stdnum.hr import oib
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from . import internship_calculator


class Employee(models.Model):
    _inherit = 'hr.employee'

    first_name = fields.Char(size=32)
    last_name = fields.Char(size=32)
    code = fields.Char(copy=False)
    code_associate = fields.Char(copy=False)
    is_employee_in_tags = fields.Boolean(compute='_calculate_is_employee_in_tags')
    is_associate_in_tags = fields.Boolean(compute='_calculate_is_associate_in_tags')
    enabled_manual_code_input = fields.Boolean(compute='_compute_manual_code_input')
    user_has_code_edit_privilege = fields.Boolean(compute='_compute_code_edit_privilege')
    oib = fields.Char(string='OIB', size=11, index=True, copy=False)
    jmbg = fields.Char(string='JMBG', copy=False)
    id_card_issue_date = fields.Date(string='ID card issue date')
    passport_issue_date = fields.Date(string='Passport issue date')
    note_ids = fields.One2many('hr.employee.note', 'employee_id', 'Employee Notes')

    hzmo_id = fields.Char(string='HZMO identification number')
    hzzo_id = fields.Char(string='HZZO identification number')
    has_supplementary_health_insurance = fields.Boolean(string='Has supplementary health insurance')

    hire_date = fields.Date('Hire date', help="Date when employee was hired", tracking=True)
    is_foreign_citizen = fields.Boolean('Foreign Citizen', default=False)

    department_id = fields.Many2one(tracking=True)
    job_id = fields.Many2one(tracking=True)
    parent_id = fields.Many2one(tracking=True)
    coach_id = fields.Many2one(tracking=True)
    addr_type = fields.Many2one("hr.address.type", "Address Type", tracking=True)
    street = fields.Char(tracking=True)
    street2 = fields.Char(tracking=True)
    city = fields.Many2one("res.city", tracking=True)
    zip = fields.Char('Zip code', tracking=True)
    country_id = fields.Many2one('res.country', tracking=True)
    nationality_id = fields.Many2one('res.country', string="Nationality") # employee nationality != employee country
    partner_id = fields.Many2one('res.partner', help="Partner related to this employee.")

    county_id = fields.Many2one('res.country.state')
    address_work_id = fields.Many2one('res.partner', 'Radna adresa', help="Adresa mjesta rada zaposlenika.")

    private_phone = fields.Char('Private phone/mobile')
    private_email = fields.Char('Private email')

    parent_name = fields.Char()
    father_name_surname = fields.Char('Name and surname of father')
    mother_name_surname = fields.Char('Name and surname of mother')
    previous_last_name = fields.Char()

    children_register_line_ids = fields.One2many(
        'hr.employee.children.register.line', 'employee_id', 'Children register', tracking=True)
    experience_ids = fields.One2many('hr.employee.experience', 'employee_id', string='Experiences')
    education_ids = fields.One2many('hr.employee.education', 'employee_id', string='Educations')
    cession_ids = fields.One2many('hr.employee.cession', 'employee_id', string='Cessions')
    cession_overseas_ids = fields.One2many('hr.employee.cession.overseas', 'employee_id', string="Cessions(Overseas)")
    work_permit_ids = fields.One2many('hr.employee.work.permit', 'employee_id', string='Work permits', tracking=True)
    inactivity_ids = fields.One2many('hr.employee.inactivity', 'employee_id', string='Inactivity', tracking=True)
    medic_exam_ids = fields.One2many('hr.employee.medic_exam', 'employee_id', string='Medical Exams', tracking=True)
    disability_ids = fields.One2many('hr.employee.disability', 'employee_id', string='Disabilities', tracking=True)
    category_type_ids = fields.Many2many('hr.category.type', string='Categories')

    # these three attributes are here since one2one is not available
    notes_note = fields.Text(string='Note')
    notes_att_data = fields.Binary(string='Note attachment file')
    notes_att_fname = fields.Char(string='Note attachment filename', size=128)

    # transportation from and to work
    transportation_work_ids = fields.One2many(
        'hr.transportation.work', 'employee_id', string="Transport from and to work")
    overall_transportation_for_payment = fields.Float(
        string='Overall price for payment', compute='_calculate_payment_price')

    # driving licence
    driving_licence_number = fields.Integer(string="Driving licence number")
    driving_licence_authority = fields.Char(string="Authority", size=256)
    driving_licence_first_issue_date = fields.Date(string="First issue date")
    driving_licence_issue_date = fields.Date(string="Issue date - Expiration date")
    driving_licence_expiration_date = fields.Date(string="Expiration date")
    driving_licence_note = fields.Text(string="Note in driving licence", default="")
    driving_licence_att_data = fields.Binary(string='Attachment file')
    driving_licence_att_fname = fields.Char(string='Attachment filename', size=128)
    driving_category_id = fields.Many2many('hr.driving_licence.category', string='Driving licence categories')

    # internship
    # Staž do zaposlenja - Korisnik sam unosi
    internship_until_emp_years = fields.Integer(string='Years until employee')
    internship_until_emp_months = fields.Integer(string='Months until employee')
    internship_until_emp_days = fields.Integer(string='Days until employee')
    # Neprekinuti staž do zaposlenja u državnom i javnom sektoru - Korisnik sam unosi
    internship_field_years = fields.Integer(string='Years in field')
    internship_field_months = fields.Integer(string='Months in field')
    internship_field_days = fields.Integer(string='Days in field')
    # Staž kod poslodavca - datum potpisivanja ugovora
    internship_company_years = fields.Integer(string='Years with employer', readonly=True, compute='_calculate_internship')
    internship_company_months = fields.Integer(string='Months with employer', readonly=True, compute='_calculate_internship')
    internship_company_days = fields.Integer(string='Days with employer', readonly=True, compute='_calculate_internship')
    # Ukupan staž - zbraja se "Staž do zaposlenja" i "Staž kod poslodavca"
    internship_total_years = fields.Integer(string='Years total', readonly=True, compute='_calculate_internship')
    internship_total_months = fields.Integer(string='Months total', readonly=True, compute='_calculate_internship')
    internship_total_days = fields.Integer(string='Days total', readonly=True, compute='_calculate_internship')
    # Staž za jubilarnu nagradu - zbraja se "Neprekinuti staž do zaposlenja u državnom i javnom sektoru"
    # i "Staž kod poslodavca"
    internship_prize_years = fields.Integer(string='Prize years', readonly=True, compute='_calculate_internship')
    internship_prize_months = fields.Integer(string='Prize months', readonly=True, compute='_calculate_internship')
    internship_prize_days = fields.Integer(string='Prize days', readonly=True, compute='_calculate_internship')

    # fields for internship export names (Year, day, month)
    internship_field_years_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_field_months_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_field_days_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_prize_years_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_prize_months_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_prize_days_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_total_years_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_total_months_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_total_days_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_company_years_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_company_months_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_company_days_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_until_emp_years_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_until_emp_months_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    internship_until_emp_days_export = fields.Integer(readonly=True, compute='_calculate_internship', store=False)
    #contract_type_ids = fields.Many2many('hr.contract.type', readonly=True, store=False, compute='_get_contract_types')

    degree_id = fields.Many2one('hr.employee.degree', 'Degree')
    insurance_start= fields.Date(string='Insurance date start', help="Start date of insurance by HZMO.")
    insurance_change= fields.Date(string='Latest change date', help="Date of the latest change to the aplication by HZMO.")
    insurance_end= fields.Date(string='Insurance date end', help="End date to the pension insurance at HZMO.")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res.update({
            'enabled_manual_code_input': self.env.user.company_id.hr_config_manually_input_employee_code,
            'user_has_code_edit_privilege': self.env.user.has_group('l10n_hr_hr.group_edit_employee_code')
        })
        return res

    def _create_work_contacts(self):
        super()._create_work_contacts()
        partner_id = self.env['res.partner'].browse(self.work_contact_id.id)
        for employee in self:
            partner_id.write(
                {
                    'oib':employee.oib,
                    'street':employee.street,
                    'city_id':employee.city,
                    'zip':employee.zip
                }
            )
            employee.write(
                {
                    'partner_id':partner_id
                }
            )

    def _get_employee_category_id(self):
        return self.env.ref("l10n_hr_hr.hr_employee_category_zaposlenik").id

    def _get_associate_category_id(self):
        return self.env.ref("l10n_hr_hr.hr_employee_category_suradnik").id

    def _get_student_category_id(self):
        return self.env.ref("l10n_hr_hr.hr_employee_category_student").id

    def _compute_manual_code_input(self):
        for rec in self:
            rec.enabled_manual_code_input = self.env.user.company_id.hr_config_manually_input_employee_code

    def _compute_code_edit_privilege(self):
        for rec in self:
            rec.user_has_code_edit_privilege = self.env.user.has_group('l10n_hr_hr.group_edit_employee_code')

    @api.depends('category_ids')
    def _calculate_is_employee_in_tags(self):
        for rec in self:
            rec.is_employee_in_tags = rec._get_employee_category_id() in rec.category_ids.ids

    @api.depends('category_ids')
    def _calculate_is_associate_in_tags(self):
        for rec in self:
            rec.is_associate_in_tags = rec._get_associate_category_id() in rec.category_ids.ids or rec._get_student_category_id() in rec.category_ids.ids

    @api.constrains("code", "code_associate")
    def _check_unique_employee_code(self):
        code = self.code if self.code else ''
        code_associate = self.code_associate if self.code_associate else ''
        emp_with_code = self.search(['&', ('id', '!=' , self.id), '|', ('code', '=', code), ('code_associate', '=', code_associate)])
        if emp_with_code:
            msg = _("Employees with selected code / associate's code already exist: {}").format('\n'.join(emp_with_code.mapped('name')))
            raise ValidationError(msg)

    @api.model
    def _get_display_name_format(self, setting):
        if setting == 'last_name_first':
            return "{1} {0}"
        return "{0} {1}"

    def _get_code(self):
        code = self.code if self.code else self.code_associate
        return code

    def _get_display_name(self, name_format):
        return name_format.format(self.first_name, self.last_name)

    @api.depends('code')
    def _compute_display_name(self):
        for record in self:
            company = self.env['res.company'].browse(record.company_id.id)
            display_name_config_param = company.hr_config_display_employee_code_in_name
            code = record._get_code()
            name = record.name
            if display_name_config_param and code:
                name = '[%s] %s' % (code, name)
            record.display_name = name

    @api.onchange('children_register_line_ids')
    def _update_number_of_children(self):
        self.children = len(self.children_register_line_ids)

    @api.constrains("children_register_line_ids", "children")
    def _check_children_register_line_ids(self):
        """ Check the number of children for consistency when records in Children register exist."""
        emps = self.filtered(lambda x: x.children > 0 and len(x.children_register_line_ids) != x.children)
        if emps:
            raise ValidationError(_("Number of children and children register records are not consistent!\n\nEmployees:\n{}")
                                    .format('\n'.join(emps.mapped('name'))))

    @api.onchange('first_name', 'last_name')
    def get_fullname(self):
        if self.first_name and self.last_name:
            name_format = self._get_display_name_format(self.company_id.hr_config_employee_display_name)
            self.name = self._get_display_name(name_format)

    def get_current_values(self,values):
        current_values = self.category_ids.ids
        tags = values['category_ids']
        for tag in tags:
            if tag[0] == 4 : # if link, append id value to current values
                current_values.append(tag[1])
            if tag[0] == 3 : # if unlink, remove id value from current values
                current_values.remove(tag[1])
        return current_values

    def should_generate_employee_code(self,values,method_called_on_write):
        result = self._get_employee_category_id() in self.get_current_values(values)
        if method_called_on_write:
            if not self.code:
                return result
            return False
        return result

    def should_generate_associate_code(self,values,method_called_on_write):
        result = (
            self._get_associate_category_id() in self.get_current_values(values) or
            self._get_student_category_id() in self.get_current_values(values)
        )
        if method_called_on_write:
            if not self.code_associate:
                return result
            return False
        return result

    def generate_code(self,sequence_code, target_field,values):
        next_code = self.env['ir.sequence'].with_context(force_company=values.get('company_id', False)).next_by_code(sequence_code)
        if not next_code:
            raise ValidationError(_("Must create '{}' sequence for generating {} code.").format(sequence_code, target_field))
        values[target_field] = next_code

    def generate_codes(self, values, method_called_on_write=False):
        rule_map = [
                (self.should_generate_employee_code, 'hr.employee', 'code'),
                (self.should_generate_associate_code, 'hr.employee.external.associate', 'code_associate'),
        ]
        for condition_method, model, field in rule_map:
            if condition_method(values, method_called_on_write):
                self.generate_code(model, field, values)

    def _check_required_tags(self, values):
        required_tags = [self._get_employee_category_id(), self._get_student_category_id(), self._get_associate_category_id()]
        if not any(tag in self.get_current_values(values)  for tag in required_tags):
            raise ValidationError(_("You have to choose at least employee or associate tag"))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('category_ids', False):
                self._check_required_tags(values)
                if not self.env.user.company_id.hr_config_manually_input_employee_code:
                    self.generate_codes(values)

            if values.get('parent_id'):
                # parent_id is integer the id of the employee's supervisor/manager
                parent_id = values.pop('parent_id')
                emp_id = super().create(values)
                emp_id.write({'parent_id': parent_id })
                return emp_id
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('category_ids', False):
            self._check_required_tags(vals)
            if not self.env.user.company_id.hr_config_manually_input_employee_code:
                self.generate_codes(vals, method_called_on_write=True)
        return super().write(vals)

    @api.depends('contract_ids')
    def _get_contract_types(self):
        self.ensure_one()
        packs = set()
        for contract in self.contract_ids:
            if contract.type_id:
                packs.add(contract.type_id.id)
        self.contract_type_ids = list(packs)

    @api.constrains('internship_until_emp_years', 'internship_until_emp_months', 'internship_until_emp_days',
                    'internship_field_years', 'internship_field_months', 'internship_field_days')
    def check_internship(self):
        if self.internship_total_years > 99 or self.internship_field_years > 99:
            raise ValidationError(_("Internship - year can not be larger than 99."))

        if self.internship_until_emp_months > 12 or self.internship_field_months > 12:
            raise ValidationError(_("Internship - month can not be larger than 12."))

        if self.internship_until_emp_days > 30 or self.internship_field_days > 30:
            raise ValidationError(_("Internship - days can not be larger than 30."))

        return True

    # Internship calculation from contract

    def _calculate_internship(self):
        for employee in self:
            records = self.env['hr.contract'].search([['employee_id', '=', employee.id],
                                                    ['state', 'not in', ['draft','cancel']]])

            employee.internship_company_days, employee.internship_company_months, employee.internship_company_years \
                = internship_calculator.calculate_internship(records)

            # calculate total internship
            employee.internship_total_days = employee.internship_until_emp_days + employee.internship_company_days
            employee.internship_total_months = employee.internship_until_emp_months + employee.internship_company_months
            employee.internship_total_years = employee.internship_until_emp_years + employee.internship_company_years
            employee.internship_total_days, employee.internship_total_months, employee.internship_total_years = \
                internship_calculator.divide_internship_results(employee.internship_total_days, employee.internship_total_months,
                                                                employee.internship_total_years)

            # calculate internship for prize
            employee.internship_prize_days = employee.internship_field_days + employee.internship_company_days
            employee.internship_prize_months = employee.internship_field_months + employee.internship_company_months
            employee.internship_prize_years = employee.internship_field_years + employee.internship_company_years
            employee.internship_prize_days, employee.internship_prize_months, employee.internship_prize_years = \
                internship_calculator.divide_internship_results(employee.internship_prize_days, employee.internship_prize_months,
                                                                employee.internship_prize_years)

            # fill fields for export with values
            employee.internship_field_years_export = employee.internship_field_years
            employee.internship_field_months_export = employee.internship_field_months
            employee.internship_field_days_export = employee.internship_field_days
            employee.internship_prize_years_export = employee.internship_prize_years
            employee.internship_prize_months_export = employee.internship_prize_months
            employee.internship_prize_days_export = employee.internship_prize_days
            employee.internship_total_years_export = employee.internship_total_years
            employee.internship_total_months_export = employee.internship_total_months
            employee.internship_total_days_export = employee.internship_total_days
            employee.internship_company_years_export = employee.internship_company_years
            employee.internship_company_months_export = employee.internship_company_months
            employee.internship_company_days_export = employee.internship_company_days
            employee.internship_until_emp_years_export = employee.internship_until_emp_years
            employee.internship_until_emp_months_export = employee.internship_until_emp_months
            employee.internship_until_emp_days_export = employee.internship_until_emp_days

    def _calculate_payment_price(self):
        for employee in self:
            employee.overall_transportation_for_payment = sum(employee.transportation_work_ids.mapped('overall'))

    _sql_constraints = [
        ('unique_oib', 'unique(oib, company_id)', 'You can not have employees with the same OIB and company.'),
        ('unique_ssnid', 'unique(ssnid, company_id)', 'You can not have employees with the same SSN and company.')
    ]

    @api.constrains("oib")
    def check_employee_oib_unique(self):
        """Check for OIB uniqueness for hr.employee
        - OIBs must be unique and of length == 11
        - OIB is mandatory"""
        for record in self:
            if record.oib and record.active:
                if len(record.oib) != 11:
                    raise ValidationError(_("OIB field must be exactly 11 characters long"))
                if not record.oib.isnumeric():
                    raise ValidationError(_("OIB field must be a number"))
                if not oib.is_valid(record.oib):
                    raise ValidationError(_("Employee OIB is not valid"))

    @api.onchange('city')
    def onchange_city(self):
        if self.city:
            self.zip = self.city.zipcode
            self.country_id = self.city.country_id

    def _has_disability_on_date(self, date):
        """
        Employee has disability on date if:
            - there exists a disability where no date is selected
            - there exists a disability where start date is selected and it is <= date
            - there exists a disability where end date is selected and it is >= date
            - there exists a disability where both start and end dates are selected and start_date <= date and end_date >= date
        """
        disability_obj = self.env['hr.employee.disability']
        emp_id = self.id
        if not self.disability_ids:
            return False
        clause_1 = ['&', ('date_from', '<=', date), '|', ('date_to', '=', False), ('date_to', '>=', date)]
        clause_2 = ['&', ('date_to', '>=', date), '|', ('date_from', '=', False), ('date_from', '<=', date)]
        clause_3 = ['&', ('date_from', '=', False), ('date_to', '=', False)]
        domain = ['&', ('employee_id', '=', emp_id), '|', '|'] + clause_1 + clause_2 + clause_3
        if disability_obj.search(domain):
            return True
        return False

    def _get_employees_by_tag(self, include_inactive=False):
        """
        Return employees which are actual employees, i.e. not students or associates.
        NOTICE: employee can be both employee and associate.
        """
        domain = [('category_ids.id', '=', self.env.ref('l10n_hr_hr.hr_employee_category_zaposlenik').id)]
        if include_inactive:
            domain.append(('active', 'in', [True, False]))
        return  self.search(domain)

class EmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    @api.depends('job_id')
    def _compute_job_title(self):
        for employee in self:
            employee.job_title = employee.job_id.name

