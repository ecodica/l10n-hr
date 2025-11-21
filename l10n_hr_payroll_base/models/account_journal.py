# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    _order = 'sequence, id, type, code'

    type = fields.Selection(
        selection_add=[('travel_order', 'Travel Order'),
        ('compensation', 'Compensation'),
        ('payroll', 'Payroll')
    ], required=True,
        help="Select 'Sale' for customer invoices journals.\n" \
             "Select 'Purchase' for vendor bills journals.\n" \
             "Select 'Cash' or 'Bank' for journals that are used in customer or vendor payments.\n" \
             "Select 'General' for miscellaneous operations journals.\n" \
             "Select 'Travel Order' for travel order journals",
        ondelete={
            'travel_order': 'cascade',
            'compensation': 'cascade',
            'payroll': 'cascade',
        },)


    def get_journal_invoice_type_map(self):
       """ Extend get_journal_invoice_type_map() method to add new types in journal_invoice_type_map for accounting dashboard """
       res = super(AccountJournal, self).get_journal_invoice_type_map()
       res.update({
            ('travel_order', None): 'travel_order',
            ('payroll', None): 'payroll',
       })
       return res

    @api.onchange('code')
    def _check_code(self):
        if self.code:
            res = self.env['account.journal'].search([('code','=',self.code)])
            if len(res):
                raise ValidationError(_("You need to enter unique code."))

    def _compute_display_name(self):
        for journal in self:
            currency = journal.currency_id
            if currency:
                name = "%s (%s)" % (journal.name, currency.name)
            else:
                name = "%s" % journal.name
            journal.display_name = name
