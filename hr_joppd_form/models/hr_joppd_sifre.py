#-*- coding:utf-8 -*-

from odoo import models, fields, api, _
        
class HrJoppdSifre(models.Model):
    _name = 'l10n.hr.joppd.sifre'
    _description = 'JOPPD šifre'
    _order = 'code_type, sort_name'
    
    code_type = fields.Char('Vrsta šifre',size=32)
    name = fields.Char('Šifra', size=32, index=1)
    sort_name = fields.Char('Šifra za sortiranje', size=32, index=1, compute='_compute_sort_name', store=True, help="Ovo polje se koristi samo za ispravno sortiranje.")
    description = fields.Char('Opis', size=512) 
    
    #TODO: search po sifri i/ili nazivu!

    @api.depends('name')
    def _compute_sort_name(self):
        """
        Add leading zeroes to name so sorting works as intended (0, 1, 2, 3, ... instead of 0, 1, 10, ...).
        The 'correct' way to do this is to add zeroes to name directly,
        but in that case we would need to modify a big part of the logic
        so this workaround is used.
        """
        for sifra in self:
            sifra.sort_name = "{:0>4}".format(sifra.name)

    def _compute_display_name(self):
        for sifra in self:
            name = u'{0}'.format(sifra.name)
            if sifra.description and sifra.description != u' ':
                name += u' - {0}'.format(sifra.description)[:100]
            sifra.display_name = name

    def _add_to_payment_order(self):
        """ Check if a payment method is a candidate for the payment order.
            Only payments to bank accounts go into the payment order, meaning:
            - code_type needs to be P-5 because other types are not for payments
            - only candidates are 1 - Isplata na tekuci racun and 2 - Isplata na ziro racun
        """
        if self.code_type != 'P-5':
            return False
        if self.name not in ('1', '2'):
            return False
        return True