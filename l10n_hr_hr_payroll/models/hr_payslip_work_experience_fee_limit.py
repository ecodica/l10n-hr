# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class HrPayslipWorkExperienceFeeLimit(models.Model):
    _name = 'hr.payslip.work.experience.fee.limit'
    _description = "Ograničenje za jubilarnu nagradu na isplatnom listiću"

    payslip_id = fields.Many2one('hr.payslip', 'Isplatni listić', ondelete='cascade')
    years = fields.Float('Godina', required=True)
    max_amount = fields.Float('Ograničenje', required=True)
