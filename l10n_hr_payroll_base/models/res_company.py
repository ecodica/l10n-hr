# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CompanyProjectManager(models.Model):
    """
    List of project managers which is used for sending notifications about annual leave and contract termination.
    """
    _name = 'res.company.project.manager'
    _description = 'List of project managers for the company'

    company_id = fields.Many2one('res.company', 'Company', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', 'User')

class Company(models.Model):
    _inherit = "res.company"

    # account dashboard onboarding
    account_dashboard_onboarding_state = fields.Selection([
        ('not_done', "Not done"), 
        ('just_done', "Just done"), 
        ('done', "Done"), 
        ('closed', "Closed")], 
        string="State of the account dashboard onboarding panel", 
        default='closed'
    )

    city = fields.Char(string="City name")
    city_id = fields.Many2one(comodel_name="res.city", related="partner_id.city_id", readonly=False)
    hzmo_registry_number = fields.Char('Registarski broj (HZMO)', size=64, help="Registarski broj u registru obveznika doprinosa za mirovinsko osiguranje")
    hzzo_commitment_number = fields.Char('Broj obveze (HZZO)', size=64)

    # fields for secondary currency configuration  (from hr_account)
    secondary_currency_enable = fields.Boolean("Enable Secondary Currency", help="Show amounts in secondary currency next to amounts primary currency on reports.")
    secondary_currency_id = fields.Many2one('res.currency', "Secondary Currency", help="Currency used as additional currency on reports.")
    secondary_currency_rate = fields.Float("Currency Rate", digits='Currency Rate', help="Rate used for conversion from primary to secondary currency.")
    secondary_currency_multiply_rate = fields.Boolean("Multiply rate", help="Helper field to avoid using inverted currency rates and instead alternate between multiplication and division.")
    secondary_currency_all_partners = fields.Boolean("Show On All Partners", help="Show amounts in secondary currency next to amounts in primary currency on reports for all partners (if report uses partner), otherwise 'Show secondary Currency' on partner form must be checked to print secondary currency.")
    secondary_currency_apply_date = fields.Date("Apply from", help="Secondary currency is applied on reports after this date. If not entered, it is applied on all reports.")

    # report fields
    external_report_invoice_layout_id = fields.Many2one('ir.ui.view', 'Invoice Template')

    invoice_posting_date_default = fields.Selection([
        ('invoice_date','Based on Invoice Date'),
        ('invoice_delivery','Based on Invoice Date Delivery')], 
        default='invoice_date', 
        string='Invoice posting date', 
        help='Posting date will be automatically set based on the selected field in this setting.'
    )

    representative_first_name = fields.Char(string='Representative first name')
    representative_last_name = fields.Char(string='Representative last name')
    project_manager_ids = fields.One2many('res.company.project.manager', 'company_id', 'Project managers')

    @api.onchange("city_id")
    def change_city_zip(self):
        """Auto-fill zip code in forms on city_id field cnahge"""
        for record in self:
            record.zip = record.city_id.zipcode

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('partner_id'):
                self.clear_caches()
                return super(Company, self).create(vals)
            partner = self.env['res.partner'].create({
                'name': vals['name'],
                'is_company': True,
                'image_1920': vals.get('logo'),
                'customer': False,
                'email': vals.get('email'),
                'phone': vals.get('phone'),
                'website': vals.get('website'),
                'vat': vals.get('vat'),
                'company_registry': vals.get('company_registry'),
                'city_id': vals.get('city_id')
            })
            vals['partner_id'] = partner.id
            self.clear_caches()
        company = super(Company, self).create(vals_list)
        # The write is made on the user to set it automatically in the multi company group.
        for vals in vals_list:
            self.env.user.write({'company_ids': [(4, company.id)]})
            partner.write({'company_id': company.id})
            # Make sure that the selected currency is enabled
            if vals.get('currency_id'):
                currency = self.env['res.currency'].browse(vals['currency_id'])
                if not currency.active:
                    currency.write({'active': True})
        return company

    def get_project_manager_partner_ids(self):
        """
        Return partner ids from users which are listed as project managers. Used for sending mail notifications.
        """
        return self.project_manager_ids.mapped('user_id').mapped('partner_id').ids

    def send_annual_leave_and_contract_termination_notification(self):
        days = 14
        date_from = datetime.now().date()
        return self.send_availability_reminder(date_from, days)
    
    def get_availability_reminder_mail_template(self):
        return self.env.ref('hr_hr_payroll_extra.mail_template_data_availability_reminder')

    def send_availability_reminder(self, date_from, days):
        """
        Send contract termination and annual leave reminder:
            1. to project managers for all employees
            2. to parent_id for each employee (group all employees by parent_id)
        """
        company = self.env.user.company_id
        date_to = date_from + relativedelta(days=days)
        manager_ids = tuple(company.get_project_manager_partner_ids())
        annual_leave = company.get_annual_leave_employees(date_from, date_to, manager_ids)
        contract_termination = company.get_contract_termination_employees(date_from, date_to, manager_ids)
        if len(annual_leave) > 0 or len(contract_termination) > 0:
            company.send_emails(annual_leave, contract_termination, days)
        return True
    
    def send_emails(self, annual_leave, contract_termination, days):
        template = self.get_availability_reminder_mail_template()

        recievers = annual_leave.keys() | contract_termination.keys()
        for reciever in recievers:
            c = {
                'recipients': ','.join([str(x) for x in reciever]) if type(reciever) in (list, tuple) else str(reciever),
                'annual_leave': [] if reciever not in annual_leave else annual_leave[reciever],
                'contract_termination': [] if reciever not in contract_termination else contract_termination[reciever],
                'days': days,
            }
            template.with_context(c).send_mail(self.id, force_send=True, raise_exception=True)
        return True

    def get_annual_leave_employees(self, date_from, date_to, manager_ids):
        """
        We need to group data by reciever:
        1. project managers receive info about all employeees
        2. other employees only get info about theis subordinates
        We use grouping by parent employee user's partner ID because that is the ID we send emails to.
        If employee has no parent or its parent has no related user, no email is sent.
        """
        query = """
            SELECT emp.name AS emp_name,
            leave.request_date_from AS date_from,
            leave.request_date_to AS date_to,
            emp.parent_id AS parent_id,
            users.id AS parent_uid,
            users.partner_id AS parent_uid_partner_id
            FROM hr_employee AS emp
            LEFT JOIN hr_leave AS leave ON leave.employee_id = emp.id
            LEFT JOIN hr_employee AS emp_parent ON emp_parent.id = emp.parent_id
            LEFT JOIN res_users AS users ON users.id = emp_parent.user_id
            WHERE leave.request_date_from >= '{0}' AND leave.request_date_from <= '{1}'
        """.format(date_from, date_to)
        self.env.cr.execute(query)
        leaves = self.env.cr.dictfetchall()
        leaves_grouped = {manager_ids: leaves}
        for leave in leaves:
            key = leave['parent_uid_partner_id']
            if not key:
                continue
            if key not in leaves_grouped:
                leaves_grouped.update({key: []})
            leaves_grouped[key].append(leave)
        return leaves_grouped

    def get_contract_termination_employees(self, date_from, date_to, manager_ids):
        query = """
            SELECT emp.name AS emp_name,
            con.termination_date AS date,
            emp.parent_id AS parent_id,
            users.id AS parent_uid,
            users.partner_id AS parent_uid_partner_id
            FROM hr_employee AS emp
            LEFT JOIN hr_contract AS con ON con.employee_id = emp.id
            LEFT JOIN hr_employee AS emp_parent ON emp_parent.id = emp.parent_id
            LEFT JOIN res_users AS users ON users.id = emp_parent.user_id
            WHERE con.termination_date >= '{0}' AND con.termination_date <= '{1}'
        """.format(date_from, date_to)
        self.env.cr.execute(query)
        terminations = self.env.cr.dictfetchall()
        terminations_grouped = {manager_ids: terminations}
        for termination in terminations:
            key = termination['parent_uid_partner_id']
            if not key:
                continue
            if key not in terminations_grouped:
                terminations_grouped.update({key: []})
            terminations_grouped[key].append(termination)
        return terminations_grouped
