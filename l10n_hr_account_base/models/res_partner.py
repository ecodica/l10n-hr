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
    l10n_hr_operator_name = fields.Char(
        string="Operator Name",
        copy=False,
        help="It will be printed on reports instead of the full name of the partner when the operator (Fiscal User) "
         "is printed (e.g. on invoices)")
