#-*- coding:utf-8 -*-

from odoo import models, fields, api


class HrReport(models.Model):
    _name = 'hr.report'
    _description = 'HR Izvještaj'
    
    _report_type = [
        ('root','Root - Naziv izvještaja'),
        ('single','Neponavljajući podaci'),
        ('multi','Ponavljajući podaci')]

    name = fields.Char('Naziv izvještaja', size=256)
    code = fields.Char('Šifra izvještaja', size=32)
    report_type = fields.Selection(_report_type,'Tip')
    parent_id = fields.Many2one('hr.report','Nadređeni', ondelete='restrict')
    child_ids = fields.One2many('hr.report','parent_id',)
    line_ids = fields.One2many('hr.report.line','report_id','Stavke izvještaja')
