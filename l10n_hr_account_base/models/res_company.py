from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    l10n_hr_fiskal_prostor_ids = fields.One2many(
        comodel_name="l10n.hr.fiskal.prostor",
        inverse_name="company_id",
        string="Business Premises",
    )
    l10n_hr_fiskal_separator = fields.Selection(
        selection=[
            ("/", "/"),
            ("-", "-"),
        ],
        string="Invoice Parts Separator",
        default="/",
        help="Only '/' or '-' are legaly defined as allowed",
    )
    l10n_hr_fiskal_invoice_sequences = fields.Many2many(
        comodel_name="ir.sequence",
        string="Invoice Fiskal Sequences For Company",
        compute="_compute_l10n_hr_sequences",
        context={"active_test": False},  # want to see inactive also!
    )
    l10n_hr_tax_model = fields.Selection(
        selection=[
            ("r1", "R1 - tax based on invoice"),
            ("r2", "R2 - tax based on payment"),
            ("r0", "R0 - NOT subject of taxation"),
            ("not_rh", "Not subject of taxation in Croatia"),
        ],
        string="Tax Model",
        required=True,
        tracking=True,
        default="r1",  # TODO: multicompany improove!
    )

    def _compute_l10n_hr_sequences(self):
        for company in self:
            sequences = (
                self.env["ir.sequence"]
                .with_context(active_test=False)
                .search(
                    [("company_id", "=", company.id), ("code", "=", "l10n_hr.fiscal")]
                )
            )
            company.l10n_hr_fiskal_invoice_sequences = [(4, s.id) for s in sequences]

    def l10n_hr_sequence_add_year(self):
        for sequence in self.l10n_hr_fiskal_invoice_sequences:
            if sequence.date_range_ids:
                last_date = sequence.date_range_ids.sorted(lambda l: l.date_to)[0]
                last_date.year + 1
            else:
                fields.Date.today().year


class IrSequenceDateRange(models.Model):
    _inherit = "ir.sequence.date_range"

    def name_get(self):
        res = [(d.id, "%s-%s" % (d.date_from.year, d.number_next_actual)) for d in self]
        return res
