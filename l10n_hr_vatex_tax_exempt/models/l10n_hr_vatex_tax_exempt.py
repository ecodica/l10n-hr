from odoo import models, fields, api


class L10nHrVatexTaxExempt(models.Model):
    _name = "l10n.hr.vatex.tax.exempt"
    _description = "Defines VATEX tax category."
    _inherit = ['mail.thread']

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True, translate=True)
    # Not stored: it is built from the translated name, so it has to be
    # evaluated per language instead of frozen at compute time.
    display_name = fields.Char(string="Display Name", compute='_compute_display_name')
    description = fields.Text(string="Description", translate=True)

    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        "The VATEX tax exempt code has to be unique!",
    )

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for exempt in self:
            exempt.display_name = False
            if exempt.code and exempt.name:
                exempt.display_name = exempt.code + ' - ' + exempt.name
