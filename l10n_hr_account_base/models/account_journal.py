from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # original fields modification
    code = fields.Char(size=16)

    # new fields needed for localization
    l10n_hr_business_premise_id = fields.Many2one(
        comodel_name="l10n.hr.business.premise",
        string="Business Premise")
    l10n_hr_fiscal_device_ids = fields.Many2many(
        comodel_name="l10n.hr.fiscal.device",
        relation="l10n_hr_fiscal_device_account_journal_rel",
        column1="l10n_hr_journal_id",
        column2="l10n_hr_fiscal_device_id",
        string="Allowed PoS Devices")
    l10n_hr_default_fiscal_payment_method = fields.Selection(
        selection=[("T", "Bank transfer")],
        string="Default fiscal payment method for this journal",
        default="T")
