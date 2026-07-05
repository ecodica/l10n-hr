from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..fiscal import fiscal


class L10nHrFiscalWorkingTime(models.Model):
    _name = "l10n_hr.fiscal.working.time"
    _description = "Fiscal working time registration"
    _order = "create_date desc"
    _rec_name = "business_premise_id"

    business_premise_id = fields.Many2one(
        comodel_name="l10n_hr.business.premise",
        string="Business Premise",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="business_premise_id.company_id",
        store=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
        tracking=1,
    )
    action_type = fields.Selection(
        selection=[
            ("prijavi", "Register"),
            ("obrisi", "Delete"),
        ],
        default="prijavi",
        required=True,
    )
    # Redovno fields (used when action_type == prijavi)
    date_from = fields.Date(string="Date From", help="DatumOd")
    date_to = fields.Date(string="Date To", help="DatumDo (optional)")
    note = fields.Char(string="Note", size=200, help="Napomena")
    redovno_type = fields.Selection(
        selection=[
            ("po_dogovoru", "By appointment"),
            ("jednokratno", "Single shift"),
            ("dvokratno", "Double shift"),
            ("parni_neparni", "Even/odd day"),
        ],
        string="Regular Schedule Type",
        default="jednokratno",
    )
    redovno_line_ids = fields.One2many(
        comodel_name="l10n_hr.fiscal.working.time.line",
        inverse_name="working_time_id",
        string="Regular Schedule Lines",
    )
    # Iznimke fields
    iznimka_ids = fields.One2many(
        comodel_name="l10n_hr.fiscal.working.time.iznimka",
        inverse_name="working_time_id",
        string="Exceptions",
    )
    # Brisanje fields (used when action_type == obrisi)
    brisanje_redovno_date_ids = fields.One2many(
        comodel_name="l10n_hr.fiscal.working.time.brisanje",
        inverse_name="working_time_id",
        string="Delete Regular Schedule",
    )
    brisanje_iznimka_date_ids = fields.Char(
        string="Delete Exception Dates",
        help="Comma-separated dates (DD.MM.YYYY) for exception deletions.",
    )
    l10n_hr_fiscal_log_ids = fields.One2many(
        comodel_name="l10n_hr.fiscal.log",
        inverse_name="res_id",
        domain=lambda self: [("res_model", "=", "l10n_hr.fiscal.working.time")],
        string="Fiscal Logs",
        readonly=True,
    )

    def _build_redovno(self, fisk):
        """Build a RedovnoType zeep object from line records."""
        tf = fisk.type_factory
        lines = []
        for line in self.redovno_line_ids:
            kwargs = {"DatumOd": line.date_from.strftime("%d.%m.%Y")}
            if line.date_to:
                kwargs["DatumDo"] = line.date_to.strftime("%d.%m.%Y")
            if self.note:
                kwargs["Napomena"] = self.note
            if self.redovno_type == "po_dogovoru":
                kwargs["PoDogovoru"] = tf.PoDogovoruType(RedovnoPoDogovoru="DA")
            elif self.redovno_type == "jednokratno":
                kwargs["Jednokratno"] = [
                    tf.JednokratnoType(
                        DanUTjednu=line.day_of_week,
                        RadnoVrijemeOd=line.time_from,
                        RadnoVrijemeDo=line.time_to,
                    )
                ]
            elif self.redovno_type == "dvokratno":
                kwargs["Dvokratno"] = [
                    tf.DvokratnoType(
                        DanUTjednu=line.day_of_week,
                        DioDvokratnog=line.dio_dvokratnog,
                        RadnoVrijemeOd=line.time_from,
                        RadnoVrijemeDo=line.time_to,
                    )
                ]
            elif self.redovno_type == "parni_neparni":
                kwargs["ParniNeparni"] = [
                    tf.ParniNeparniType(
                        DanUTjednu=line.day_of_week,
                        ParNepar=line.par_nepar,
                        RadnoVrijemeOd=line.time_from,
                        RadnoVrijemeDo=line.time_to,
                    )
                ]
            lines.append(tf.RedovnoType(**kwargs))
        return lines

    def _build_iznimke(self, fisk):
        """Build IznimkeType zeep objects from exception records."""
        tf = fisk.type_factory
        iznimke = []
        for iznimka in self.iznimka_ids:
            kwargs = {"Datum": iznimka.date.strftime("%d.%m.%Y")}
            if iznimka.shift_type == "jednokratno":
                kwargs["Jednokratno"] = tf.JednokratnoIznimkeType(
                    RadnoVrijemeOd=iznimka.time_from,
                    RadnoVrijemeDo=iznimka.time_to,
                )
            elif iznimka.shift_type == "dvokratno":
                kwargs["Dvokratno"] = [
                    tf.DvokratnoIznimkeType(
                        DioDvokratnog=iznimka.dio_dvokratnog,
                        RadnoVrijemeOd=iznimka.time_from,
                        RadnoVrijemeDo=iznimka.time_to,
                    )
                ]
            iznimke.append(tf.IznimkeType(**kwargs))
        return iznimke

    def _build_poslovni_prostor(self, fisk):
        """Build PoslovniProstorType for prijavi or obrisi service."""
        tf = fisk.type_factory
        company = self.company_id
        cert_vat = company.l10n_hr_fiscal_cert_subject_vat
        if cert_vat and cert_vat.startswith("HR"):
            cert_vat = cert_vat[2:]
        oib = cert_vat or company.company_registry
        kwargs = dict(
            Oib=oib,
            OznPosPr=self.business_premise_id.l10n_hr_fiscal_code,
        )
        if self.action_type == "prijavi":
            radno_vrijeme = tf.RadnoVrijemeType(
                Redovno=self._build_redovno(fisk) or None,
                Iznimke=self._build_iznimke(fisk) or None,
            )
            kwargs["RadnoVrijeme"] = radno_vrijeme
        elif self.action_type == "obrisi":
            redovno_brisanje = []
            for br in self.brisanje_redovno_date_ids:
                redovno_brisanje.append({"DatumOd": br.date_from.strftime("%d.%m.%Y")})
            iznimke_brisanje = []
            if self.brisanje_iznimka_date_ids:
                for d in self.brisanje_iznimka_date_ids.split(","):
                    d = d.strip()
                    if d:
                        iznimke_brisanje.append({"Datum": d})
            brisanje = tf.RadnoVrijemeBrisanjeType(
                Redovno=redovno_brisanje or None,
                Iznimke=iznimke_brisanje or None,
            )
            kwargs["BrisanjeRadnogVremena"] = brisanje
        return tf.PoslovniProstorType(**kwargs)

    def _get_oib_oper(self):
        company = self.company_id
        cert_vat = company.l10n_hr_fiscal_cert_subject_vat
        if cert_vat and cert_vat.startswith("HR"):
            cert_vat = cert_vat[2:]
        return cert_vat or company.company_registry

    def action_send(self):
        """Send the working time registration to the fiscal service."""
        self.ensure_one()
        company = self.company_id
        time_start = company.get_l10n_hr_time_formatted()
        fiscal_data = company.get_fiscal_data()
        fisk = fiscal.Fiscalization(data=fiscal_data)
        poslovni_prostor = self._build_poslovni_prostor(fisk)
        oib_oper = self._get_oib_oper()
        response = None
        odoo_error = {}
        if self.action_type == "prijavi":
            msg_type = "prijavi_radno_vrijeme"
            try:
                response = fisk.prijavi_radno_vrijeme(poslovni_prostor, oib_oper)
            except Exception as e:
                odoo_error = {"error_message": str(e)}
        else:
            msg_type = "obrisi_radno_vrijeme"
            try:
                response = fisk.obrisi_radno_vrijeme(poslovni_prostor, oib_oper)
            except Exception as e:
                odoo_error = {"error_message": str(e)}
        company.create_fiscal_log(msg_type, fisk, response or odoo_error, time_start, self)
        if odoo_error.get("error_message"):
            self.state = "error"
            raise UserError(odoo_error["error_message"])
        if hasattr(response, "Greske") and response.Greske is not None:
            self.state = "error"
        else:
            self.state = "sent"
        return True


