from odoo import fields, models


class L10nHrFiscalLog(models.Model):
    _name = "l10n_hr.fiscal.log"
    _description = "Fiscal messages log"

    name = fields.Char(size=64, readonly=True, help="Unique communication mark")
    user_id = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
        string="Person",
        help="Person which sent fiscalization message",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        readonly=True,
    )
    type = fields.Selection(
        selection=[
            ("racuni", "Invoice fiscalization"),
            ("rac_pon", "Late delivery for fiscalization"),
            ("provjera", "Check/Verify fiscalization data"),  # NOVO!
            ("pd", "Fiscalization of attached document"),
            ("pd_rac", "Fiscalization of invoice for attached doc"),
            ("echo", "Test service message"),
            ("other", "Other / Not recognized"),
        ],
        string="Message type",
        readonly=True,
    )
    # related document
    res_model = fields.Char('Related Document Model', readonly=True, required=True)
    res_id = fields.Many2oneReference('Related Document ID', model_field='res_model', readonly=True, required=True)
    business_premise_id = fields.Many2one(comodel_name="l10n_hr.business.premise",
                                          string="Business Premise", readonly=True)
    fiscal_device_id = fields.Many2one(comodel_name="l10n_hr.fiscal.device", string="POS Device", readonly=True)
    content = fields.Text(string="Sent message", readonly=True)
    reply_msg = fields.Text(string="Reply", readonly=True)
    error_msg = fields.Text(string="Error", readonly=True)
    reply_timestamp = fields.Char(string="Reply TimeStamp", readonly=True)
    process_time = fields.Char(string="Process time", readonly=True)
