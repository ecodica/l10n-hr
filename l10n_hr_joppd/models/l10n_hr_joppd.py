# -*- coding: utf-8 -*-

import os
import base64
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import Warning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from . import joppd_help as jh
from . import joppd_schema_specific as jss
STATES = {'draft': [('readonly', False)]}


class L10nHrJOPPD(models.Model):
    _name = 'l10n.hr.joppd'
    _inherit = ['l10n.hr.xml.mixin']
    _description = 'JOPPD Obrazac'
    _order = 'date_joppd desc'

    def _get_schema(self):
        if self.xml_schema == '1.0':
            schema = jss.JoppdSchemaV10()
        elif self.xml_schema == '1.1':
            schema = jss.JoppdSchemaV11()
        else:
            schema = None
        return schema

    def _select_default_schema(self):
        date = datetime.now()
        v10 = datetime.strptime('2015-01-01', DEFAULT_SERVER_DATE_FORMAT)
        v11 = datetime.strptime('2015-02-28', DEFAULT_SERVER_DATE_FORMAT)
        if date < v10:
            raise
        elif v10 < date < v11:
            return '1.0'
        elif v11 < date:
            return '1.1'

    def _get_joppd_oznaka(self):
        return ''.join((datetime.strftime(datetime.now(), '%y'),
                        datetime.strftime(datetime.now(), '%j')))

    def _get_oznaka_selection(self):
        if self.xml_schema:
            schema = self._get_schema()
        else:
            schema = jss.JoppdSchemaV11()
        return schema.oznaka_selection()

    def _get_name_draft(self):
        res = self._get_joppd_oznaka()
        return res + ' (priprema)'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    name = fields.Char(
        string='Naziv', size=64,
        required=True, copy=False, readonly=True,
        states=STATES,
        index=True, default=_get_name_draft)
    oznaka = fields.Char(
        string='I. Oznaka izvješća', size=5,
        required=True, readonly=True,
        states=STATES,
        default=_get_joppd_oznaka,
        help=jh.oznaka_help)
    state = fields.Selection(
        selection=[
            ('draft', 'Nacrt'),
            ('finished', 'Spreman'),
            ('sent', 'Poslan u PU'),
            ('accepted', 'Prihvaćen u PU')],
        string='Status',
        required=True, readonly=True, default='draft')
    date_joppd = fields.Date(
        string='Datum',
        required=True, readonly=True,
        states=STATES,
        default=fields.Date.today())
    period_joppd = fields.Many2one(
        comodel_name='date.range', string="Razdoblje", readonly=True,
        states=STATES,
        required=True, help="Razdoblje prijave obrazca")
    period_date_from_joppd = fields.Date(
        string='Datum razdoblja od',
        required=True, readonly=True,
        states=STATES)
    period_date_to_joppd = fields.Date(
        string='Datum razdoblja do',
        required=True, readonly=True,
        states=STATES)
    parent_id = fields.Many2one(
        comodel_name='l10n.hr.joppd',
        string='Izvorno izvješće')
    child_ids = fields.One2many(
        comodel_name='l10n.hr.joppd',
        inverse_name='parent_id',
        string='Povezani JOPPD obrasci')
    vrsta = fields.Selection(
        selection=[
            ('1', '1 - Izvorno izvješće'),
            ('2', '2 - Ispravak izvješća'),
            ('3', '3 - Dopuna izvješća'),
            ('4', '4 - Izvorno'),
            ('5', '5 - Izvorno'),
            ('6', '6 - Korektivno za 5'),
            ('7', '7 - Nadopuna za 5'),
            ('8', '8 - Izvorno'),
            ('9', '9 - Korektivno za 8'),
            ('10', '10- Nadopuna za 8')],
        string='II. Vrsta izvještaja', required=True, readonly=True,
        states=STATES,
        default='1', help=jh.vrsta_help)

    podnositelj_naziv = fields.Char(
        string="III.1 Naziv/ime i prezime",
        required=True, readonly=True,
        states=STATES)
    podnositelj_mjesto = fields.Char(
        string="Mjesto",
        required=True, readonly=True,
        states=STATES)
    podnositelj_ulica = fields.Char(
        string="Ulica",
        required=True, readonly=True,
        states=STATES)
    podnositelj_kbr = fields.Char(
        string="kbr",
        required=True, readonly=True,
        states=STATES)
    podnositelj_email = fields.Char(
        string="III.3 Adresa e-pošte",
        required=True, readonly=True,
        states=STATES)
    podnositelj_oib = fields.Char(
        string="III.4 OIB",
        required=True, readonly=True,
        states=STATES)
    podnositelj_oznaka = fields.Selection(
        selection=_get_oznaka_selection, default="1",
        string="III.5 Oznaka podnositelja",
        required=True, readonly=True,
        states=STATES,
        help="Oznake iz priloga 1 upute o popunjavanju JOPPD obrasca")

    note = fields.Text(string='Napomena')
    identifier = fields.Char(string='UUID Identifikator', size=64)

    broj_osoba = fields.Integer(
        string="IV.1 Broj osoba",
        copy=False, readonly=True,
        states=STATES)
    broj_redaka = fields.Integer(
        string="IV.2 Broj redaka",
        copy=False, readonly=True,
        states=STATES)

    sastavio_id = fields.Many2one(
        comodel_name='res.partner',
        string="Sastavio",
        # domain="[('fiskal_responsible','=',True)]"
    )

    sast_ime = fields.Char(
        string="Ime", readonly=True, required=True,
        states=STATES)
    sast_prez = fields.Char(
        string="Prezime", readonly=True, required=True,
        states=STATES)

    xml_schema = fields.Selection(
        selection=[
            ('1.0', 'v1.0 - od 1.1.2015'),
            ('1.1', 'v1.1 - od 28.2.2015')],
        string="Verzija sheme",
        required=True, readonly=True,
        states=STATES,
        default=_select_default_schema)
    xml_file = fields.Binary(string='XML File', readonly=True)
    xml_file_name = fields.Char(string='XML File Name', size=128, readonly=True)

    sideA_ids = fields.One2many(
        comodel_name='l10n.hr.joppd.a',
        inverse_name='joppd_id',
        string='Strana A', readonly=True,
        states=STATES)
    sideB_ids = fields.One2many(
        comodel_name='l10n.hr.joppd.b',
        inverse_name='joppd_id',
        string='Strana B', readonly=True,
        states=STATES)

    @api.onchange('xml_schema')
    def _onchange_xml_schema(self):
        schema = self._get_schema()
        stavke = schema.stavke_strana_A()
        stavke_a = [(0, 0, {'code': x[0], 'position': x[1]}) for x in stavke]
        if not self.sideA_ids:
            self.sideA_ids = stavke_a
        else:
            # DB: damn.. moram prvo brisati pa tek onda upisati... o2m ne radi sa (6,0, {})
            self.sideA_ids = [(2, x.id) for x in self.sideA_ids]
            self.sideA_ids = stavke_a

    @api.onchange('podnositelj_oznaka')
    def _onchange_oznaka_podnositelj(self):
        if self.podnositelj_oznaka == '1':
            addr, num = "", ""
            full_addr = self.company_id.partner_id.street
            if full_addr:
                part_addr = full_addr.split(" ")
                num = part_addr[len(part_addr) - 1]
                for index in range(len(part_addr) - 1):
                    addr += part_addr[index] + " "
                if len(addr) > 0:
                    addr = addr[:-1]
            self.podnositelj_naziv = self.company_id.partner_id.name
            self.podnositelj_mjesto = self.company_id.partner_id.city
            self.podnositelj_ulica = addr
            self.podnositelj_kbr = num
            self.podnositelj_email = self.company_id.l10n_hr_responsible_email
            try:
                self.podnositelj_oib = self.company_id.partner_id.get_oib_from_vat()
            except:
                oib = self.company_id.partner_id.vat
                if not oib:
                    raise ValidationError(_('Molimo unesite OIB vaše tvrtke!'))
                oib = oib.startswith('HR') and oib[2:] or oib
                self.podnositelj_oib = oib
        elif self.podnositelj_oznaka in ('6', '7', '8', '9'):
            raise ValidationError('Navedenu oznaku niste ovlašteni koristiti!')

    @api.onchange('date_joppd')
    def _onchange_date_joppd(self):
        related_date_range_id = self.env['date.range'].search([('date_end', '>=', self.date_joppd),
                                                               ('date_start', '<=', self.date_joppd)], limit=1)
        if related_date_range_id:
            previous_date_range_id = self.env['date.range'].search(
                [('date_end', '<=', related_date_range_id.date_start)],
                limit=1, order='date_end DESC')
            self.period_joppd = previous_date_range_id.id or None

    @api.onchange('period_joppd')
    def _onchange_period_joppd(self):
        if self.period_joppd:
            self.period_date_from_joppd = self.period_joppd.date_start
            self.period_date_to_joppd = self.period_joppd.date_end
        else:
            self.period_date_from_joppd = False
            self.period_date_to_joppd = False

    def _numeriraj_sql(self):
        sql = {
            'select': [
                ('row_number() over (order by b.b5) as rbr', 0),
                (', b.id as id', 5)
            ],
            'from': [('l10n_hr_joppd_b b', 0)],
            'where': [('joppd_id = %(jop_id)s', 0)]
        }
        return sql

    def numeriraj_strana_B(self):
        if self.vrsta in ('1', '5', '8'):
            self.env.cr.execute("""
            SELECT row_number() over (order by b.b5) as rbr,
                   b.id as id
            FROM l10n_hr_joppd_b b
            WHERE joppd_id = %(jop_id)s
            """, {'jop_id': self.id})
            rows = self.env.cr.dictfetchall()
            # rows = self.execute_sql(
            #     sql=self.make_sql(self._numeriraj_sql()),
            #     pref='dict', vals={'jop_id': self.id})
            redni_b = [(1, r['id'], {'b1': r['rbr']}) for r in rows]
            self.sideB_ids = redni_b
        else:
            # TODO ostalo... dopuna, ispravak...
            pass
        return True

    def _count_strana_b(self):
        self.numeriraj_strana_B()
        self._cr.execute("""
            SELECT
                count(distinct(b4)) as broj_osoba,
                count(id) as broj_redaka
            FROM l10n_hr_joppd_b where joppd_id = %(joppd_id)s
            """ % {'joppd_id': self.id})
        res = self._cr.dictfetchone()
        self.broj_osoba = res['broj_osoba']
        self.broj_redaka = res['broj_redaka']

    def button_summarize_sideA(self):
        if not self.sideB_ids:
            raise ValidationError('Nema podataka na strani B, zbrajanje nije moguće!')
        sum_sql = self._get_schema().sql_sum_B_to_A()
        self._cr.execute(sum_sql % {'joppd_id': self.id})
        res = self._cr.dictfetchone()
        for line in self.sideA_ids:
            kcode = line.code.replace('.', '_').lower()
            if kcode in res.keys():
                line.value = res[kcode]
        return self._count_strana_b()

    def button_done_editing(self):
        if self.vrsta != '4' and not self.sideB_ids:
            # DB : samo vrsta 4 se predaje bez redaka na strani B!
            raise ValidationError('Nije moguće završiti bez redaka na strani B!')
        if self.date_joppd != fields.Date.today():
            # DB : nisam bas 100% siguran da ce ovjek ovkao... ali zassada nek bude
            self.date_joppd = fields.Date.today()
            self.code = self._get_joppd_oznaka()
        self.name = '_'.join(('JOPPD',
                              self.podnositelj_oznaka,
                              self.podnositelj_oib,
                              self.vrsta,
                              self.oznaka,
                              self.company_id.\
                                  get_l10n_hr_time_formatted()['datum_vrijeme'].\
                                      replace('T', '_')))
        self.state = 'finished'

    def button_set_draft(self):
        """
        Button : 'invisible':[('state','in',('draft','accepted'))]
        so no need for control
        :return:
        """
        self.state = 'draft'
        self.xml_file = False
        self.xml_file_name = False

    def button_generate_xml(self):
        schema = self._get_schema()
        metadata, identifier = self.get_xml_metadata(
                                    xml_naslov=schema.xml_naslov(),
                                    xml_autor=' '.join((self.sast_ime, self.sast_prez)),
                                    xml_conforms=schema.xml_conforms_to())
        # Strana B
        self._cr.execute(schema.xmldata_strana_B() % self.id)
        sideB_data = self._cr.dictfetchall()
        EM = self._get_elementmaker()
        Primatelji = []
        for b in sideB_data:
            Primatelji.append(schema.xml_generate_primatelj(EM, b))
        StranaB = EM.StranaB(EM.Primatelji(EM.P))
        StranaB.Primatelji.P = Primatelji

        #Strana A
        self._cr.execute("""
                SELECT code, value
                FROM l10n_hr_joppd_a
                WHERE joppd_id = %s
                """ % self.id)
        sideA_data = self._cr.fetchall()
        sideA_data = sideA_data and dict(sideA_data) or {}
        sideA_data.update({
            'datum_izvjesca': self.date_joppd,
            'oznaka_izvjesca': self.oznaka,
            'vrsta_izvjesca': self.vrsta,
            'podnositelj_oznaka': self.podnositelj_oznaka,
            'podnositelj_naziv': self.podnositelj_naziv,
            'podnositelj_mjesto': self.podnositelj_mjesto,
            'podnositelj_ulica': self.podnositelj_ulica,
            'podnositelj_kbr': self.podnositelj_kbr,
            'podnositelj_email': self.podnositelj_email,
            'podnositelj_oib': self.podnositelj_oib,
            'oznaka': self.oznaka,
            'broj_osoba': self.broj_osoba,
            'broj_redaka': self.broj_redaka,
            'sast_ime': self.sast_ime,
            'sast_prezime': self.sast_prez,
        })
        StranaA = schema.xml_strana_A(EM, sideA_data)
        JOPPD = self._get_elementmaker(namespace=schema.xml_namespace())

        joppd = JOPPD.ObrazacJOPPD(metadata, StranaA, StranaB, verzijaSheme=self.xml_schema)

        #TODO: config: bool pretty print for xml?
        xml_string = self.get_xml_string(joppd, deannotate=True, pretty=True,
                        replace=[('ns0:', ''), (':ns0', ''), ('xmlns="False"', '')])

        my_path = os.path.dirname(os.path.abspath(__file__))
        module_path = os.path.split(my_path)[0]
        schema_dir = 'schema_' + self.xml_schema
        schema_file ='ObrazacJOPPD-v' + self.xml_schema.replace('.', '-') + '.xsd'

        xml_error = self.validate_xml(xml_string=xml_string,
                                      xsd_path=os.path.join(module_path, schema_dir),
                                      xsd_file=schema_file)
        if xml_error:
            raise ValidationError(xml_error)

        self.identifier = identifier
        self.xml_file_name = self.name + '.xml'
        self.xml_file = base64.encodestring(xml_string.encode('utf-8'))
        self.state = 'sent' # označi za slanje!

    def button_delete_sideB_rows(self):
        self.sideB_ids = [(2, x.id) for x in self.sideB_ids]

    def button_accepted_xml(self):
        self.state = 'accepted'

    def button_correction(self):
        # TODO
        return

    def button_addition(self):
        # TODO
        return

    def export_xls(self):
        self.ensure_one()
        return (
            self.env.ref("l10n_hr_joppd.joppd_obrazac_xlsx")
            .report_action(self, data=dict(dummy=True))  # required to propagate context
        )


