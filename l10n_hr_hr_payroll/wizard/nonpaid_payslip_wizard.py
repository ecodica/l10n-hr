from odoo import models, fields, api
import datetime


class NonPaidPayslipWizard(models.TransientModel):
    _name = 'nonpaid.payslip.wizard'
    _description = 'Ispis neisplaćene plaće'

    pay_date = fields.Date('Datum dospijeća', required=True)
    print_date = fields.Date('Datum ispisa')
    handover_date = fields.Date('Datum predaje')
    authorised_person = fields.Char('Punomoćnik', required=True)


    @api.model
    def default_get(self, fields):
        res = super(NonPaidPayslipWizard, self).default_get(fields)
        context = self._context
        if context.get('whole_payslip_run', False):
            payslip_run = self.env['hr.payslip.run'].browse(context['active_id'])
            pay_date = payslip_run.pay_date
        else:
            payslip = self.env['hr.payslip'].browse(context['active_id'])
            pay_date = payslip.payslip_run_id.pay_date
        res.update({
            'pay_date': pay_date,
            'print_date': datetime.date.today(),
            'handover_date': datetime.date.today(),
        })

        return res
        
    def print_payslips_as_nonpaid(self):
        self.ensure_one()
        context = self._context
        wizard_data = {
            'pay_date': self.pay_date,
            'print_date': self.print_date,
            'handover_date': self.handover_date,
            'authorised_person': self.authorised_person,
        }
        if context.get('whole_payslip_run', False):
            slip_obj = self.env["hr.payslip"]
            slip_ids = slip_obj.search([('payslip_run_id', 'in', context['active_ids'])]).ids
        else:
            slip_ids = context['active_ids']
        data = {}
        data['wizard_data'] = wizard_data
        data['active_ids'] = slip_ids

        if context.get('report_no1_type', False):
            report_id = 'l10n_hr_hr_payroll.no1_report'
            return self.env.ref(report_id).report_action(self, data)
        report_id = 'l10n_hr_hr_payroll.hr_payslip_nonpaid_report'
        return self.env.ref(report_id).report_action(self, data)
