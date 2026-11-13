from odoo import api, fields, models


class Company(models.Model):
    _inherit = "res.company"

    l10n_hr_business_premise_ids = fields.One2many(
        comodel_name="l10n_hr.business.premise",
        inverse_name="company_id",
        string="Business Premises")
    l10n_hr_fiscal_separator = fields.Selection(
        selection=[
            ("/", "/"),
            ("-", "-"),
        ],
        string="Invoice Parts Separator",
        default="/",
        help="Only '/' or '-' are legally defined as allowed.")
    l10n_hr_fiscal_invoice_sequence_ids = fields.Many2many(
        comodel_name="ir.sequence",
        string="Invoice Fiscal Sequences For Company",
        compute="_compute_l10n_hr_fiscal_invoice_sequence_ids",
        context={"active_test": False})  # want to see inactive also!
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
        default="r1")  # TODO: multicompany improve!
    l10n_hr_pdv_po_naplati = fields.Boolean(
        string="VAT on Payment",
        compute="_compute_l10n_hr_pdv_po_naplati",
        store=True,
        help="Follows the company Tax Model: set for R2 (VAT on payment).",
    )
    l10n_hr_show_required_fiscal_fields_on_header = fields.Boolean(
        string="Show Base Fiscalization Fields On Invoice",
        default=True)
    l10n_hr_tax_representative_party_id = fields.Many2one(
        'res.partner',
        string='Tax Representative Party',
        prefetch=False
    )

    @api.depends("l10n_hr_tax_model")
    def _compute_l10n_hr_pdv_po_naplati(self):
        for company in self:
            company.l10n_hr_pdv_po_naplati = company.l10n_hr_tax_model == "r2"

    def _compute_l10n_hr_fiscal_invoice_sequence_ids(self):
        for company in self:
            sequences = (
                self.env["ir.sequence"]
                .with_context(active_test=False)
                .search(
                    [("company_id", "=", company.id), ("code", "=", "l10n_hr.fiscal")]
                )
            )
            company.l10n_hr_fiscal_invoice_sequence_ids = [(4, s.id) for s in sequences]

    def l10n_hr_sequence_add_year(self):
        for sequence in self.l10n_hr_fiscal_invoice_sequence_ids:
            if sequence.date_range_ids:
                last_date = sequence.date_range_ids.sorted(lambda l: l.date_to)[0]
                last_date.year + 1
            else:
                fields.Date.today().year
