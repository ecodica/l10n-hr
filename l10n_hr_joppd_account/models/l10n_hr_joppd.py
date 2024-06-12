from odoo import fields, models, api, _


class L10nHrJOPPD(models.Model):
    _inherit = 'l10n.hr.joppd'

    def calculate_sideB_rows_from_entries(self):
        sideB_obj = self.env['l10n.hr.joppd.b']
        joppd_entry_obj = self.env['l10n.hr.joppd.account.move.entry']
        index = 0
        # unlink before creating new lines
        self.sideB_ids.unlink()
        for joppd_report in self:
            entries_domain = [('date', '>=', joppd_report.period_date_from_joppd),
                              ('date', '<=', joppd_report.period_date_to_joppd),
                              ('state', 'not in', ['done', 'cancel']),
                              # ('company_id', '=', self.company_id.id),
                              ]
            entries = joppd_entry_obj.sudo().search(entries_domain)
            employees_missing_data = entries.employee_id.filtered(
                lambda l: not l.l10n_hr_city_municipality_id or not l.l10n_hr_city_municipality_work_id)
            if employees_missing_data:
                warnings = ("Employees %s don't have City/Municipality data, please correct it before proceeding!"
                            % ', '.join(employees_missing_data.mapped('name')))
                notification = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Warning'),
                        'type': 'warning',
                        'message': warnings,
                        'sticky': True,
                    }
                }
                return notification
            for entry in entries:
                index += 1
                vals = dict(
                    joppd_id=joppd_report.id,
                    joppd_move_entry_id=entry.id,
                    b1=index,
                    b2=entry.employee_id.l10n_hr_city_municipality_id.code,
                    b3=entry.employee_id.l10n_hr_city_municipality_work_id.code,
                    b4=entry.employee_id.ssnid,
                    b5=entry.employee_id.name,
                    b151=entry.nontaxable_receipt_id.code,
                    b161=entry.payment_method_id.code,
                    b101=joppd_report.period_date_from_joppd,
                    b102=joppd_report.period_date_to_joppd,
                    b152=entry.amount,
                    b162=entry.amount,
                    b61='0000',
                    b62='0000'
                )
                sideB_obj.create(vals)

    def button_done_editing(self):
        res = super().button_done_editing()
        self.mapped('sideB_ids.joppd_move_entry_id').write({'state': 'done'})
        return res

    def button_set_draft(self):
        res = super().button_set_draft()
        self.mapped('sideB_ids.joppd_move_entry_id').write({'state': 'ready'})
        return res
