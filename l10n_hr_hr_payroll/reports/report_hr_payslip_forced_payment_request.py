from odoo import api, models
from odoo.tools.misc import format_date

class PayslipForcePaymentRequestReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_payslip_forced_payment_request'
    _description = 'Payslip Forced Payment Request Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docids = data['active_ids']
        wizard_data = data['wizard_data']
        obj_name = 'hr.payslip'
        lang = self.env.context.get('lang')
        slip_obj = self.env[obj_name]
        slips = slip_obj.browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': obj_name,
            'docs': slips,
            'lang': lang,
            'report_slip_data': self._get_slip_data(slips),
            'company': self._get_company_data(self.env.user.company_id, wizard_data),
            'dates': self._get_dates(wizard_data),
        }
    def _get_slip_data(self, slips):
        data = {}
        for slip in slips:
            slip_data = {}
            slip_data['name'] = slip.employee_id.name
            slip_data['oib'] = slip.employee_id.oib
            slip_data['address'] = self._get_employee_address(slip)
            slip_data['bank_account'] = slip.bank_account_id.acc_number if slip.bank_account_id else ''
            slip_data['protected_bank_account'] = slip.protected_bank_account_id.acc_number if slip.protected_bank_account_id else ''
            data [slip.id] = slip_data
        return data

    def _get_employee_address(self, slip):
        street = slip.street.split(',')[0]
        return street + ', ' + slip.zip_code + ' ' + slip.city.name

    def _get_company_data(self, company, wizard_data):
        return {
            'name': company.name,
            'oib': company.company_registry,
            'city': company.city_id.name,
            'address': company.street + ', ' + company.city_id.zipcode + ' ' + company.city_id.name,
            'authorised_person': wizard_data['authorised_person'] if wizard_data['authorised_person'] else '',
            'authorised_person_oib': wizard_data['authorised_person_oib'] if wizard_data['authorised_person_oib'] else '',
            'print_place': wizard_data['print_place'],
        }

    def _get_dates(self, wizard_data):
        return {
            'pay_date': format_date(self.env, wizard_data['pay_date']),
            'print_date': format_date(self.env, wizard_data['print_date']),
        }

