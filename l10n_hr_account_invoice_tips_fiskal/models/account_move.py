from odoo import api, fields, models


class AccountMove(models.Model):
    """Extend to add fields for tips fiskalization."""
    _inherit = 'account.move'

    l10n_hr_napojnica_is_fiscalized = fields.Boolean(string="Tip Is Fiskalized", copy=False)
    l10n_hr_napojnica_refund_fiscalized = fields.Boolean(string="Tip Refund Is Fiskalized", copy=False)
    l10n_hr_fiskal_log_ids = fields.One2many(domain=[('type', '!=', 'napojnica')])
    l10n_hr_fiskal_tips_log_ids = fields.One2many(
        comodel_name="l10n.hr.fiskal.log",
        inverse_name="invoice_id",
        domain=[('type', '=', 'napojnica')],
        string="Tip Fiskal Message Logs",
        help="Log of all messages sent and received for FINA tips fiskalization",
    )

    def button_fiskalize_tips(self):
        """Fiskalize napojnica"""
        self.ensure_one()
        self.fiskaliziraj(msg_type='napojnica')

    def button_fiskalize_tip_refund(self):
        """Fiskalize napojnica refund"""
        self.ensure_one()
        self.with_context(l10n_hr_tip_refund=True).fiskaliziraj(msg_type='napojnica')

    def _l10n_hr_post_out_invoice(self):
        """Extend to fiskalize tip after invoice is fiskalized."""
        res = super()._l10n_hr_post_out_invoice()
        # NOTE: try to fiskalize invoice tip after invoice is fiskalized
        if  self.company_id.l10n_hr_fiskal_tip_on_confirm and self._l10n_hr_fiscalization_needed('napojnica'):
            self.fiskaliziraj(msg_type='napojnica')
        return res

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """Extend to set l10n_hr_napojnica_iznosto 0.0 if refund is fiskalized."""
        default = dict(default or {})
        if self.l10n_hr_napojnica_refund_fiscalized and 'l10n_hr_napojnica_iznos' not in default:
            default['l10n_hr_napojnica_iznos'] = 0.0
        return super().copy(default=default)
