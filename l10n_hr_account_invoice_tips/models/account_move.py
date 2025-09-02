from odoo import fields, models, api


class AccountMove(models.Model):
    ''' Extension to add Tip fields to invoice. '''
    _inherit = 'account.move'

    def _get_default_l10n_hr_account_payment_type_id(self):
        return self.journal_id and self.journal_id.l10n_hr_default_account_payment_type_id

    # deprecated field -------
    def _get_l10n_hr_nacin_placanja(self):
        return self.journal_id.l10n_hr_default_nacin_placanja

    def _get_l10n_hr_nacin_placanja_options(self):
        return self.env['account.move']._fields['l10n_hr_nacin_placanja']._description_selection(self.env)

    l10n_hr_napojnica_nacin_placanja = fields.Selection(
        selection=_get_l10n_hr_nacin_placanja_options,
        string="Tip Payment Method",
        default=lambda self: self._get_l10n_hr_nacin_placanja()
    )
    # ------------------------

    l10n_hr_napojnica_iznos = fields.Monetary(
        string='Tip Amount',
        currency_field='currency_id')

    l10n_hr_account_tip_payment_type_id = fields.Many2one(
        'l10n_hr.account.payment.type',
        string="Tip Payment Method",
        default=lambda self: self._get_default_l10n_hr_account_payment_type_id()
    )

    l10n_hr_enable_tips_on_invoice = fields.Boolean(
        related='company_id.l10n_hr_enable_tips_on_invoice',
    )
