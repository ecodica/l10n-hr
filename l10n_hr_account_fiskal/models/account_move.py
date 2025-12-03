from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.hr.fiskal.mixin", "l10n.hr.xml.mixin"]

    l10n_hr_nacin_placanja = fields.Selection(
        selection_add=[
            ("G", "Cash (bills and coins)"),
            ("K", "Credit or debit cards"),
            ("C", "Bank Cheque"),
            ("O", "Other payment means"),
        ],
        help="According to Fiscalization Law and regulative "
             "there is 5 possible options: \n"
             "T - Transaction bank account\n"
             "G - Cash (coins or bills), fiskalisation required\n"
             "K - Bank cards, fiskalisation required\n"
             "C - Cheque payment, fiskalisation required\n"
             "O - Other payment, fiskalisation required\n",
    )
    l10n_hr_fiskal_log_ids = fields.One2many(
        comodel_name="l10n.hr.fiskal.log",
        inverse_name="invoice_id",
        string="Fiskal message logs",
        help="Log of all messages sent and received for FINA",
    )

    def button_fiskaliziraj(self):
        self.ensure_one()
        # ako imam JIR pokreće provjeru ili ako nema fiskalizaciju.
        self.fiskaliziraj()  # from 10n.hr.fixcal.mixin

    def _l10n_hr_post_out_invoice(self):
        # singleton record! checked in super()
        res = super()._l10n_hr_post_out_invoice()
        # TODO selection or decision which to send ?
        bp_type = self.l10n_hr_business_process_type_id and self.l10n_hr_business_process_type_id.code or ''
        # Do not check/fiscalize for other business process types
        if bp_type != 'XF1':
            return res
        else:
            if self.l10n_hr_fiskal_uredjaj_id.fiskalisation_active:
                raise ValidationError(_("Fiscalization is not active for %s!! " % self.journal_id.display_name))
            else:
                self.fiskaliziraj()
        return res
