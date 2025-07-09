# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    tax_clause = fields.Text(
        string='Tax Clause',
        compute='_compute_tax_clause', store=True, readonly=False, precompute=True,
    )

    @api.depends('invoice_line_ids.tax_ids')
    def _compute_tax_clause(self):
        for invoice in self:
            if invoice.partner_id.lang:
                taxes = invoice.invoice_line_ids.tax_ids.with_context(lang=invoice.partner_id.lang)
            else:
                taxes = invoice.invoice_line_ids.tax_ids
            invoice.tax_clause = '\n'.join([tax.tax_clause for tax in taxes if tax.tax_clause])
