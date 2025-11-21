#-*- coding:utf-8 -*-

from odoo import models, fields, api, _


class HrJoppdFormA(models.Model):
    _name = "hr.joppd.form.a"
    _description = 'A strana JOPPD obrasca'
    
    joppd_id = fields.Many2one('hr.joppd.form', 'JOPPD', ondelete="cascade")
    position = fields.Many2one('hr.report.line','Pozicija',help="Pozicija JOPPD obrasca")
    val = fields.Float('Vrijednost', default=0.0)
    