from odoo import models, fields, api, _

OPZ_STAT_VAT_IDS = [
    ("vat", "1"),
    ("vat_id", "2"),
    ("other", "3"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    opz_stat_vat_id = fields.Selection(OPZ_STAT_VAT_IDS, compute='_compute_opz_stat_id', string="OPZ-STAT ID",
                                       required=True, prefetch=False, index=True, readonly=False, store=True,
                                       default=OPZ_STAT_VAT_IDS[0][0])

    @api.depends('vat', 'country_id')
    def _compute_opz_stat_id(self):
        for partner in self:
            if partner.vat:
                if partner.vat.startswith('HR') or (partner.country_id and partner.country_id.code == 'HR'):
                    partner.opz_stat_vat_id = 'vat'
                elif partner.country_id:
                    partner.opz_stat_vat_id = 'vat_id'
                else:
                    partner.opz_stat_vat_id = 'other'
            else:
                partner.opz_stat_vat_id = 'other'
