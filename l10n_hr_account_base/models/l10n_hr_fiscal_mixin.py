from odoo import fields, models, api


class L10nHrFiscalMixin(models.AbstractModel):
    _name = 'l10n_hr.fiscal.mixin'
    _description = 'Fiscal Mixin class for joint fields'

    l10n_hr_date_document = fields.Date(
        string="Document Date",
        copy=False,
        help="Date when the document was actually created. "
             "Leave blank for current date.")
    l10n_hr_fiscal_time = fields.Char(
        string="Time Of Fiscalization",
        copy=False,
        help="Croatia Fiscal datetime value as string, should respect format: hh:mm")
    l10n_hr_fiscal_number = fields.Char(
        string="Fiscal Number",
        copy=False,
        readonly=True,
        help="Required fiscal number, generated according to "
             "regulations regardless of journal number.")
    l10n_hr_payment_method = fields.Selection(
        selection=[("G", "Cash"),
                   ("K", "Credit or debit cards"),
                   ("T", "Bank transfer"),
                   ("O", "Other payment means"),
                   ],
        string="Croatia - Payment Method",
        default="T",
        help="According to Fiscalization Law and regulative "
             "there are 4 possible options: \n"
             "G - Cash (coins or bills), fiscalization required\n"
             "K - Bank cards, fiscalization required\n"
             "T - Transaction bank account\n"
             "O - Other payment, fiscalization required\n", )
    l10n_hr_fiscal_device_id = fields.Many2one(
        comodel_name="l10n_hr.fiscal.device",
        string="Fiscal Device",
        help="Device that registers fiscal payment.")
    l10n_hr_fiscal_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Fiscal User",
        domain=lambda self: self._get_l10n_hr_fiscal_user_id_domain(),
        ondelete='restrict',
        default=lambda self: self.env.user.id,
        copy=False,
        help="User who sent the fiscalization message."
             " Can be different from responsible person on invoice.",
    )

    def _get_l10n_hr_fiscal_user_id_domain(self):
        """"Build domain to filter only internal partners."""
        internal_users = self.env.ref('base.group_user')
        domain = [('user_ids', 'in', internal_users.users.ids)]
        return domain

    @api.constrains('l10n_hr_fiscal_number', 'company_id', 'date')
    def _check_l10n_hr_fiscal_number(self):
        raise NotImplementedError('Must be implemented!')
