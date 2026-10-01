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
        help="Reason text an eRačun states for a pass-through charge in this category (BT-118 "
             "E with HR-BT-18 O), unless the tax itself names another. Empty where the category "
             "name cannot serve as the reason: HR:N shares its name verbatim with HR:O, so only "
             "the tax knows which charge it carries.")

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'The tax category code has to be unique!')
    ]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for category in self:
            if category.code and category.name:
                category.display_name = category.code + ' - ' + category.name
