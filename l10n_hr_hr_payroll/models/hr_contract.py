# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from datetime import datetime, timedelta

class Contract(models.Model):

    _inherit = 'hr.contract'

    termination_date = fields.Date('Datum prestanka radnog odnosa', help="Datum raskida ugovora.")
    salary_parameters_ids = fields.One2many('hr.salary.parameters', 'contract_id', 'Parametri plaće', tracking=True)
    # remove required attribute from wage field
    wage = fields.Monetary(required=False, string="Bruto plaća")

    active = fields.Boolean(tracking=True)
    job_id = fields.Many2one(tracking=True, string='Radno mjesto')
    date_start = fields.Date(tracking=True)
    date_end = fields.Date(tracking=True)
    trial_date_end = fields.Date(tracking=True, string='Kraj probnog rada')
    advantages = fields.Text('Prednosti', tracking=True)
    notes = fields.Text('Bilješke', tracking=True)

    def get_immediate_follower(self):
        """ Check if contract has an immediate follower.
            Definition: a contract for the same employee which starts the day after current contract ends.
            If current contract has no end date, it can not have a follower so we return an empty recordset.

        Returns:
            hr.contract recordset: empty recordset or the follower.
        """
        if not self.date_end:
            return self.env['hr.contract']
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '=', self.date_end + timedelta(days=1))
        ]
        immediate_follower = self.search(domain, limit=1)
        return immediate_follower
    
    def write(self, vals):
        """
        Set closing date = new contract end date on all salary parameters related to contract which end after it.
        """
        if 'date_end' in vals:
            for contract in self:
                contract_date_end = vals.get('date_end')
                self.update_params_end_date(contract.id, contract_date_end)
        return super().write(vals)

    def update_params_end_date(self, contract_id, contract_date_end):
        params_obj = self.env['hr.salary.parameters']
        params_domain = [
            ('contract_id', '=', contract_id),
            '|', ('date_to', '>', contract_date_end), ('date_to', '=', False)
        ]
        params_ids = params_obj.search(params_domain)
        if params_ids:
            params_ids.write({'date_to': contract_date_end})
        return True

    def open_duplicate_wizard(self):
        action = self.env.ref('l10n_hr_hr_payroll.action_duplicate_contract')

        wizard = self.env['duplicate.contract.wizard'].create({})
        return {
            'name': action.name,
            'type': 'ir.actions.act_window',
            'res_model': 'duplicate.contract.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': action.view_id.id,
            'target': 'new',
        }
