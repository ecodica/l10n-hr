from odoo import fields, models


class FiskalLog(models.Model):
    _name = "l10n.hr.fiskal.log"
    _description = "Fiskal messages log"

    name = fields.Char(size=64, readonly=True, help="Unique communication mark")
    type = fields.Selection(
        selection=[
            ("racuni", "Invoice fiscalisation"),
            ("rac_pon", "Late delivery for fiscalisation"),
            ("provjera", "Check/Verify fiscalisation data"),  # NOVO!
            ("pd", "Fiscalisation of attached document"),
            ("pd_rac", "Fiscalisation of invoice for attached doc"),
            ("echo", "Test service message"),
            ("other", "Other / Not recognized"),
        ],
        string="Message type",
        readonly=True,
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move", string="Invoice", readonly=True
    )
    fiskal_prostor_id = fields.Many2one(
        comodel_name="l10n.hr.fiskal.prostor", string="Premisse", readonly=True
    )
    fiskal_uredjaj_id = fields.Many2one(
        comodel_name="l10n.hr.fiskal.uredjaj", string="POS Device", readonly=True
    )
    sadrzaj = fields.Text(string="Sent message", readonly=True)
    odgovor = fields.Text(string="Reply", readonly=True)
    greska = fields.Text(string="Error", readonly=True)
    time_stamp = fields.Char(string="Reply TimeStamp", readonly=True)
    time_obr = fields.Char(string="Process time", readonly=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
        string="Person",
        help="Person which sent fiscalisation message",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
    )
