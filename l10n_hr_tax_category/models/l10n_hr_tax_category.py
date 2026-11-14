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
    pass_through_reason_text = fields.Char(
        string="Default Exemption Reason", translate=True,
        help="Reason text proposed on a tax of this category for a pass-through charge (BT-118 "
             "E with HR-BT-18 O), prefixed with the category code. Empty where the category "
             "name cannot serve as the reason: HR:N shares its name verbatim with HR:O, so only "
             "the tax knows which charge it carries.")

    exemption_reason_mode = fields.Selection(
        selection=[
            ('none', 'No exemption reason'),
            ('reason', 'Exemption reason'),
            ('pass_through', 'Generated pass-through reason'),
        ],
        string="Exemption Reason Mode", compute='_compute_exemption_reason_mode',
        help="Whether a VAT breakdown in this category states an exemption reason. Follows "
             "BT-118: S and Z forbid one (BR-S-10, BR-Z-10), every other code requires one "
             "(BR-E-10, BR-AE-10, BR-IC-10, BR-G-10, BR-O-10). A pass-through charge (BT-118 E "
             "with HR-BT-18 O) is outside the VATEX codebook and gets a generated reason.")

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'The tax category code has to be unique!')
    ]

    @api.depends('untdid_5305_code', 'l10n_hr_untdid_5305_code')
    def _compute_exemption_reason_mode(self):
        for category in self:
            if category.untdid_5305_code in ('S', 'Z', 'L', 'M'):
                category.exemption_reason_mode = 'none'
            elif category.untdid_5305_code == 'E' and category.l10n_hr_untdid_5305_code == 'O':
                category.exemption_reason_mode = 'pass_through'
            else:
                category.exemption_reason_mode = 'reason'

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for category in self:
            if category.code and category.name:
                category.display_name = category.code + ' - ' + category.name
