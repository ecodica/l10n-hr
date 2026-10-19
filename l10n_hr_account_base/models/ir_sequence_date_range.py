from odoo import api, models


class IrSequenceDate_Range(models.Model):
    _inherit = "ir.sequence.date_range"

    @api.depends("sequence_id", "date_from", "number_next_actual")
    def _compute_display_name(self):
        # "year - next number" label only for Croatian fiscal sequences;
        # every other sequence keeps the core rendering.
        fiscal = self.filtered(lambda d: d.sequence_id.code == "l10n_hr.fiscal")
        super(IrSequenceDate_Range, self - fiscal)._compute_display_name()
        for date_range in fiscal:
            date_range.display_name = "%s-%s" % (
                date_range.date_from.year, date_range.number_next_actual)
