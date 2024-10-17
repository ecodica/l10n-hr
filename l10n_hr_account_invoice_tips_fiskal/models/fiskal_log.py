from odoo import fields, models


class FiskalLog(models.Model):
    """"Extend to add new log type."""
    _inherit = "l10n.hr.fiskal.log"

    type = fields.Selection(
        selection_add=[('napojnica', "Tip fiscalisation")])
