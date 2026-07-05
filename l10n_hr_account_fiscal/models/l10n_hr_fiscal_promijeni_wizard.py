from odoo import fields, models, _
from odoo.exceptions import UserError


class L10nHrFiscalPromijeniPodatkeWizard(models.TransientModel):
    _name = "l10n_hr.fiscal.promijeni.podatke.wizard"
    _description = "Wizard for promijeniPodatkeRacuna service"

    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        required=True,
        readonly=True,
    )
    new_payment_method = fields.Selection(
        selection=lambda self: self.env["account.move"]._fields[
            "l10n_hr_payment_method"
        ].selection,
        string="New Payment Method",
        help="Leave empty to keep the current payment method unchanged.",
    )
    new_recipient_oib = fields.Char(
        string="New Recipient OIB",
        size=11,
        help="Enter a new recipient OIB for B2B, or leave empty to clear it.",
    )
    clear_recipient_oib = fields.Boolean(
        string="Clear Recipient OIB",
        help="Check this to remove the recipient OIB from the invoice.",
    )

    def action_confirm(self):
        self.ensure_one()
        new_oib = None
        if self.clear_recipient_oib:
            new_oib = ""
        elif self.new_recipient_oib:
            new_oib = self.new_recipient_oib
        if not self.new_payment_method and new_oib is None:
            raise UserError(_("Nothing to change!"))
        self.move_id.fiscalize_promijeni_podatke_racuna(
            new_payment_method=self.new_payment_method or None,
            new_recipient_oib=new_oib,
        )
        return {"type": "ir.actions.act_window_close"}
