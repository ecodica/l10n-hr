# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class Info3RescheduledHours(models.Model):
    """
    This class is used as an overview of employee's resheduled hours by month, as entered on timesheet.
    Internal system user is given all access rights except write because of the way rescheduled hours are calculated,
    but can not see the tab on employee form view.
    Payroll officer has all access rights and can see the tab.
    """
    _name = 'info3.rescheduled.hours'
    _description = 'Preraspodjeljeni sati zaposlenika po mjesecima'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='ID zaposlenika', ondelete='cascade')
    date = fields.Char(string='Godina i mjesec')
    number_of_hours = fields.Float(string='Broj sati')
