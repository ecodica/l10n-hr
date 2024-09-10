# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountAnalyticDistributionModel(models.Model):
    _inherit = 'account.analytic.distribution.model'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        domain = [
                     ('account_prefix', operator, name),
                 ] + (args or [])
        recs = self.search(domain, limit=limit)
        return recs.name_get()
