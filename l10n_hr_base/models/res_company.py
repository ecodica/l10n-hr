from datetime import datetime
import pytz

from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

FISCAL_DATETIME_FORMAT = '%d.%m.%YT%H:%M:%S'
# DatVrijeme is signed into the ZKI and printed on the receipt, so the timestamp
# belongs to the business premise and must not shift with the logged-in user's tz.
FISCAL_TIMEZONE = 'Europe/Zagreb'
INVOICE_DATETIME_FORMAT = '%d.%m.%Y %H:%M'


class ResCompany(models.Model):
    _inherit = "res.company"

    # Technical field to hide country specific fields in company form view
    # from account module
    # same as in base country_code = fields.Char(depends=['country_id'])
    l10n_hr_nkd_code = fields.Char(
        string="NKD Code",
        help="Main company activity classified by NKD-2007.")
    l10n_hr_pension_fund = fields.Char(
        string="Pension Fund",
        help="Registration number for payments in pension fund.")
    l10n_hr_health_insurance = fields.Char(
        string="Health Insurance",
        help="Registration number for payments to health insurance.")
    l10n_hr_registration_number = fields.Char(string="Registration Number")
    l10n_hr_responsible_fname = fields.Char(
        string='Responsible Person First Name', size=64, 
        help='Responsible person first name.')
    l10n_hr_responsible_lname = fields.Char(
        string='Responsible Person Last Name', size=64, 
        help='Responsible person last name.')
    l10n_hr_responsible_tel = fields.Char(
        string='Responsible Person Phone Number', size=64, 
        help='Responsible person phone number.')
    l10n_hr_responsible_email = fields.Char(
        string='Responsible Person E-mail', size=64, 
        help='Responsible person e-mail.')
    l10n_hr_responsible_vat = fields.Char(
        string='Responsible Person OIB Number', size=32, 
        help='Responsible person OIB number.')
    l10n_hr_activity_classification = fields.Selection(
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
        ], 
        string='Activity classification')

    def get_l10n_hr_time_formatted(self):
        # odoo16 - date/time) fields are WITH TZ info! diff from previous versions!
        # Was self.env.tz, which made DatVrijeme - and the ZKI signed over it -
        # depend on who was logged in. See FISCAL_TIMEZONE above.
        tstamp = datetime.now().astimezone(pytz.timezone(FISCAL_TIMEZONE))
        time_now = tstamp.replace(tzinfo=None)
        return {
            "datum": tstamp.strftime("%d.%m.%Y"),
            "datum_vrijeme": tstamp.strftime(
                FISCAL_DATETIME_FORMAT),
            "datum_meta": tstamp.strftime(
                "%Y-%m-%dT%H:%M:%S"),
            "datum_racun": tstamp.strftime(
                INVOICE_DATETIME_FORMAT),
            "time_stamp": tstamp,
            "odoo_datetime": time_now.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        }
