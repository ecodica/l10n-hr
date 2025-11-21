from odoo import api, models, _
from datetime import datetime

class ReportContracts(models.AbstractModel):
    _name = 'report.hr_hr.hr_contracts_report'
    _description = 'HR contracts report'

    @api.model
    def _get_report_values(self, docids, data=None):

        self.model = self.env.context.get('active_model')

        contract_entries = self.env['hr.contract'].search([])
        employee = self.env['hr.employee'].search([])

        contract_entries_list = []
        employee_list = []

        if contract_entries:
            for i in contract_entries:
                for elem in docids:
                    if i.id == elem:
                        vals = {
                            'id': i.employee_id.id,
                            'name': i.name,
                            'employee_id': i.employee_id.name,
                            'type_id': i.type_id.name,
                            'company_id': i.company_id.name,
                            'department_id': i.department_id.name,
                            'job_id': i.job_id.name,
                            'job_description': i.job_description,
                            'contract_no': i.contract_no,
                            'document_type': i.document_type.name,
                            'area': i.area.name,
                            'area_type': i.area_type.name,
                            'old_state': i.old_state,
                            'date_start': datetime.strptime(str(i.date_start), '%Y-%m-%d').strftime('%d.%m.%Y') if i.date_start else "",
                            'date_end': datetime.strptime(str(i.date_end), '%Y-%m-%d').strftime('%d.%m.%Y') if i.date_end else "",
                            'termination_reason': i.termination_reason.name,
                            'resource_calendar_id': i.resource_calendar_id.name,
                            'trial_date_start': datetime.strptime(str(i.trial_date_start), '%Y-%m-%d').strftime('%d.%m.%Y') if i.trial_date_start else "",
                            'trial_date_end': datetime.strptime(str(i.trial_date_end), '%Y-%m-%d').strftime('%d.%m.%Y') if i.trial_date_end else "",
                            'internship_date_start': datetime.strptime(str(i.internship_date_start), '%Y-%m-%d').strftime('%d.%m.%Y') if i.internship_date_start else "",
                            'internship_date_end': datetime.strptime(str(i.internship_date_end), '%Y-%m-%d').strftime('%d.%m.%Y') if i.internship_date_end else "",
                            'notes': i.notes,
                        }
                        contract_entries_list.append(vals)

        if employee:
            for i in employee:
                vals1 = {
                    'id': i.id,
                    'oib': i.oib,
                    'work_location': i.work_location,
                }
                employee_list.append(vals1)

        return {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'contract': contract_entries_list,
            'employee': employee_list,
            'data': data,
        }
