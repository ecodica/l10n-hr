from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('account_id', 'employee_id')
    def _is_for_joppd(self):
        for line in self:
            if line.employee_id and line.joppd_payment_method_id and line.joppd_nontaxable_receipt_id:
                line.is_for_joppd = True

    is_for_joppd = fields.Boolean(string='Is for JOPPD?', compute='_is_for_joppd')
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        ondelete='restrict')
    joppd_payment_method_id = fields.Many2one(
        comodel_name='l10n.hr.joppd.code.register.payment.method',
        string='JOPPD Payment Method',
        ondelete='restrict',
        domain=[('type', '=', 'normal')])
    joppd_nontaxable_receipt_id = fields.Many2one(
        comodel_name='l10n.hr.joppd.code.register.nontaxable.receipt',
        string='JOPPD Non-Taxable Receipt',
        ondelete='restrict',
        domain=[('type', '=', 'normal')])

    @api.onchange('account_id')
    def _onchange_joppd_account_id(self):
        if self.account_id.joppd_payment_method_id:
            self.joppd_payment_method_id = self.account_id.joppd_payment_method_id.id
        if self.account_id.joppd_nontaxable_receipt_id:
            self.joppd_nontaxable_receipt_id = self.account_id.joppd_nontaxable_receipt_id.id

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            line._onchange_joppd_account_id()
        return lines

