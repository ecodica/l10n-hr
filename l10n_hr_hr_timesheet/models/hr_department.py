# -*- coding: utf-8 -*-
from odoo import models, fields


class Department(models.Model):    
    _inherit = 'hr.department'
    
    manager_add_on_timesheet = fields.Boolean('Manager can add himself on timesheet')
    