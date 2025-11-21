from odoo import api, fields, models


class HrHoliday(models.Model):
    _name = 'hr.holiday'
    _description = "Model for adding holidays"

    name = fields.Char(required=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
