from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    city_municipality_id = fields.Many2one(comodel_name='l10n.hr.joppd.code.register.city.municipality',
                                           string='City/Municipality',
                                           domain=[('type', '=', 'normal')],
                                           related='employee_id.city_municipality_id',
                                           store=True, readonly=False)
    city_municipality_work_id = fields.Many2one(comodel_name='l10n.hr.joppd.code.register.city.municipality',
                                                string='City/Municipality of Work',
                                                domain=[('type', '=', 'normal')],
                                                related='employee_id.city_municipality_work_id',
                                                store=True, readonly=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['city_municipality_id', 'city_municipality_work_id']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['city_municipality_id', 'city_municipality_work_id']
