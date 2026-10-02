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
        if self.company_id.account_fiscal_country_id.code != "HR":
            return res
        if self.journal_id.l10n_hr_business_process_type_id:
            self.l10n_hr_business_process_type_id = self.journal_id.l10n_hr_business_process_type_id.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Back-fill the business process type from the journal.

        The onchange above only runs in the form view, so invoices built in
        Python (EDI import, API, cron) would otherwise have none, while it is
        required in the fiscalized XML. Only fills it in when still empty, so a
        value passed explicitly by the caller is kept.
        """
        moves = super().create(vals_list)
        for move in moves:
            if move.country_code == 'HR' and not move.l10n_hr_business_process_type_id:
                move.l10n_hr_business_process_type_id = (move.journal_id
                                                         and move.journal_id.l10n_hr_business_process_type_id)
        return moves
