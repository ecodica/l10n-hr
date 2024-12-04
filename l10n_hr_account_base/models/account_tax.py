from odoo import fields, models

class AccountTax(models.Model):
    '''Inherit Account tax to add notes field to the taxes '''
    _inherit = "account.tax"


    tax_notes = fields.Text(
        string='Notes',
        help='Additional notes related to this tax'
    )
