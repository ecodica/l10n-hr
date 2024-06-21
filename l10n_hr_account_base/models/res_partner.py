from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    sale_journal_id = fields.Many2one('account.journal', 'Sale Journal', required=1, company_dependent=1,
                                      domain=[('type', '=', 'sale')])
    purchase_journal_id = fields.Many2one('account.journal', 'Purchase Journal', required=1, company_dependent=1,
                                          domain=[('type', '=', 'purchase')])
