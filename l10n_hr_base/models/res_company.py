from datetime import datetime

import pytz

from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

FISKAL_DATETIME_FORMAT = '%d.%m.%YT%H:%M:%S'
RACUN_DATETIME_FORMAT = '%d.%m.%Y %H:%M'


class Company(models.Model):
    _inherit = "res.company"

    # Technical field to hide country specific fields in company form view
    # from account module
    country_code = fields.Char(depends=['country_id'])

    l10n_hr_nkd = fields.Char(
        string="NKD Code",
        help="Main company activity classified by NKD-2007",
    )
    l10n_hr_mirovinsko = fields.Char(
        string="Pension Fund",
        help="Regstration Number for payments in pension fund",
    )
    l10n_hr_zdravstveno = fields.Char(
        string="Health Insurance",
        help="Registration number for payments to health insurance",
    )
    l10n_hr_maticni_broj = fields.Char(string="Registration Number")

    l10n_hr_responsible_fname = fields.Char(
        string='Ime', size=64, help='Ime odgovorne osobe')
    l10n_hr_responsible_lname = fields.Char(
        string='Prezime', size=64, help='Prezime odgovorne osobe')
    l10n_hr_responsible_tel = fields.Char(
        string='Telefon', size=64, help='Tel odgovorne osobe')
    l10n_hr_responsible_email = fields.Char(
        string='E-mail', size=64, help='E-mail odgovorne osobe')
    l10n_hr_responsible_vat = fields.Char(
        string='OIB', size=32, help='OIB odgovorne osobe')
    l10n_hr_podrucje_djelatnosti = fields.Selection(
        selection=[
            ('A', 'A-POLJOPRIVREDA, ŠUMARSTVO I RIBARSTVO'),
            ('B', 'B-RUDARSTVO I VAĐENJE'),
            ('C', 'C-PRERAĐIVAČKA INDUSTRIJA'),
            ('D', 'D-OPSKRBA ELEKTRIČNOM ENERGIJOM, PLINOM, PAROM I KLIMATIZACIJA'),
            ('E', 'E-OPSKRBA VODOM, UKLANJANJE OTPADNIH VODA, GOSPODARENJE OTPADOM TE DJELATNOSTI SANACIJE OKOLIŠA'),
            ('F', 'F-GRAĐEVINARSTVO'),
            ('G', 'G-TRGOVINA NA VELIKO I NA MALO; POPRAVAK MOTORNIH VOZILA I MOTOCIKALA'),
            ('H', 'H-PRIJEVOZ I SKLADIŠTENJE'),
            ('I', 'I-DJELATNOSTI PRUŽANJA SMJEŠTAJA TE PRIPREME I USLUŽIVANJA HRANE'),
            ('J', 'J-INFORMACIJE I KOMUNIKACIJE'),
            ('K', 'K-FINANCIJSKE DJELATNOSTI I DJELATNOSTI OSIGURANJA'),
            ('L', 'L-POSLOVANJE NEKRETNINAMA'),
            ('M', 'M-STRUČNE, ZNANSTVENE I TEHNIČKE DJELATNOSTI'),
            ('N', 'N-ADMINISTRATIVNE I POMOĆNE USLUŽNE DJELATNOSTI'),
            ('O', 'O-JAVNA UPRAVA I OBRANA; OBVEZNO SOCIJALNO OSIGURANJE'),
            ('P', 'P-OBRAZOVANJE'),
            ('Q', 'Q-DJELATNOSTI ZDRAVSTVENE ZAŠTITE I SOCIJALNE SKRBI'),
            ('R', 'R-UMJETNOST, ZABAVA I REKREACIJA'),
            ('S', 'S-OSTALE USLUŽNE DJELATNOSTI'),
            ('T', 'T-DJELATNOSTI KUĆANSTAVA KAO POSLODAVACA'),
            ('U', 'U-DJELATNOSTI IZVANTERITORIJALNIH ORGANIZACIJA I TIJELA'),
        ], string='Područje djelatnosti',
    )

    def get_l10n_hr_time_formatted(self):
        # odoo16 - date/time) fields are WITH TZ info! diff from previous versions!
        user_tz = self.env.user.tz or self.env.context.get("tz")
        user_pytz = pytz.timezone(user_tz) if user_tz else pytz.utc
        tstamp = datetime.now().astimezone(user_pytz)
        time_now = tstamp.replace(tzinfo=None)
        return {
            "datum": tstamp.strftime("%d.%m.%Y"),  # datum_regular SAD
            "datum_vrijeme": tstamp.strftime(
                FISKAL_DATETIME_FORMAT
            ),  # format za zaglavlje FISKAL XML poruke
            "datum_meta": tstamp.strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),  # format za metapodatke xml-a ( JOPPD...)
            "datum_racun": tstamp.strftime(
                RACUN_DATETIME_FORMAT
            ),  # format za ispis na računu
            "time_stamp": tstamp,  # timestamp, za zapis i izračun vremena obrade
            "odoo_datetime": time_now.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        }
