from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    city_municipality_id = fields.Many2one(comodel_name='l10n.hr.joppd.code.register.city.municipality',
                                           string='City/Municipality', ondelete='restrict',
                                           domain=[('type', '=', 'normal')], groups="hr.group_hr_user",
                                           tracking=True)
    city_municipality_work_id = fields.Many2one(comodel_name='l10n.hr.joppd.code.register.city.municipality',
                                                string='City/Municipality of Work', ondelete='restrict',
                                                domain=[('type', '=', 'normal')], groups="hr.group_hr_user",
                                                tracking=True)
