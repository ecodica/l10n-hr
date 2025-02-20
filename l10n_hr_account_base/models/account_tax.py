from odoo import models


class AccountTax(models.Model):
    _inherit = "account.tax"
    _rec_names_search = ['name', 'invoice_label']
    #NOTE: removed 'description' from _rec_names_search because we have long descriptions of taxes
    #      that add uneccessary taxes to the search
