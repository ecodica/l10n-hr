from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_default_l10n_hr_account_payment_type(self):
        """ Try to return 'Bank Transfer' as default payment type """
        return self.env['account.move'].get_default_l10n_hr_account_payment_type()

    # original fields modification
    code = fields.Char(size=16)

    # new fields needed for localization
    l10n_hr_prostor_id = fields.Many2one(
        comodel_name="l10n.hr.fiskal.prostor",
        string="Business Premise",
    )
    l10n_hr_fiskal_uredjaj_ids = fields.Many2many(
        comodel_name="l10n.hr.fiskal.uredjaj",
        relation="l10n_hr_fiskal_uredjaj_account_journal_rel",
        column1="journal_id",
        column2="uredjaj_id",
        string="Allowed PoS Devices",
    )
    l10n_hr_default_account_payment_type_id = fields.Many2one(
        comodel_name='l10n_hr.account.payment.type',
        string="Default fiscal payment type for this journal",
        ondelete="restrict",
        default=lambda self: self._get_default_l10n_hr_account_payment_type()
    )
