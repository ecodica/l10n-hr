from odoo import models, fields, api


class L10nHrTaxCategory(models.Model):
    _name = "l10n.hr.tax.category"
    _description = "Defines UNTDID5305 tax category."
    _inherit = ['mail.thread']

    code = fields.Char(string="Code", required=True)
    untdid_5305_code = fields.Char(string="UNTDID 5305 Code", required=True,
                                   help='Tax code defined by UNTDID 5305 standard(BT-118)')
    l10n_hr_untdid_5305_code = fields.Char(string="Croatian UNTDID 5305 Code", required=True,
                                   help='Croatian Tax code defined by UNTDID 5305 standard(BT-18)')
    untdid_5153_code = fields.Char(string="UNTDID 5153 Code", required=True,
                                   help='Tax scheme code defined by UNTDID 5153 standard')
    name = fields.Char(string="Name", required=True)
    display_name = fields.Char(string="Display Name", compute='_compute_display_name', store=True)
    description = fields.Text(string="Description")
    is_pass_through_charge = fields.Boolean(
        string="Pass-through Charge", compute='_compute_is_pass_through_charge', store=True,
        help="A category is a pass-through charge when its UNTDID 5305 code (BT-118) is E while "
             "its Croatian code (HR-BT-18) is O, which the shipped codebook states for "
             "HR:POVNAK, HR:PP, HR:PPMV and HR:N. Such a charge is collected on behalf of a "
             "third party and stays outside the VAT base (čl. 33. st. 3), so it is not a supply "
             "exempt from VAT and no VATEX code from the codebook applies to it.")
    pass_through_reason_text = fields.Char(
        string="Default Exemption Reason", translate=True,
        help="Reason text an eRačun states for a pass-through charge in this category, unless "
             "the tax itself names another. Empty where the category name cannot serve as the "
             "reason: HR:N shares its name verbatim with HR:O, so only the tax knows which "
             "charge it carries.")

    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        "The tax category code has to be unique!",
    )

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for category in self:
            if category.code and category.name:
                category.display_name = category.code + ' - ' + category.name

    @api.depends('untdid_5305_code', 'l10n_hr_untdid_5305_code')
    def _compute_is_pass_through_charge(self):
        """The one definition of the pass-through rule.

        The codes are compared as an ordered pair, not for membership: a genuine exemption
        states E on both sides and HR:O states O on both sides, so only E/O marks a charge that
        is merely passed through. Stored so the flag can be searched.
        """
        for category in self:
            category.is_pass_through_charge = (
                category.untdid_5305_code, category.l10n_hr_untdid_5305_code) == ('E', 'O')
