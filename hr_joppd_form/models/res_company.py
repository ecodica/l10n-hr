# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    _applicant_code_sel = [
        ('1',u'1 - Pravna osoba'),
        ('2',u'2 - Fizička osoba koja obavlja samostalnu djelatnost i po toj osnovi obveznik je poreza na dohodak ili poreza na dobit'),
        ('3',u'3 - Poslodavci diplomatske misije i konzularni uredi stranih država i međunarodnih organizacija koji u Republici Hrvatskoj uživaju diplomatski imunitet – za doprinose obračunane za osiguranike po osnovi radnog odnosa'),
        ('4',u'4 - Ostale fizičke osobe'),
        ('5',u'5 - Ostali poslovni subjekti'),
        ('6',u'6 - Škola ili ustanova za osiguranike'),
        ('7',u'7 - HZMO'),
        ('8',u'8 - HZZO'),
        ('9',u'9 - Ostala tijela (izuzev HZMO i HZZO)'),
        ('10',u'10 - SKDD'),
        ('11',u'11 - Poslodavac u stečaju u slučaju izravne isplate plaće koju Agencija za osiguranje radničkih potraživanja u slučaju stečaja poslodavaca isplaćuje radniku'),
        ('12',u'12 - Osiguranik po osnovi rada kod poslodavca s registriranim sjedištem ili mjestom poslovanja u drugoj državi članici Europske unije koji je od tog poslodavca preuzeo obvezu doprinosa'),
        ('13',u'13 - Poslodavac u slučaju kada druga osoba umjesto toga poslodavca isplaćuje plaću')
    ]

    joppd_applicant_id = fields.Selection(_applicant_code_sel, 'Oznaka podnositelja')
    joppd_create_name = fields.Char('Sastavio (ime)', size=128)
    joppd_create_surname = fields.Char('Sastavio (prezime)', size=128)
    # joppd_applicant_new_id': fields.many2one('joppd.code.register.applicant', 'Applicant Code', domain=[('type','=','normal')]),
    joppd_applicant_email = fields.Char('E-Mail podnositelja', size=64)
    joppd_oib = fields.Char('OIB podnositelja', size=11)