class L10nHrJOPPD_A(models.Model):
    _name = 'l10n.hr.joppd.a'
    _description = 'Strana A JOPPD obrasca'

    joppd_id = fields.Many2one(
        comodel_name='l10n.hr.joppd',
        string='JOPPD obrazac',
        ondelete="cascade")
    code = fields.Char(
        string="Pozicija",
        required=True)
    position = fields.Char(
        string="Opis pozicije",
        required=True)
    value = fields.Float(
        string='Iznos', copy=False)  # TODO: define decimal precision


class L10nHrJOPPD_B(models.Model):
    _name = 'l10n.hr.joppd.b'
    _description = 'Strana B JOPPD obrasca'
    _order = 'b1'

    joppd_id = fields.Many2one(
        comodel_name='l10n.hr.joppd',
        string='JOPPD obrazac', ondelete='cascade')
    original_line_id = fields.Many2one(
        comodel_name='l10n.hr.joppd.b',
        string='Izvorni redak')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        relate='joppd_id.company_id.currency_id',
        string="Valuta poduzeća")
    b1 = fields.Integer(
        string='1. Redni broj', readonly=True)
    b2 = fields.Char(
        string='2. Šifra općine/grada prebivališta/boravišta',
        size=5, required=True)
    b3 = fields.Char(
        string='3. Šifra općine/grada rada',
        size=5, required=True)
    b4 = fields.Char(
        string='4. OIB stjecatelja/osiguranika',
        size=11, required=True)
    b5 = fields.Char(
        string='5. Ime i prezime stjecatelja/osiguranika',
        size=128, required=True)
    b61 = fields.Char(
        string='6.1. Oznaka stjecatelja/osiguranika',
        size=6, required=True, ) # default='0001'
    b62 = fields.Char(
        string='6.2. Oznaka primitka/obveze doprinosa',
        size=6, required=True, ) # default='0001'
    b71 = fields.Selection(
        selection=[
            ('0', '0 - Nema dodatnog doprinosa'),
            ('1', '1 - Obveza za 12=14 mjes.'),
            ('2', '2 - Obveza za 12=15 mjes.'),
            ('3', '3 - Obveza za 12=16 mjes.'),
            ('4', '4 - Obveza za 12=18 mjes.')],
        string='7.1. Dodatni doprinosi MO',
        help=jh.b71_help, default='0')
    b72 = fields.Selection(
        selection=[
            ('0', '0 - Nije obveznik'),
            ('1', '1 - Stopa 0,1%'),
            ('2', '2 - Stopa 0,2%')],
        string='7.2. Doprinos za zap. inv. osoba',
        help=jh.b72_help, default='0')
    b8 = fields.Selection(
        selection=[
            ('0', '0 - Nema prethodne obveze'),
            ('1', '1 - Prvi mjesec po osnovi'),
            ('2', '2 - Zadnji mjesec po osnovi'),
            ('3', '3 - Mjeseci unutar perioda osnove'),
            ('4', '4 - Početak i kraj u istom mjesecu'),
            ('5', '5 - Obveza nastala nakon perioda')],
        string='8. Oznaka mjeseca osiguranja',
        help=jh.b8_help, default='0')
    b9 = fields.Selection(
        selection=[
            ('0', '0 - Bez radnog vremena'),
            ('1', '1 - Puno radno vrijeme'),
            ('2', '2 - Nepuno radno vrijeme'),
            ('3', '3 - Pola rad.vr.-njega djeteta')],
        string='9. Oznaka radnog vremena',
        help=jh.b9_help, default='0')
    b10 = fields.Integer(
        string='10. Broj sati rada', help=jh.b10_help)
    b100 = fields.Integer(
        string='10.0. Broj neodrađenih sati', help=jh.b10_help)

    b101 = fields.Date(
        string='10.1. Razdoblje OD',
        required=True, help=jh.b_101_102_help)
    b102 = fields.Date(
        string='10.2. Razdoblje DO',
        required=True, help=jh.b_101_102_help)
    b11 = fields.Monetary(
        string='11. Iznos primitka (oporezivi)',
        currency_field='currency_id')
    b12 = fields.Monetary(
        string='12. Osnovica za doprinose',
        currency_field='currency_id', help=jh.b12_help)
    b121 = fields.Monetary(
        string='12.1. Doprinos za mirovinsko osiguranje',
        currency_field='currency_id', help=jh.b121_help)
    b122 = fields.Monetary(
        string='12.2. Dopr. za mir. osig. II Stup',
        currency_field='currency_id')
    b123 = fields.Monetary(
        string='12.3. Zdravstveno osig.',
        currency_field='currency_id')
    b124 = fields.Monetary(
        string='12.4. Doprinos za zašt.zdravlja na radu',
        currency_field='currency_id')
    b125 = fields.Monetary(
        string='12.5. Doprinosi za zapošljavanje',
        currency_field='currency_id')
    b126 = fields.Monetary(
        string='12.6. Dodatni dop. za mir. osig. - staž pov. traj.',
        currency_field='currency_id')
    b127 = fields.Monetary(
        string='12.7. Dod.dop. za mir. osig.- staž pov. traj. II STUP',
        currency_field='currency_id')
    b128 = fields.Monetary(
        string='12.8. Poseban dop. - zdrav.zašt.ino.',
        currency_field='currency_id')
    b129 = fields.Monetary(
        string='12.9. Poseban dop. za zap.osoba s inv.',
        currency_field='currency_id')
    b131 = fields.Monetary(
        string='13.1. Izdatak',
        currency_field='currency_id')
    b132 = fields.Monetary(
        string='13.2. Izdatak -upla.dop. mir.osig',
        currency_field='currency_id')
    b133 = fields.Monetary(
        string='13.3. Dohodak',
        currency_field='currency_id')
    b134 = fields.Monetary(
        string='13.4. Osobni odbitak',
        currency_field='currency_id')
    b135 = fields.Monetary(
        string='13.5. Porezna osnovica',
        currency_field='currency_id')
    b141 = fields.Monetary(
        string='14.1. Izn.obr. poreza na dohodak',
        currency_field='currency_id')
    b142 = fields.Monetary(
        string='14.2. Izn.obr. prireza por.na doh.',
        currency_field='currency_id')
    b151 = fields.Char(
        string='15.1. Oznaka neopor. primitka',
        size=5, required=True, )  # default='0'
    b152 = fields.Monetary(
        string='15.2. Iznos neopor. primitka',
        currency_field='currency_id')
    b161 = fields.Char(
        string='16.1. Oznaka načina isplate',
        size=5, required=True, )  # default='0'
    b162 = fields.Monetary(
        string='16.2. Iznos za isplatu',
        currency_field='currency_id')
    b17 = fields.Monetary(
        string='17. Obračun. prim. od nesam. rada (plaća)',
        currency_field='currency_id')
