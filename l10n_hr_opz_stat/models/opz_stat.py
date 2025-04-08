from odoo import models, fields, api, _
from lxml import objectify
import os
import base64
from . import xml_common as rc
from odoo.modules.module import get_resource_path


class OpzStat(models.Model):
    _name = "opz.stat"
    _description = "OPZ STAT report"

    date_from = fields.Date("Date From", required=True)
    date_to = fields.Date("Date To", required=True)
    date_open = fields.Date("Date Open", required=True)
    name = fields.Char("Name", required=True, default="/")
    opz_stat_line = fields.One2many(
        "opz.stat.line",
        "opz_id",
        string="OPZ STAT Lines",
        readonly=True,
        states={"draft": [("readonly", False)]},
        copy=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        change_default=True,
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: self.env["res.company"]._company_default_get("opz.stat")
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
        ],
        "State",
        required=True,
        index=True,
        readonly=True,
        default="draft",
    )
    xml_file = fields.Binary("XML File", readonly=True)
    xml_filename = fields.Char("XML File Name", readonly=True)
    skip_xml_validation = fields.Boolean("Skip XML validation", default=False)
    skip_negative_amount = fields.Boolean("Skip Negative Amount", default=False)
    sum_others = fields.Boolean("Sum Others", default=False)
    partner_ids = fields.Many2many('res.partner',
                                   'opz_stat_res_partner_rel',
                                   'opz_stat_id', 'partner_id',
                                   string='Partners',
                                   readonly=True,
                                   states={"draft": [("readonly", False)]},
                                   copy=False,
                                   )
    journal_ids = fields.Many2many('account.journal',
                                   'opz_stat_account_journal_rel',
                                   'opz_stat_id', 'journal_id',
                                   string='Journals',
                                   readonly=True,
                                   states={"draft": [("readonly", False)]},
                                   copy=False,
                                   )

    def _auto_init(self):
        res = super(OpzStat, self)._auto_init()
        f = get_resource_path("l10n_hr_opz_stat", "sql", "oe_opz_stat.sql")
        sql = open(f).read()
        self.env.cr.execute(sql)
        return res

    def compute(self):
        # Remove lines first
        self.opz_stat_line.unlink()
        sql = """
             SELECT DISTINCT 1
             FROM oe_opz_stat(
                     _date_to      := '%(date_to)s'
                    ,_date_open    := '%(date_open)s'
                    ,_opz_id    := %(opz_id)s
                    ,_company_id := %(company_id)s
                         )
           """ % {
            "date_to": self.date_to,
            "date_open": self.date_open,
            "opz_id": self.id,
            "company_id": self.company_id.id,
        }
        self.env.cr.execute(sql)
        self.invalidate_recordset()
        if self.skip_negative_amount:
            self.opz_stat_line.filtered(lambda l: l.unpaid < 0.0).unlink()
        return True

    def set_to_confirmed(self):
        self.ensure_one()
        self.state = "confirmed"

    def set_to_draft(self):
        self.ensure_one()
        self.state = "draft"

    @api.onchange('date_to')
    def _onchange_date_to(self):
        if self.date_to:
            self.date_open = self.date_to

    def print_report(self):
        pass

    def view_lines(self):
        return {
            'name': _('OPZ-STAT lines'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'opz.stat.line',
            'target': 'current',
            'domain': [('opz_id', '=', self.id)],
            'context': self.env.context,
        }

    def export_xml(self):
        self.ensure_one()
        kupac_line_no = 0
        period = {"date_start": self.date_from, "date_stop": self.date_to}
        Tijelo = objectify.Element("Tijelo")
        Kupci = objectify.SubElement(Tijelo, "Kupci")

        UkupanIznosRacunaObrasca = 0.0
        UkupanIznosPdvObrasca = 0.0
        UkupanIznosRacunaSPdvObrasca = 0.0
        UkupniPlaceniIznosRacunaObrasca = 0.0
        NeplaceniIznosRacunaObrasca = 0.0
        OPZUkupanIznosRacunaSPdv = 0.0
        OPZUkupanIznosPdv = 0.0

        if self.sum_others:
            amounts = self._calc_other_partner_amounts()
            OPZUkupanIznosRacunaSPdv = amounts.get("amount_total")
            OPZUkupanIznosPdv = amounts.get("amount_tax")

        partners = self._get_partners()
        for partner in partners:
            kupac_line_no += 1
            lines = self._get_partner_lines(partner["partner_id"])
            Kupac = objectify.SubElement(Kupci, "Kupac")
            Kupac.K1 = kupac_line_no  # Redni broj
            Kupac.K2 = partner["partner_vat_type"]  # Oznaka poreznog broja 1=OIB, 2=PDV ID, 3=ostali porezni brojevi
            Kupac.K3 = partner["partner_vat_number"]  # porezni broj ovisno o vrijednosti K2
            Kupac.K4 = partner["partner_name"][:128]  # Naziv kupca
            Kupac.K5 = partner["partner_amount"]  # Iznos računa ukupno
            Kupac.K6 = partner["partner_amount_tax"]  # Iznos PDV ukupno
            Kupac.K7 = partner["partner_amount_total"]  # Iznos računa s PDV ukupno
            Kupac.K8 = partner["partner_paid"]  # Plaćeni iznos ukupno
            Kupac.K9 = partner["partner_unpaid"]  # Neplaćeni iznos ukupno

            Racuni = objectify.SubElement(Kupac, "Racuni")
            line_no = 1
            for line in lines:
                Racun = objectify.SubElement(Racuni, "Racun")
                Racun.R1 = line_no  # Redni broj
                Racun.R2 = line["invoice_number"]  # Broj (naziv) računa
                Racun.R3 = line["invoice_date"]  # Datum računa
                Racun.R4 = line["due_date"]  # Datum dospjeća
                Racun.R5 = line["overdue_days"]  # broj dana kašnjenja
                Racun.R6 = line["amount"]  # iznos računa bez PDV-a
                Racun.R7 = line["amount_tax"]  # iznos PDV-a
                Racun.R8 = line["amount_total"]  # iznos računa s PDV-om
                Racun.R9 = line["paid"]  # plaćeni iznos
                Racun.R10 = line["unpaid"]  # otvoreni iznos
                line_no += 1
                UkupanIznosRacunaObrasca += line["amount"]
                UkupanIznosPdvObrasca += line["amount_tax"]
                UkupanIznosRacunaSPdvObrasca += line["amount_total"]
                UkupniPlaceniIznosRacunaObrasca += line["paid"]
                NeplaceniIznosRacunaObrasca += line["unpaid"]

        Tijelo.UkupanIznosRacunaObrasca = round(UkupanIznosRacunaObrasca, 2)
        Tijelo.UkupanIznosPdvObrasca = round(UkupanIznosPdvObrasca, 2)
        Tijelo.UkupanIznosRacunaSPdvObrasca = round(UkupanIznosRacunaSPdvObrasca, 2)
        Tijelo.UkupniPlaceniIznosRacunaObrasca = round(UkupniPlaceniIznosRacunaObrasca, 2)
        Tijelo.NeplaceniIznosRacunaObrasca = round(NeplaceniIznosRacunaObrasca, 2)
        Tijelo.OPZUkupanIznosRacunaSPdv = OPZUkupanIznosRacunaSPdv
        Tijelo.OPZUkupanIznosPdv = OPZUkupanIznosPdv
        tijelo = Tijelo

        author, company, metadata = rc.get_common_data(self, self)

        metadata["naslov"] = u"Obrazac OPZ"
        metadata["uskladjenost"] = u"ObrazacOPZ-v1-0"

        xml_metadata, uuid = rc.create_xml_metadata(self, metadata)
        xml_header = rc.create_xml_header(self, period, company, author)

        OBRAZACOPZ = objectify.ElementMaker(
            annotate=False,
            namespace="http://e-porezna.porezna-uprava.hr/sheme/zahtjevi/ObrazacOPZ/v1-0",
        )
        obrazacopz_stat = OBRAZACOPZ.ObrazacOPZ(xml_metadata, xml_header, tijelo, verzijaSheme="1.0")
        xml = {"xml": rc.etree_tostring(self, obrazacopz_stat), "xsd_path": "schema/opz_stat_xml_v1.0",
               "xsd_name": "ObrazacOPZ-v1-0.xsd", "path": os.path.dirname(os.path.abspath(__file__))}
        if not self.skip_xml_validation:
            rc.validate_xml(self, xml)
        filename = "OPZ_STAT_%s.xml" % fields.Date.to_string(fields.Date.today())
        opz_xml = b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml["xml"]
        data64 = base64.b64encode(opz_xml)
        self.write({"xml_file": data64, "xml_filename": filename, "state": 'done'})
        return True

    def _get_partners(self):
        allowed_vat_types = ['vat', 'vat_id']
        if not self.sum_others:
            allowed_vat_types += ['other']
        sql = """
            SELECT 
                DISTINCT opzl.partner_id
                ,CASE WHEN opzl.partner_vat_type = 'vat' THEN 1
                      WHEN opzl.partner_vat_type = 'vat_id' THEN 2
                      WHEN opzl.partner_vat_type = 'other' THEN 3
                END AS partner_vat_type
                ,opzl.partner_vat_number
                ,opzl.partner_name
                ,SUM(opzl.amount) AS partner_amount
                ,SUM(opzl.amount_tax) AS partner_amount_tax
                ,SUM(opzl.amount_total) AS partner_amount_total
                ,SUM(opzl.paid) AS partner_paid
                ,SUM(opzl.unpaid) AS partner_unpaid
             FROM opz_stat_line opzl
            WHERE opzl.opz_id = %s AND opzl.partner_vat_type IN %s
           GROUP BY opzl.partner_id, opzl.partner_vat_type, opzl.partner_vat_number, opzl.partner_name
          """
        self.env.cr.execute(sql, (self.id, tuple(allowed_vat_types)))
        partners = self.env.cr.dictfetchall()
        return partners

    def _calc_other_partner_amounts(self):
        allowed_vat_types = ['other']
        sql = """
                SELECT 
                    SUM(opzl.amount_total) AS amount_total
                    ,SUM(opzl.amount) AS amount
                    ,SUM(opzl.amount_tax) AS amount_tax
                    ,SUM(opzl.paid) AS amount_paid
                    ,SUM(opzl.unpaid) AS amount_unpaid
                 FROM opz_stat_line opzl
                WHERE opzl.opz_id = %s AND opzl.partner_vat_type IN %s
              """
        self.env.cr.execute(sql, (self.id, tuple(allowed_vat_types)))
        totals = self.env.cr.dictfetchone()
        return totals

    def _get_partner_lines(self, partner_id):
        sql = """
                SELECT opzl.invoice_number
                      ,opzl.invoice_date
                      ,opzl.due_date
                      ,opzl.overdue_days
                      ,opzl.amount
                      ,opzl.amount_tax
                      ,opzl.amount_total
                      ,opzl.paid
                      ,opzl.unpaid
                FROM opz_stat_line opzl
                WHERE opzl.opz_id = %s AND opzl.partner_id = %s
              """
        self.env.cr.execute(sql, (self.id, partner_id))
        lines = self.env.cr.dictfetchall()
        return lines
