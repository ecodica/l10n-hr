from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    l10n_hr_sale_journal_id = fields.Many2one(
        comodel_name='account.journal', 
        string='Sale Journal', 
        domain=[('type', '=', 'sale')])
    l10n_hr_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal', 
        string='Purchase Journal', 
        domain=[('type', '=', 'purchase')])
