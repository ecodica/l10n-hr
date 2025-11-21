# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class Info3WorkExpBenefit(models.Model):
    """
    This class is used to select benefit level on contract.
    Records are imported through info3.work.benefit.csv.
    """
    _name = 'info3.work.exp.benefit'
    _description = 'Razine beneficiranog staža'

    _internship_type_sel = [
        ('0', '0 - None'),
        ('1', '1 - 12/14'),
        ('2', '2 - 12/15'),
        ('3', '3 - 12/16'),
        ('4', '4 - 12/18'),
    ]
        
    salary_parameters_ids = fields.One2many('hr.salary.parameters', 'benefit_id', 'Parametri plaće')
    internship_type = fields.Selection(_internship_type_sel, 'Staž s povećanim trajanjem', required=True)
    mio_2 = fields.Boolean('MIO II stup')
    dmio1b = fields.Float(string='Dodatni doprinos za 1. stup (%)')
    dmio2b = fields.Float(string='Dodatni doprinos za 2. stup (%)')
