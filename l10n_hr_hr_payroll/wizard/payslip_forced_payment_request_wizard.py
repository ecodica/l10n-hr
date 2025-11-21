from odoo import models, fields, api
import datetime

class PayslipForcedPaymentRequestWizard(models.TransientModel):
    _name = 'payslip.forced.payment.request.wizard'
    _description = 'Zahtjev za prisilnu naplatu'

    pay_date = fields.Date('Datum dospijeća')
    print_date = fields.Date('Datum ispisa')
    print_place = fields.Char('Mjesto izdavanja')
    authorised_person = fields.Char('Punomoćnik')
    authorised_person_oib = fields.Char('OIB punomoćnika', size=11)

    @api.model
    def default_get(self, fields):
        res = super(PayslipForcedPaymentRequestWizard, self).default_get(fields)
        context = self._context
        if context.get('whole_payslip_run', False):
            pay_date = self.env['hr.payslip.run'].browse(context['active_id']).pay_date
        else:
            pay_date = self.env['hr.payslip'].browse(context['active_id']).payslip_run_id.pay_date
        user = self.env['res.users'].browse(self.env.uid)
        company = self.env.user.company_id

        res.update({
            'pay_date': pay_date,
            'print_date': datetime.date.today(),
            'print_place': company.city_id.name,
            'authorised_person': '',
            'authorised_person_oib': '',
        })
        return res

    def print_forced_payslip_payment_request(self):
        self.ensure_one()
        context = self._context
        wizard_data = {
            'pay_date': self.pay_date,
            'print_date': self.print_date,
            'print_place': self.print_place,
            'authorised_person': self.authorised_person,
            'authorised_person_oib': self.authorised_person_oib,
        }

        if context.get('whole_payslip_run', False):
            slip_obj = self.env["hr.payslip"]
            slip_ids = slip_obj.search([('payslip_run_id', 'in', context['active_ids'])]).ids
        else:
            slip_ids = context['active_ids']
        data = {}
        data['wizard_data'] = wizard_data
        data['active_ids'] = slip_ids

        return self.env.ref('l10n_hr_hr_payroll.hr_payslip_forced_payment_request_report').report_action(self, data)