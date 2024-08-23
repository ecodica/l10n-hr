from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('account_id', 'l10n_hr_employee_id')
    def _is_for_joppd(self):
        for line in self:
            line.l10n_hr_is_for_joppd = False
            if line.l10n_hr_employee_id and \
                    line.l10n_hr_joppd_payment_method_id and line.l10n_hr_joppd_nontaxable_receipt_id:
                line.l10n_hr_is_for_joppd = True

    l10n_hr_is_for_joppd = fields.Boolean(string='Is for JOPPD?', compute='_is_for_joppd')
    l10n_hr_employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        ondelete='restrict')
    l10n_hr_joppd_payment_method_id = fields.Many2one(
        comodel_name='l10n.hr.joppd.code.register.payment.method',
        string='JOPPD Payment Method',
        ondelete='restrict',
        domain=[('type', '=', 'normal')])
    l10n_hr_joppd_nontaxable_receipt_id = fields.Many2one(
        comodel_name='l10n.hr.joppd.code.register.nontaxable.receipt',
        string='JOPPD Non-Taxable Receipt',
        ondelete='restrict',
        domain=[('type', '=', 'normal')])

    @api.onchange('account_id')
    def _onchange_joppd_account_id(self):
        if self.account_id.l10n_hr_joppd_payment_method_id:
            self.l10n_hr_joppd_payment_method_id = self.account_id.l10n_hr_joppd_payment_method_id.id
        if self.account_id.l10n_hr_joppd_nontaxable_receipt_id:
            self.l10n_hr_joppd_nontaxable_receipt_id = self.account_id.l10n_hr_joppd_nontaxable_receipt_id.id

    # this may be obsolete
    # ...apparently not
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if not (line.l10n_hr_joppd_payment_method_id and line.l10n_hr_joppd_nontaxable_receipt_id):
                line._onchange_joppd_account_id()
        return lines

