# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from datetime import date
from dateutil.relativedelta import relativedelta

class DuplicateContract(models.TransientModel):
    _name = 'duplicate.contract.wizard'
    _description = 'Wizard for choosing parameters when duplicating contract'
    
    duplicate_parameters = fields.Boolean('Dupliciraj parametre plaće')
    contract_id = fields.Many2one('hr.contract', 'Contract')

    def duplicate_contract(self):
        duplicated_contract = self.contract_id.copy(default={})

        if self.duplicate_parameters and self.contract_id.salary_parameters_ids:
            self.contract_id.salary_parameters_ids[0].copy(default={'contract_id': duplicated_contract.id})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.contract',
            'res_id': duplicated_contract.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        id = self._context.get('default_contract_id')
        if id:
            res['contract_id'] = id
        return res
