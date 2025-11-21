#-*- coding:utf-8 -*-

from odoo import models, fields, api


class HrReportLine(models.Model):
    _name = 'hr.report.line'
    _description = 'HR report line'
    
    _report_field_type = [
        ('char','Znakovni niz ograničene duljine'),
        ('txt','Polje za unos teksta proizvoljen duljine'),
        ('int', 'Cjelobrojni iznos'),
        ('float','decimalni iznos'),
        ('bool','DA/NE polje'),
        ('sel','Izbor zadanih podataka'),
        ('view','Informativno polje, ne traži unos podataka')
    ]
    
    sequence = fields.Integer('Redni broj')
    report_id = fields.Many2one('hr.report','Izvještaj')
    parent_id = fields.Many2one('hr.report.line','Nadređeni')
    code = fields.Char('Šifra',size=32)
    description = fields.Char('Opis',size=256)
    help_text = fields.Text('Pomoć')
    field_type = fields.Selection(_report_field_type,'Vrsta polja')
    required = fields.Boolean('Obavezno')
    
    @api.depends('description','code')
    def _compute_display_name(self):
        for line in self:
            line.display_name = " ".join([line['code'],line['description']])
