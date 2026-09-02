# Copyright 2025 Ecodica d.o.o
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import os

from lxml import etree

from odoo import _, fields, models, api
from odoo.exceptions import MissingError

from ..fiscal import fiscal
from ..helpers.docs_helper import SCHEMA_HELP


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

    l10n_hr_fiscal_cert_ids = fields.Many2many(
        comodel_name="certificate.certificate",
        string="FINA Fiscal certificates",
        tracking=1,
        domain="[('scope', '=', 'fina')]",
        help="Officially issued by Croatian FINA Agency, imported and activated",
    )
    l10n_hr_fiscal_cert_id = fields.Many2one(
        comodel_name="certificate.certificate",
        compute='_compute_l10n_hr_fiscal_cert',
        string="Valid FINA Fiscal certificate",
        tracking=True,
        store=True,
        domain="[('scope', '=', 'fina')]",
        help="Officially issued by Croatian FINA Agency, imported and activated",
    )
    l10n_hr_fiscal_cert_subject_vat = fields.Char(related='l10n_hr_fiscal_cert_id.l10n_hr_subject_vat',
                                                  string='Fiscal Cert Subject VAT', readonly=True)
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
    # l10n_hr_fiscal_on_confirm = fields.Boolean(
    #     string="Fiscalize Invoice On Confirmation", default=True, tracking=1,
    #     help="""Invoices will be fiscalized on confirmation"""
    # )
    l10n_hr_fiscal_cancel_confirmed_invoice = fields.Boolean(
        string="Cancel Fiscalized Invoices", tracking=1,
        help="""Allow users to cancel fiscalized invoiced"""
    )
    l10n_hr_fiscal_silent_error_logging = fields.Boolean(
        string="Silent Error Logging", default=True, tracking=1,
        help="""If true and if the fiscalization process has failed, then users won't get a warning about it,\
            but the issue will be logged in fiscalization logs."""
    )
    l10n_hr_fiscal_test_env = fields.Boolean(
        string="Fiscal Test Mode",
        help="Use the test environment for Fiscalization",
        default=True,
        prefetch=False,
    )
    l10n_hr_fiscal_schema = fields.Selection(
        selection=[
            ("EDUC_v1.6", "DEMO schema v1.6"),
            ("EDUC_v1.7", "DEMO schema v1.7"),
            ("EDUC_v1.8", "DEMO schema v1.8"),
            ("EDUC_v1.9", "DEMO schema v1.9"),
            ("EDUC_v1.10", "DEMO schema v1.10"),
            ("PROD_v1.6", "PROD Schema v1.6"),
            ("PROD_v1.7", "PROD Schema v1.7"),
            ("PROD_v1.8", "PROD Schema v1.8"),
            ("PROD_v1.9", "PROD Schema v1.9"),
            ("PROD_v1.10", "PROD Schema v1.10"),
        ],
        string="Fiscalization schema",
        prefetch=False,
        help=SCHEMA_HELP,
    )

    @api.depends('country_id', 'l10n_hr_fiscal_cert_ids', 'l10n_hr_fiscal_cert_ids.l10n_hr_type')
    def _compute_l10n_hr_fiscal_cert(self):
        for company in self:
            cert_id = False
            if company.country_code == 'HR':
                available_certs = company.l10n_hr_fiscal_cert_ids.filtered("is_valid")
                if company.l10n_hr_fiscal_test_env:
                    cert_id = next(iter(available_certs.filtered(lambda c: c.l10n_hr_type == 'demo')), False)
                else:
                    cert_id = next(iter(available_certs.filtered(lambda c: c.l10n_hr_type == 'prod')), False)
            company.l10n_hr_fiscal_cert_id = cert_id

    def _get_log_vals(self, msg_type, msg_obj, response, time_start, origin):
        """
        Inherit in other modules with proper super to add values
        """
        time_stop = self.get_l10n_hr_time_formatted()
        p_time = time_stop["time_stamp"] - time_start["time_stamp"]
        # total_seconds(): .seconds drops .days so negative intervals wrapped, and
        # .microseconds is not zero-padded so 112 us read as 112 ms.
        process_time = "%.6f s" % p_time.total_seconds()
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
            "company_id": self.id,
            "res_model": origin._name,
            "res_id": origin.id,
            "type": msg_type,
            "reply_timestamp": time_stop["datum_vrijeme"],
            "process_time": process_time,
            "content": False,
            "reply_msg": False,
            "error_msg": error_log != "" and error_log or "OK",
        }

        if isinstance(response, dict) and response.get('error_message'):
            values.update({
                "name": _("Fiscalization Failed"),
                "error_msg": response.get('error_message', False)
            })
        elif isinstance(response, dict) and response.get('delay_message'):
            values.update({
                "name": _("Fiscalization Delayed"),
                "error_msg": _("Fiscalization Delayed"),
            })
        else:
            values.update({
                "name": msg_type != "echo" and response.Zaglavlje.IdPoruke or "ECHO",
                "reply_timestamp": msg_type != "echo" and response.Zaglavlje.DatumVrijeme or time_stop["datum_vrijeme"],
                "content": etree.tostring(msg_obj.history.last_sent["envelope"]).decode("utf-8"),
                "reply_msg": etree.tostring(msg_obj.history.last_received["envelope"]).decode("utf-8"),
            })

        # Appended after the branching above, not before it: the error and delay
        # branches overwrite error_msg wholesale, and an unverified signature
        # matters most precisely when the response was also an error. Verification
        # never raises (see zeep_signer), so recording it beside the message is the
        # only way a failure reaches a human.
        verification_ok = getattr(
            getattr(msg_obj, "fiscal_plugin", None), "last_verification_ok", None
        )
        if verification_ok is False:
            current = values.get("error_msg") or ""
            values["error_msg"] = "\n".join(filter(None, [
                current if current != "OK" else "",
                _("WARNING: the FINA response signature could not be verified."),
            ]))

        # Keyed on the field, not the model name, so any document carrying
        # l10n_hr.fiscal.base.mixin logs its premise and device without a new branch.
        if "l10n_hr_fiscal_device_id" in origin._fields:
            values.update(
                {
                    "business_premise_id": origin.l10n_hr_fiscal_device_id.l10n_hr_business_premise_id.id,
                    "fiscal_device_id": origin.l10n_hr_fiscal_device_id.id,
                }
            )
        elif origin._name == "l10n_hr.fiscal.device":
            values.update(
                {
                    "business_premise_id": origin.l10n_hr_business_premise_id.id,
                    "fiscal_device_id": origin.id,
                }
            )
        elif origin._name == "l10n_hr.business.premise":
            values.update(
                {
                    "business_premise_id": origin.id,
                }
            )
        return values

    def create_fiscal_log(self, msg_type, msg_obj, response, time_start, origin):
        log_vals = self._get_log_vals(msg_type, msg_obj, response, time_start, origin)
        self.env["l10n_hr.fiscal.log"].create(log_vals)

    def button_l10n_hr_test_fiscal_echo(self, origin=None):
        # if called from Company default origin to itself
        origin = origin or self
        fd = self.get_fiscal_data()
        fisk = fiscal.Fiscalization(data=fd)
        time_start = self.get_l10n_hr_time_formatted()
        msg = "TEST message"
        echo = fisk.test_service(msg)
        self.create_fiscal_log("echo", fisk, echo, time_start, origin=origin)

    def get_fiscal_data(self):
        self.ensure_one()
        fiscal_cert = self.l10n_hr_fiscal_cert_id
        if not fiscal_cert:
            raise MissingError(_("Fiscal Certificate not found! Check company setup!"))
        if not self.l10n_hr_fiscal_schema:
            raise MissingError(_("Fiscal schema not found! Check company setup!"))
        demo = self.l10n_hr_fiscal_test_env
        cert_data = fiscal_cert.pem_certificate
        key_data = fiscal_cert.private_key_id.pem_key

        fiscal_path = self._get_fiscal_path()
        schema = "".join(
            [
                "file://",
                fiscal_path,
                "schema/Fiskalizacija-WSDL-",
                self.l10n_hr_fiscal_schema,
            ]
        )
        wsdl_file = schema + "/wsdl/FiskalizacijaService.wsdl"
        cert_path = fiscal_path + "fina_cert/" + self.l10n_hr_fiscal_cert_id.l10n_hr_type
        cert_vat = self.l10n_hr_fiscal_cert_subject_vat and self.l10n_hr_fiscal_cert_subject_vat[2:]
        if self.l10n_hr_fiscal_test_env:
            cert_vat = cert_vat
        else:
            # Maybe totally not needed
            cert_vat = self.company_registry
        res = {
            # "company_vat": self.company_registry,
            "cert_vat": cert_vat,
            "wsdl": wsdl_file,
            "key_data": key_data,
            "cert_data": cert_data,
            "fina_bundle_path": cert_path + "/fina_bundle.pem",
            "app_cert_path": cert_path + "/certificate.pem",
            "demo": demo,
        }
        return res