class L10nHrFiscalWorkingTimeLine(models.Model):
    _name = "l10n_hr.fiscal.working.time.line"
    _description = "Working time regular schedule line"

    working_time_id = fields.Many2one(
        comodel_name="l10n_hr.fiscal.working.time",
        ondelete="cascade",
        required=True,
    )
    day_of_week = fields.Selection(
        selection=[
            ("1", "Monday"),
            ("2", "Tuesday"),
            ("3", "Wednesday"),
            ("4", "Thursday"),
            ("5", "Friday"),
            ("6", "Saturday"),
            ("7", "Sunday"),
            ("8", "Holiday"),
        ],
        string="Day of Week",
        required=True,
    )
    dio_dvokratnog = fields.Selection(
        selection=[("1", "First part"), ("2", "Second part")],
        string="Shift Part",
    )
    par_nepar = fields.Selection(
        selection=[("P", "Even"), ("N", "Odd")],
        string="Even/Odd",
    )
    time_from = fields.Char(string="From", required=True, help="Format: HH:MM")
    time_to = fields.Char(string="To", required=True, help="Format: HH:MM")


class L10nHrFiscalWorkingTimeIznimka(models.Model):
    _name = "l10n_hr.fiscal.working.time.iznimka"
    _description = "Working time exception"

    working_time_id = fields.Many2one(
        comodel_name="l10n_hr.fiscal.working.time",
        ondelete="cascade",
        required=True,
    )
    date = fields.Date(string="Date", required=True)
    shift_type = fields.Selection(
        selection=[
            ("jednokratno", "Single shift"),
            ("dvokratno", "Double shift"),
        ],
        default="jednokratno",
        required=True,
    )
    dio_dvokratnog = fields.Selection(
        selection=[("1", "First part"), ("2", "Second part")],
        string="Shift Part",
    )
    time_from = fields.Char(string="From", required=True, help="Format: HH:MM")
    time_to = fields.Char(string="To", required=True, help="Format: HH:MM")


class L10nHrFiscalWorkingTimeBrisanje(models.Model):
    _name = "l10n_hr.fiscal.working.time.brisanje"
    _description = "Working time deletion date entry"

    working_time_id = fields.Many2one(
        comodel_name="l10n_hr.fiscal.working.time",
        ondelete="cascade",
        required=True,
    )
    date_from = fields.Date(string="Date From", required=True)
