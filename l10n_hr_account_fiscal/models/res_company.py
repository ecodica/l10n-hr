# Copyright 2025 Ecodica d.o.o
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import os

from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import MissingError

from ..fiscal import fiscal


class ResCompany(models.Model):
    _inherit = "res.company"

    @staticmethod
    def _get_fiscal_path(sub=None):
        """
        :param sub: additional sub path needed as a string
           - fina_cert/demo
           - fina_cert/prod
        :return:
        """
        path = os.path.dirname(os.path.realpath(__file__))
        path = path.replace("models", "fiscal/")
        return path

    l10n_hr_fiscal_cert_id = fields.Many2one(
        comodel_name="l10n_hr.fiscal.certificate",
        string="Fiscal certificate",
        tracking=1,
        domain="[('state', '=', 'active')]",
        help="Officially issued by Croatian FINA Agency, imported and activated",
    )
    l10n_hr_fiscal_spec = fields.Char(
        string="Special",
        size=1000,
        help="OIB informatičke tvrtke koja održava software, "
        "za demo cert mora odgovarati OIBu sa demo certifikata",
    )
    l10n_hr_fiscal_transaction_type_skip = fields.Boolean(
        string="Skip Bank Transfer Fiscalization", default=True, tracking=1,
        help="""Transakcijski računi se ne fiskaliziraju"""
    )
    l10n_hr_fiscal_on_confirm = fields.Boolean(
        string="Fiscalize Invoice On Confirmation", default=True, tracking=1,
        help="""Invoices will be fiscalized on confirmation"""
    )
    l10n_hr_fiscal_cancel_confirmed_invoice = fields.Boolean(
        string="Cancel Fiscalized Invoices", tracking=1,
        help="""Allow users to cancel fiscalized invoiced"""
    )
    l10n_hr_fiscal_silent_error_logging = fields.Boolean(
        string="Silent Error Logging", default=True, tracking=1,
        help="""If true and if the fiscalization process has failed, then users won't get a warning about it,\
            but the issue will be logged in fiscalitation logs."""
    )

    def _get_log_vals(self, msg_type, msg_obj, response, time_start, origin):
        """
        Inherit in other modules with proper super to add values
        """
        time_stop = self.get_l10n_hr_time_formatted()
        t_obrada = time_stop["time_stamp"] - time_start["time_stamp"]
        time_obr = "%s.%s s" % (t_obrada.seconds, t_obrada.microseconds)
        error_log = ""
        if hasattr(response, "Greske") and response.Greske is not None:
            error_log = "\n".join(
                [
                    " - ".join(
                        [
                            item.SifraGreske,
                            item.PorukaGreske.replace("\t", "").replace("\n", ""),
                        ]
                    )
                    for item in response.Greske.Greska
                ]
            )
        if msg_type == "racuni" and origin.l10n_hr_late_delivery:
            msg_type = "rac_pon"

        values = {
            "user_id": self.env.user.id,
            "type": msg_type,
            "time_stamp": time_stop["datum_vrijeme"],
            "time_obr": time_obr,
            "sadrzaj": False,
            "odgovor": False,
            "greska": error_log != "" and error_log or "OK",
            "company_id": self.id,
        }

        if isinstance(response, dict) and response.get('error_message'): # NOTE: case when response in to received
            values.update({
                "name": _("Fiscalization Failed"),
                "greska": response.get('error_message', False)
            })
        elif isinstance(response, dict) and response.get('delay_message'): # NOTE: case when response in to received
            values.update({
                "name": _("Fiscalization Delayed"),
                "greska": _("Fiscalization Delayed"),
            })
        else:
            values.update({
                "name": msg_type != "echo" and response.Zaglavlje.IdPoruke or "ECHO",
                "time_stamp": msg_type != "echo" and response.Zaglavlje.DatumVrijeme or time_stop["datum_vrijeme"],
                "sadrzaj": etree.tostring(msg_obj.history.last_sent["envelope"]).decode("utf-8"),
                "odgovor": etree.tostring(msg_obj.history.last_sent["envelope"]).decode("utf-8"),
            })

        if origin._name == "account.move":
            values.update(
                {
                    "fiskal_prostor_id": origin.l10n_hr_fiscal_uredjaj_id.prostor_id.id,
                    "fiskal_uredjaj_id": origin.l10n_hr_fiscal_uredjaj_id.id,
                    "invoice_id": origin.id,
                }
            )
        elif origin._name == "l10n.hr.fiskal.uredjaj":
            values.update(
                {
                    "fiskal_prostor_id": origin.prostor_id.id,
                    "fiskal_uredjaj_id": origin.id,
                }
            )
        elif origin._name == "l10n.hr.fiskal.prostor":
            values.update(
                {
                    "fiskal_prostor_id": origin.id,
                }
            )
        return values

    def create_fiscal_log(self, msg_type, msg_obj, response, time_start, origin):
        log_vals = self._get_log_vals(msg_type, msg_obj, response, time_start, origin)
        self.env["l10n_hr.fiscal.log"].create(log_vals)

    def button_test_echo(self, origin=None):
        fd = self.get_fiscal_data()
        fisk = fiscal.Fiscalization(data=fd)
        time_start = self.get_l10n_hr_time_formatted()
        msg = "TEST message"
        echo = fisk.test_service(msg)
        self.create_fiscal_log("echo", fisk, echo, time_start, origin)

    def get_fiscal_data(self):
        fina_cert = self.l10n_hr_fiscal_cert_id
        if not fina_cert:
            raise MissingError(_("Fiscal Certificate not found! Check company setup!"))
        key_file, cert_file, production = fina_cert.get_fiscal_ssl_data()

        fiscal_path = self._get_fiscal_path()
        schema = "".join(
            [
                "file://",
                fiscal_path,
                "schema/Fiskalizacija-WSDL-",
                self.l10n_hr_fiscal_cert_id.fiskal_schema,
            ]
        )
        wsdl_file = schema + "/wsdl/FiskalizacijaService.wsdl"
        cert_path = fiscal_path + "fina_cert/" + self.l10n_hr_fiscal_cert_id.cert_type
        cer_oib = self.l10n_hr_fiscal_cert_id.cert_oib and self.l10n_hr_fiscal_cert_id.cert_oib[2:]
        res = {
            "company_oib": self.company_registry,
            "cert_oib": cer_oib,
            "wsdl": wsdl_file,
            "key": key_file,
            "cert": cert_file,
            "fina_bundle": cert_path + "/fina_bundle.pem",
            "app_cert": cert_path + "/certificate.pem",
            "demo": not production,
        }
        return res



