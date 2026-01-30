from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_hr_business_process_type_id = fields.Many2one(
        comodel_name='l10n.hr.business.process.type',
        string="Business Process Type")

    l10n_hr_business_process_type_code = fields.Char(
        related='l10n_hr_business_process_type_id.code',
        string="Business Process Type Code")

    l10n_hr_business_process_name = fields.Char(
        string='Definition of business process for P99'
    )

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        res = super()._onchange_journal_id()
        if self.country_code != 'HR':
            return res
        self.l10n_hr_business_process_type_id = self.journal_id.l10n_hr_business_process_type_id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.country_code == 'HR' and not move.l10n_hr_business_process_type_id:
                move.l10n_hr_business_process_type_id = (move.journal_id
                                                         and move.journal_id.l10n_hr_business_process_type_id)
        return moves
