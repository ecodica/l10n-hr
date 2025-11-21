# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class WorkExperienceFeeLimit(models.Model):
    _name = 'work.experience.fee.limit'
    _description = "Ograničenja za jubilarnu nagradu"

    years = fields.Float('Godina', required=True)
    max_amount = fields.Float('Ograničenje', required=True)
