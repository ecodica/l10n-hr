# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from datetime import datetime, timedelta
from dateutil import relativedelta

from odoo import fields, api, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT


class hr_payslip_employees(models.TransientModel):

    _inherit ='hr.payslip.employees'
    
    def compute_sheet(self):
        emp_obj = self.env['hr.employee']
        slip_obj = self.env['hr.payslip']
        run_obj = self.env['hr.payslip.run']
        param_obj = self.env['hr.salary.parameters']
        company = self.env.user.company_id
        slip_list = []
        data = self.read()[0]
        run = {}
        if self.env.context and self.env.context.get('active_id', False):
            run = run_obj.browse(self.env.context.get('active_id', False))

        date_from =  run['date_start']
        date_to = run['date_end']
        credit_note = run['credit_note']
        work_hours =  run['period_work_hours']
        journal_id =  run['journal_id']
        journal_id = journal_id and journal_id.id or False

        month_number_of_days = (date_to - date_from).days + 1
        # get min and max sick leave fee to update sick leave hourly rate
        min_sick_leave_fee_net = company.i3_config_min_sick_leave_fee_net
        max_sick_leave_fee_net = company.i3_config_max_sick_leave_fee_net
        if not data['employee_ids']:
            raise UserError(_("Potrebno je odabrati zaposlenike da bi se mogli generirati listići"))
        employees_with_invalid_params = ''
        for emp in emp_obj.browse(data['employee_ids']):
            param_domain = [
                '&', ('employee_id', '=', emp.id),
                '&', ('date_from', '<=', date_to),
                '|', ('date_to', '>=', date_from), ('date_to', '=', False)
            ]
            params_ids = param_obj.search(param_domain, order='date_from ASC')
            if not params_ids:
                employees_with_invalid_params += '\n' + emp.name
            for params in params_ids:
                params_date_from = date_from if params.date_from < date_from else params.date_from
                params_date_to =  date_to if (params.date_to and params.date_to > date_to or not params.date_to) else params.date_to
                contract_id = params.contract_id
                slip_data = slip_obj.get_employee_slip_data(params_date_from, params_date_to, emp.id, contract_id.id, params)
                emp_number_of_days = (params_date_to - params_date_from).days + 1
                res = {
                    'employee_id': emp.id,
                    'name': slip_data['value'].get('name', False),
                    'salary_parameters_id': params.id,
                    'contract_id': params.contract_id.id,
                    'struct_id': params.struct_id.id,
                    'payslip_run_id': self.env.context.get('active_id', False),
                    'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids', False)],
                    'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids', False)],
                    'employee_number_of_days_in_month': month_number_of_days,
                    'employee_number_of_days_at_work': emp_number_of_days,
                    'date_from': params_date_from,
                    'date_to': params_date_to,
                    'credit_note': credit_note,
                    'min_sick_leave_hourly_rate': float(min_sick_leave_fee_net) / work_hours,
                    'max_sick_leave_hourly_rate': float(max_sick_leave_fee_net) / work_hours,
                }
                slip_list.append(res)
        slip_ids = slip_obj.with_context({'journal_id': journal_id}).create(slip_list)
        
        if employees_with_invalid_params:
            raise UserError(_(u"Zaposlenici s nevaljanim parametrima plaće za odabrano razdoblje: {0}").format(employees_with_invalid_params))

        run.update_employee_tax_base()
        # use context to handle profit payment - structure has been set on create() so we don't want to revert it immediately
        slip_ids.with_context(on_create = True).get_calculation_parameters()
        return {'type': 'ir.actions.act_window_close'}
