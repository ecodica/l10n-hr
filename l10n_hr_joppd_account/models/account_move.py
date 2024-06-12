from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('line_ids')
    def _is_for_joppd(self):
        for move in self:
            move.l10n_hr_is_for_joppd = False
            for line in move.line_ids:
                if line.l10n_hr_is_for_joppd:
                    move.l10n_hr_is_for_joppd = True
                    break

    l10n_hr_joppd_posted = fields.Boolean(
        string='JOPPD Posted', readonly=True, copy=False, help='JOPPD Posted')
    l10n_hr_is_for_joppd = fields.Boolean(string='Is for JOPPD?', compute='_is_for_joppd')

    def post_joppd(self, post_date=None):
        joppd_entry_obj = self.env['l10n.hr.joppd.account.move.entry']
        allowed_journal_types = {'cash', 'bank', 'purchase', 'general'}
        for move in self.filtered(lambda m: m.l10n_hr_is_for_joppd and m.journal_id.type in allowed_journal_types):
            date_payment = post_date or move.date
            if move.journal_id.type == 'general':
                date_payment = False
            for line in move.line_ids.filtered(lambda l: l.l10n_hr_is_for_joppd):
                entry_vals = dict(
                    name=line.name or line.move_id.name,
                    state=date_payment and 'ready' or 'wait',
                    move_id=move.id,
                    move_line_id=line.id,
                    date=post_date or move.date,
                    date_payment=date_payment,
                    employee_id=line.l10n_hr_employee_id.id,
                    nontaxable_receipt_id=line.l10n_hr_joppd_nontaxable_receipt_id.id,
                    payment_method_id=line.l10n_hr_joppd_payment_method_id.id,
                    amount=line.debit - line.credit,
                    company_id=move.company_id.id
                )
                joppd_entry_obj.create(entry_vals)
            move.l10n_hr_joppd_posted = True
