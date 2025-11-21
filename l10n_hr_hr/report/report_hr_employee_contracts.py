from odoo import api, models


class HrEmployeeRegistrationReport(models.AbstractModel):
    _name = 'report.hr_hr.report_hr_employee_contracts'
    _description = 'Employee contracts within date limit report'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        doc_ids = self.env.context['active_ids']
        doc_model = self.env.context['active_model']
        docs = self.env[doc_model].browse(doc_ids)
        emp_obj = self.env['hr.employee']
        contract_obj = self.env['hr.contract']

        employees_application = False
        contracts_termination = False
        contracts_expiration = False

        include_application = docs.include_application
        include_termination = docs.include_termination
        include_expiration = docs.include_expiration

        if not include_application and not include_termination and not include_expiration:
            include_application = True
            include_termination = True
            include_expiration = True

        all_contracts = contract_obj.with_context(active_test=False).search([])
        all_employees = emp_obj.with_context(active_test=False).search([])

        if include_application:
            employees_application = all_employees.filtered(lambda c: c.hire_date and c.hire_date >= docs.date_from and c.hire_date <= docs.date_to)

        if include_termination:
            contracts_termination = all_contracts.filtered(lambda c: c.termination_date and c.termination_date >= docs.date_from and c.termination_date <= docs.date_to)

        if include_expiration:
            contracts_expiration = self.get_expiration_contract_ids(docs.date_from, docs.date_to, all_employees)

        lang = self.env.context.get('lang')
        report_data = {
            'company': self.env.user.company_id,
            'employees_application': employees_application,
            'employees_termination': contracts_termination,
            'employees_expiration': contracts_expiration,
            'include_application': include_application,
            'include_termination': include_termination,
            'include_expiration': include_expiration,
        }
        return {
            'doc_ids': doc_ids,
            'doc_model': doc_model,
            'docs': docs,
            'data': report_data,
            'lang':lang,
        }

    def get_expiration_contract_ids(self, date_from, date_to, all_employees):
        contracts = []
        for employee in all_employees:
            consecutive_contracts = employee.get_consecutive_contracts(date_to)
            if not consecutive_contracts:
                continue
            last_contract = consecutive_contracts[-1]
            if last_contract.date_end and last_contract.date_end <= date_to and last_contract.date_end >= date_from:
                # if last contract end EXACTLY on date_end, we do not know if it is THE last contract
                # because get_consecutive_contracts only returns contracts which start before or exactly on date_end
                # we need to manually check if there is a contract starting exactly on date_end+1 in that case
                if last_contract.date_end == date_to and last_contract.get_immediate_follower():
                    continue
                contracts.append(last_contract)

        return contracts
