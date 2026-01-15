from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    sale_journal_id = fields.Many2one('account.journal', 'Sale Journal', domain=[('type', '=', 'sale')])
    purchase_journal_id = fields.Many2one('account.journal', 'Purchase Journal', domain=[('type', '=', 'purchase')])
    l10n_hr_operator_name = fields.Char(
        string="Operator Name",
        copy=False,
        help="It will be printed on reports instead of the full name of the partner when the operator (Fiscal User) "
         "is printed (e.g. on invoices)")
