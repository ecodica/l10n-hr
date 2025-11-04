from odoo import fields, models


class Certificate(models.Model):
    _inherit = 'certificate.certificate'

    scope = fields.Selection(
        selection_add=[
            ('fina', 'Fina'),
        ],
    )
    l10n_hr_type = fields.Selection(
        selection=[
            ("prod", "Prod"),
            ("demo", "Demo"),
            ("other", "Other/Unknown"),
        ],
        readonly=False,
        string="FINA type"
    )
