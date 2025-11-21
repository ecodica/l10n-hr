#-*- coding:utf-8 -*-

from odoo import models, fields, api, _


class HrJoppdFormCheckLine(models.Model):   
    _name = 'hr.joppd.form.check.line'    
    _description = 'JOPPD lines that need to be checked manually'

    joppd_id = fields.Many2one('hr.joppd.form','JOPPD id')
    sequence = fields.Integer('Redni broj')
    employee_id = fields.Many2one('hr.employee', 'Zaposlenik')
    description = fields.Char('Opis', size=512)


