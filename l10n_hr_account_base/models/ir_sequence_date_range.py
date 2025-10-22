from odoo import fields, models


class IrSequenceDateRange(models.Model):
    _inherit = "ir.sequence.date_range"

    def name_get(self):
        res = [(d.id, "%s-%s" % (d.date_from.year, d.number_next_actual)) for d in self]
        return res
