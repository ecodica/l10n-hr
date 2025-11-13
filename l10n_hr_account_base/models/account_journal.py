from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # original fields modification
    code = fields.Char(size=16)

    # new fields needed for localization
    l10n_hr_business_premise_id = fields.Many2one(
        comodel_name="l10n_hr.business.premise",
        string="Business Premise")
    l10n_hr_fiscal_device_ids = fields.Many2many(
        comodel_name="l10n_hr.fiscal.device",
        relation="l10n_hr_fiscal_device_account_journal_rel",
        column1="l10n_hr_journal_id",
        column2="l10n_hr_fiscal_device_id",
        string="Allowed PoS Devices")
    l10n_hr_default_account_payment_type_id = fields.Many2one(
        comodel_name='l10n_hr.account.payment.type',
        ondelete="restrict",
        string="Default fiscal payment method for this journal",
        default=lambda self: self.env['account.move'].get_default_l10n_hr_account_payment_type())
