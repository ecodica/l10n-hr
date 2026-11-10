import base64
import io
import logging
import pytz
import qrcode
from datetime import datetime
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import LockError, UserError, ValidationError
from odoo.tools import float_compare
from odoo.addons.l10n_hr_base.models.res_company import FISCAL_DATETIME_FORMAT, INVOICE_DATETIME_FORMAT
from ..fiscal import fiscal
from ..helpers.fiscal_wrapper import fisc_handler

_logger = logging.getLogger(__name__)


def employee_oib(employee):
    """Return the OIB of ``employee``: the company registry of their work contact.

    Read as superuser: the employee record is HR data that cashiers cannot read, and
    the OIB is all that is taken from it.
    """
    return employee.sudo().work_contact_id.company_registry or False


def operator_errors(operator, user, company):
    """Return why ``operator`` cannot be reported as ``OibOper``, as a list of messages.

    :param operator: the ``hr.employee`` who issued the document, possibly empty
    :param user: the ``res.users`` the operator was looked up for, named when there is none
    :param company: the company the document belongs to
    """
    if not operator:
        return [company.env._(
            "No fiscal operator: %(user)s has no employee in %(company)s. The person who "
            "issues a fiscalized document is reported by the OIB on their employee's work "
            "contact.",
            user=user.display_name,
            company=company.display_name,
        )]
    if not employee_oib(operator):
        return [company.env._(
            "Fiscal operator %(employee)s has no OIB. Enter it on the employee; it is "
            "required for fiscalization.",
            employee=operator.sudo().display_name,
        )]
    return []


class L10nHrFiscalV1Mixin(models.AbstractModel):
    """
    Basic fields and methods for all fiscal classes
    - inherit for invoice, POS, etc...
    """
    _name = "l10n_hr.fiscal.v1.mixin"
    _description = "Croatia Fiscalization 1.0 base mixin"

    l10n_hr_zki = fields.Char(string="ZKI", readonly=True, copy=False)
    l10n_hr_jir = fields.Char(string="JIR", readonly=True, copy=False)
    l10n_hr_paragon_br = fields.Char(
        "Paragon nr.",
        readonly=True,
        copy=False,
        help="If system was down, and invoice is records on 'paragon blok',"
             ". This needs to be entered BEFORE confirming the invoice.",
    )
    l10n_hr_late_delivery = fields.Boolean(
        string="Late delivery",
        readonly=True,
        copy=False,
        help="Checked if message could not be sent at time of invoicing",
    )
    l10n_hr_fiscal_qr = fields.Binary(
        compute="_compute_l10n_hr_fiscal_qr",
        string="Fiscal QR code",
        help="Binary field visible in the interface",
    )
    l10n_hr_fiscal_log_ids = fields.One2many(
        comodel_name="l10n_hr.fiscal.log",
        inverse_name="res_id",
        domain=lambda model: [('res_model', '=', model._name)],
        string="Fiscal message logs",
        help="Log of all messages sent and received for FINA",
        readonly=True
    )
    l10n_hr_fiscal_operator_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Fiscal Operator",
        readonly=True,
        copy=False,
        ondelete="restrict",
        help="The person who issued the document. The OIB on their work contact is "
             "reported to the Tax Administration as OibOper. Set when the document is "
             "first fiscalized and kept afterwards.",
    )
    # promijeniPodatkeRacuna has to repeat the receipt as it was issued (FINA error s012
    # otherwise), while the document itself shows the latest recipient and payment method.
    l10n_hr_fiscal_orig_payment_method = fields.Char(
        string="Reported Payment Method",
        readonly=True,
        copy=False,
        help="NacinPlac the document was fiscalized with. Recorded on the first change of "
             "its fiscal data, empty until then.",
    )
    l10n_hr_fiscal_orig_partner_oib = fields.Char(
        string="Reported Recipient OIB",
        readonly=True,
        copy=False,
        help="OibPrimateljaRacuna the document was fiscalized with, empty when it was "
             "issued without one. Recorded on the first change of its fiscal data.",
    )
    l10n_hr_fiscal_change_allowed = fields.Boolean(
        string="Fiscal Data Can Change",
        compute="_compute_l10n_hr_fiscal_change_allowed",
        help="The document is fiscalized and was issued today, so its recipient and "
             "payment method can still be changed with the tax authority.",
    )

    @api.model
    def _get_fiscal_amount_field_name(self):
        return NotImplementedError('Must be defined in subclass!')

    def _get_fiscal_amount(self):
        """The one canonical total for this document.

        Everything that must agree derives from here: the ZKI
        payload, ``IznosUkupno`` and the QR ``izn`` parameter. It has to be in
        **company currency** and **signed** like ``IznosUkupno``: positive
        for an invoice, negative for a storno.
        """
        self.ensure_one()
        return self[self._get_fiscal_amount_field_name()]

    def _get_fiscal_amount_formatted(self):
        """The canonical total as the exact string that goes to FINA."""
        return fiscal.format_decimal(self._get_fiscal_amount())

    def generate_fiscal_url(self):
        """ Generate URL for fiscalization """
        self.ensure_one()
        url = "https://porezna.gov.hr/rn?"
        # Fiscalized invoice
        if self.l10n_hr_jir:
            url += "jir=" + self.l10n_hr_jir
        # If not fiscalized, for any reason whatsoever
        else:
            url += "zki=" + self.l10n_hr_zki
        fiscal_time = datetime.strptime(self.l10n_hr_fiscal_time, FISCAL_DATETIME_FORMAT).strftime("%Y%m%d_%H%M")
        url += "&datv=" + fiscal_time
        amount = f"&izn={self._get_fiscal_amount_formatted()}"
        url += amount.replace(".", "")  # no decimal point in a link!
        return url

    def _generate_fiscal_qr_code(self):
        self.ensure_one()
        url = self.generate_fiscal_url()
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        try:
            img = qr.make_image(fill_color="black", back_color="white")
            ret = io.BytesIO()
            img.save(ret, img.kind)
            ret.seek(0)
            res = base64.b64encode(ret.getvalue())
        except Exception as e:
            _logger.error(repr(e))
            res = False
        return res

    @api.depends("l10n_hr_jir", "l10n_hr_zki")
    def _compute_l10n_hr_fiscal_qr(self):
        for rec in self:
            rec.l10n_hr_fiscal_qr = False
            if rec.l10n_hr_jir or rec.l10n_hr_zki:
                rec.l10n_hr_fiscal_qr = rec._generate_fiscal_qr_code()

    def _l10n_hr_post_fiscal_check(self):
        res = []
        if self.l10n_hr_fiscal_device_id and self.l10n_hr_fiscal_device_id.fiscalization_active:
            res += operator_errors(self.l10n_hr_fiscal_operator_id, self.env.user, self.company_id)
            if not self.company_id.l10n_hr_fiscal_cert_id:
                res.append(
                    _(
                        "No Fiscal certificate found, please install one "
                        "activate and select it on company setup!"
                    )
                )
            if not self.company_id.company_registry:
                res.append(
                    _("Company OIB is not not entered! It is required for fiscalization")
                )
            res += self._l10n_hr_partner_payment_errors(self.partner_id, self.l10n_hr_payment_method)
        return res

    def _l10n_hr_partner_payment_errors(self, partner, payment_method):
        """Return why this document cannot be reported to ``partner`` paid by ``payment_method``.

        The R1 rules: a company recipient (B2B) needs an OIB and cannot pay by bank
        transfer (FINA error 181), and cash is capped at 10.000,00 €, at 700,00 € for a
        company. Shared by fiscalization and by a later change of the fiscal data. A
        contact of a company is judged by its company.
        """
        res = []
        digits = self.currency_id.decimal_places
        partner = partner.commercial_partner_id
        if partner.is_company and not partner.company_registry:
            res.append(
                self.env._("To fiscalize an R1 invoice, an OIB must be set on the company %s", partner.display_name)
            )
        if partner.is_company and payment_method == 'T':
            res.append(
                self.env._("R1 invoice cannot be fiscalized with %s payment type", payment_method)
            )
        if payment_method == 'G' and float_compare(self.amount_total, 10000, precision_digits=digits) == 1:
            res.append(
                self.env._("Invoice total amount bigger than 10.000,00 € cannot be fiscalized with the %s payment type",
                           payment_method)
            )
        if (
                payment_method == 'G' and
                partner.is_company and
                float_compare(self.amount_total, 700, precision_digits=digits) == 1
        ):
            res.append(
                self.env._("R1 invoice total amount bigger than 700,00 € cannot be fiscalized with the %s payment type",
                           payment_method)
            )
        return res

    @api.model
    def _l10n_hr_recipient_oib(self, partner):
        """Return ``OibPrimateljaRacuna`` for ``partner``: its company's OIB, else empty.

        Only a B2B receipt carries the recipient's OIB; a private person is never
        reported, even with an OIB on file. A contact of a company reports the company's.
        """
        commercial = partner.commercial_partner_id
        return commercial.is_company and commercial.company_registry or ""

    def _l10n_hr_fiscalization_needed(self):
        """"Check if invoice should be fiscalized"""
        if self.l10n_hr_fiscal_device_id.fiscalization_active and (
                not self.company_id.l10n_hr_fiscal_transaction_type_skip or
                self.l10n_hr_payment_method != "T"
        ):
            return True
        return False

    def _get_fisc_tax_values(self):
        """Tax breakdown for the Fiskalizacija message, per fiscal type and rate.

        Must return the shape ``_prepare_fisc_taxes()`` consumes::

            {"Pdv": {rate: {"Osnovica": .., "Iznos": ..}}, "Pnp": {...},
             "OstaliPor": [...], "Naknade": [...],
             "IznosOslobPdv"/"IznosNePodlOpor"/"IznosMarza": "0.00"}

        Amounts are signed by document direction - positive on an invoice,
        negative on a storno - so that they sum to ``IznosUkupno``.

        Implemented per model: the source of tax amounts differs (``account.move``
        reads its ``display_type == 'tax'`` journal items; ``pos.order`` computes
        them from its lines).
        """
        raise NotImplementedError(
            "%s must implement _get_fisc_tax_values()" % self._name
        )

    def _prepare_fisc_taxes(self, factory):
        res = {}
        if self.company_id.l10n_hr_tax_model not in ('r1', 'r2'):
            return res
        tax_data = self._get_fisc_tax_values()
        for pdv in tax_data["Pdv"]:
            if not res.get("Pdv"):
                res["Pdv"] = []
            _pdv = tax_data["Pdv"][pdv]
            porez = factory.type_factory.PorezType(
                Stopa=fiscal.format_decimal(pdv),
                Osnovica=fiscal.format_decimal(_pdv["Osnovica"]),
                Iznos=fiscal.format_decimal(_pdv["Iznos"]),
            )
            res["Pdv"].append(porez)
        for pnp in tax_data["Pnp"]:
            if not res.get("Pnp"):
                res["Pnp"] = []
            _pnp = tax_data["Pnp"][pnp]
            porez = factory.type_factory.PorezType(
                Stopa=fiscal.format_decimal(pnp),
                Osnovica=fiscal.format_decimal(_pnp["Osnovica"]),
                Iznos=fiscal.format_decimal(_pnp["Iznos"]),
            )
            res["Pnp"].append(porez)

        # - currenty no such
        # for ost in tax_data['OstaliPor']:
        #     _ost = tax_data['OstaliPor'][ost]
        #     porez = factory.type_factory.Porez
        #     porez.Naziv = _ost['Naziv']
        #     porez.Stopa = fiscal.format_decimal(ost)
        #     porez.Osnovica = fiscal.format_decimal(_ost['Osnovica'])
        #     porez.Iznos = fiscal.format_decimal(_pnp['Iznos'])
        #     racun.OstaliPor.Porez.append(porez)

        for nak in tax_data["Naknade"]:
            if not res.get("Naknade"):
                res["Naknade"] = []
            # `nak` is a dict; unpacking it as a 2-tuple yielded its keys, so every
            # Naknade tax went out as the literal strings "NazivN"/"IznosN".
            naknada = factory.type_factory.Naknada(
                NazivN=nak["NazivN"], IznosN=fiscal.format_decimal(nak["IznosN"])
            )
            res["Naknade"].append(naknada)
        return res

    def _prepare_fiscal_invoice_total(self):
        """"Get total invoice amount

        NOTE: this used to sum the payment_term lines' balance. That is the same
        number as the canonical amount, but it silently returned "0.00" for a
        document without a payment_term line, while the ZKI was signed over the
        real total. Both now come from the same place.
        """
        return self._get_fiscal_amount_formatted()

    @api.model
    def _get_fiscal_invoice_type(self, factory, msg_type):
        if msg_type == 'promijeniPodatkeRacuna':
            return factory.type_factory.RacunPPType
        else:
            return factory.type_factory.RacunType

    def _prepare_fiscal_invoice(self, factory, fiscal_data, msg_type):
        porezi = self._prepare_fisc_taxes(factory)
        BrRac = factory.type_factory.BrojRacunaType(
            BrOznRac=fiscal_data["racun"][0],
            OznPosPr=fiscal_data["racun"][1],
            OznNapUr=fiscal_data["racun"][2],
        )
        pdv, pnp = None, None
        if porezi.get("Pdv", None):
            pdv = factory.type_factory.PdvType(Porez=porezi["Pdv"])
        if porezi.get("Pnp", None):
            pnp = factory.type_factory.PorezNaPotrosnjuType(Porez=porezi["Pnp"])
        # oib_company = self.company_id.partner_id.company_registry
        # if self.company_id.l10n_hr_fiscal_cert_id.cert_type == "demo":
        #     # demo cert na tudjoj bazi... onda ide oib iz certa
        #     cert_oib = self.company_id.l10n_hr_fiscal_cert_id.cert_oib
        #     oib_company = cert_oib and cert_oib[2:] or False

        RacunType = self._get_fiscal_invoice_type(factory, msg_type)
        racun = RacunType(
            Oib=fiscal_data['cert_vat'],
            USustPdv=self.company_id.l10n_hr_tax_model in ('r1', 'r2'),
            DatVrijeme=self.l10n_hr_fiscal_time,
            OznSlijed=self.l10n_hr_fiscal_device_id.l10n_hr_business_premise_id.l10n_hr_invoice_sequence_by,
            BrRac=BrRac,
            Pdv=pdv,
            Pnp=pnp,
            IznosOslobPdv=porezi.get("IznosOslobPdv", None),
            IznosMarza=porezi.get("IznosMarza", None),
            IznosNePodlOpor=porezi.get("IznosNePodlOpor", None),
            # Naknade=ws_naknade,
            IznosUkupno=self._prepare_fiscal_invoice_total(),
            NacinPlac=self.l10n_hr_payment_method,
            OibOper=employee_oib(self.l10n_hr_fiscal_operator_id),
            ZastKod=self.l10n_hr_zki,
            NakDost=self.l10n_hr_late_delivery,
            ParagonBrRac=self.l10n_hr_paragon_br or None,
            # See Fiskalizacija Tehnička specifikacija, section 13: Errors
            # error v125: "Trenutno ne postoje 'Ostali porezi'"
            OstaliPor=None,
            # error v141: Polje 'Specifična namjena' je namijenjeno za buduće potrebe.
            SpecNamj=None,
        )
        recipient_oib = self._l10n_hr_recipient_oib(self.partner_id)
        if recipient_oib:
            # this is valid OIB, for B2C and B2B customers, without a country prefix
            racun.OibPrimateljaRacuna = recipient_oib
        elif self.partner_id.commercial_partner_id.is_company:
            raise ValidationError(
                _("Partner {} is defined as R1 but missing VAT").format(
                    self.partner_id.commercial_partner_id.display_name))
        return racun

    def _validate_fiscal_invoice(self, racun):
        """Sanity-check the assembled message against the source document.

        Default is a no-op: the checks that matter compare the message with the
        document's own tax lines, which only some models have. Override where a
        meaningful comparison exists.
        """
        return

    def _l10n_hr_default_fiscal_user(self):
        """Login recorded as having transmitted the document, when none was set.

        The base answer - the user doing the fiscalizing - is right for a document raised
        from the back office. The person reported as ``OibOper`` is the fiscal operator,
        see ``_l10n_hr_default_fiscal_operator``.
        """
        return self.env.user.id

    def _l10n_hr_default_fiscal_operator(self):
        """Employee reported as ``OibOper`` when none was set: the person who issued it.

        The base answer is the employee of the user doing the fiscalizing, in the
        document's company. Models where someone else issues the document override it.
        There is no fallback to the login's own OIB: a login can be shared, and an empty
        ``OibOper`` is accepted by FINA and wrong.
        """
        self.ensure_one()
        return self.env.user.with_company(self.company_id).employee_id

    def _l10n_hr_is_late_delivery(self):
        """Whether the message reports a late delivery (``NakDost``).

        A late delivery is a document handed over without a JIR. Here the ZKI is computed
        inside ``fiscalize()``, so a ZKI without a JIR means an earlier attempt issued the
        document and did not get one. A model whose ZKI exists before the first attempt
        decides differently.
        """
        self.ensure_one()
        return bool(self.l10n_hr_zki and not self.l10n_hr_jir)

    @api.model
    def _fisc_msg_type(self):
        """Return list of fisc message types that should be fiscalized."""
        return ["racuni", "provjera"]

    def _handle_fisc_response(self, response, msg_type):
        """Update invoice with received data"""
        self.ensure_one()
        # NOTE: write JIR number if it is received in response
        if hasattr(response, "Jir") and not self.l10n_hr_jir:
            self.l10n_hr_jir = response.Jir

    def fiscalize(self, msg_type="racuni", delay_fiscalization=False):
        """
        Fiskalizira jedan izlazni racun ili point of sale račun
        msg_type : Racun,
        delay_fiscalization : odgodi poziv servisa za fiskalizaciju (generira se samo ZKI broj),
        """
        self.ensure_one()
        # exit if fiscalization is not needed for invoice
        if not self._l10n_hr_fiscalization_needed():
            return

        # before the check, which refuses a document without an operator with an OIB
        if not self.l10n_hr_fiscal_operator_id:
            self.l10n_hr_fiscal_operator_id = self._l10n_hr_default_fiscal_operator()
        errors = self._l10n_hr_post_fiscal_check()
        if errors:
            msg = _("Fiscalization not possible: \n")
            msg += "\n".join(errors)
            raise ValidationError(msg)
        # don't fiscalize invoice if invoice already has jir
        # Was compared against 'racun' while the default is 'racuni', so a document
        # that already had a JIR was re-sent instead of switched to 'provjera'.
        if self.l10n_hr_jir and len(self.l10n_hr_jir) > 30 and msg_type == 'racuni':
            msg_type = 'provjera'
        if not self.l10n_hr_late_delivery and self._l10n_hr_is_late_delivery():
            self.l10n_hr_late_delivery = True
        time_start = self.company_id.get_l10n_hr_time_formatted()
        if not self.l10n_hr_fiscal_user_id:
            # MUST USE CURRENT user for fiscalization!
            # Except in case of paragon račun? or naknadna dostava?
            # but then it should be manually entered already!
            self.l10n_hr_fiscal_user_id = self._l10n_hr_default_fiscal_user()
        fiscal_data = self.company_id.get_fiscal_data()
        fiscal_data["time"] = time_start
        fis_racun = self.l10n_hr_fiscal_number.split(self.company_id.l10n_hr_fiscal_separator)
        assert len(fis_racun) == 3, "Invoice must be assembled using 3 values!"
        fiscal_data["racun"] = fis_racun
        if not self.l10n_hr_zki:
            formatted_date = self.l10n_hr_fiscal_time or time_start["datum_racun"]
            zki_datalist = [
                fiscal_data["cert_vat"],
                formatted_date,
                fis_racun[0],
                fis_racun[1],
                fis_racun[2],
                self._get_fiscal_amount_formatted(),
            ]
            fisk = fiscal.Fiscalization(data=fiscal_data)
            self.l10n_hr_zki = fiscal.generate_zki(
                zki_datalist=zki_datalist, signer=fisk.signer
            )
        fisk = fiscal.Fiscalization(data=fiscal_data)

        # NOTE: call right service proxy
        # list of available services is in FiskalizacijaService.wsdl
        try:
            service_proxy = fisk.client.service[msg_type]
        except:
            raise ValidationError(_("Service proxy %s not found", msg_type))

        if msg_type in self._fisc_msg_type():
            racun = self._prepare_fiscal_invoice(fisk, fiscal_data, msg_type)
            self._validate_fiscal_invoice(racun)
            zaglavlje = fisk.create_request_header()  # self._create_fiskal_header(fisk)
            req_kw = dict(Zaglavlje=zaglavlje, Racun=racun)
            response = None
            odoo_error = {}
            # NOTE: skip calling FINA fiscal service
            if delay_fiscalization:
                self.company_id.create_fiscal_log(msg_type, fisk, {'delay_message': True}, time_start, self)
                return False
            # NOTE: call FINA fisc service
            try:
                response = fisk._call_service(service_proxy, req_kw)
                self.company_id.create_fiscal_log(msg_type, fisk, response, time_start, self)
                self._handle_fisc_response(response, msg_type)
            except AttributeError as e:
                odoo_error = {'error_message': str(e) + '\n' + str(e.obj)}
            except Exception as e:
                # NOTE: handle cases when response is not received from FINA
                odoo_error = {'error_message': e.args[0]}
            # log odoo error
            if odoo_error.get('error_message'):
                self.company_id.create_fiscal_log(msg_type, fisk, odoo_error, time_start, self)
            # raise error
            error_message = response and hasattr(response, 'error_message') and response[
                'error_message'] or odoo_error.get('error_message')
            if error_message and not self.company_id.l10n_hr_fiscal_silent_error_logging:
                raise ValidationError(_("Fiscalization Error:\n %s") % error_message)
        return bool(self.l10n_hr_jir)

    # ------------------------------------------------------------------ change of fiscal data

    def _l10n_hr_is_fiscal_issue_day(self):
        """Whether today, in Croatian time, is the day this document was issued.

        Both sides are Europe/Zagreb wall time: ``l10n_hr_fiscal_time`` is stored that
        way (``dd.mm.yyyyThh:mm:ss``) and ``get_l10n_hr_time_formatted`` returns it.
        """
        self.ensure_one()
        today = self.company_id.get_l10n_hr_time_formatted()["datum"]
        return bool(self.l10n_hr_fiscal_time) and self.l10n_hr_fiscal_time[:10] == today

    @api.model
    def _l10n_hr_fiscal_change_depends(self):
        """Fields ``_l10n_hr_fiscal_change_document_errors`` reads. Models add theirs."""
        return ["l10n_hr_jir", "l10n_hr_fiscal_time"]

    @api.depends(lambda self: self._l10n_hr_fiscal_change_depends())
    def _compute_l10n_hr_fiscal_change_allowed(self):
        """Allow the change of fiscal data while nothing about the document refuses it."""
        for rec in self:
            rec.l10n_hr_fiscal_change_allowed = not rec._l10n_hr_fiscal_change_document_errors()

    def _l10n_hr_fiscal_change_document_errors(self):
        """Return why the recipient and payment method of this document cannot change now.

        Only a document FINA acknowledged can be changed, and only until midnight of the
        day it was issued: after that FINA refuses the change (s011), and the receipt has
        to be cancelled and issued again. Models add their own conditions.
        """
        self.ensure_one()
        if not self.l10n_hr_jir:
            return [self.env._("%(document)s has no JIR: it has not been fiscalized.",
                               document=self.display_name)]
        if not self._l10n_hr_is_fiscal_issue_day():
            return [self.env._(
                "The recipient and payment method of %(document)s can only be changed on the "
                "day it was issued, until midnight. Cancel it and issue a new one instead.",
                document=self.display_name,
            )]
        return []

    def _l10n_hr_fiscal_change_errors(self, partner, payment_method):
        """Return why this document cannot be reported to ``partner`` paid by ``payment_method``."""
        self.ensure_one()
        errors = self._l10n_hr_fiscal_change_document_errors()
        if errors:
            return errors
        if not payment_method:
            return [self.env._("Choose the payment method.")]
        if partner == self.partner_id and payment_method == self.l10n_hr_payment_method:
            return [self.env._("Nothing to change: the customer and payment method are the same.")]
        # as core's company check on the write, which would fail after FINA confirmed
        if partner and not partner.with_context(active_test=False).filtered_domain(
                partner._check_company_domain(self.company_id)):
            errors.append(self.env._("%(partner)s belongs to another company.",
                                     partner=partner.display_name))
        commercial = partner.commercial_partner_id
        if self._l10n_hr_recipient_oib(partner) and not commercial._l10n_hr_is_oib_valid():
            errors.append(self.env._("The OIB of %(partner)s is not valid: it must have 11 digits.",
                                     partner=commercial.display_name))
        return errors + self._l10n_hr_partner_payment_errors(partner, payment_method)

    def _l10n_hr_fiscal_change_warnings(self, partner, payment_method):
        """Return what the change will leave as it is, for the user to know. Models add theirs."""
        self.ensure_one()
        return []

    @api.private
    @fisc_handler(msg_type='promijeniPodatkeRacuna')
    def fiscalize_data_change(self, partner, payment_method):
        """Build the promijeniPodatkeRacuna request for a new recipient and payment method.

        ``Racun`` repeats the receipt as it was issued - FINA compares it with what it
        holds (s012) - so after a first change its payment method and recipient OIB come
        from the recorded originals. ``PromijenjeniNacinPlac`` and
        ``PromijenjeniOibPrimateljaRacuna`` are both mandatory and carry the whole new
        state; an empty OIB element removes the recipient.
        """
        self.ensure_one()
        time_start = self.company_id.get_l10n_hr_time_formatted()
        fiscal_data = self.company_id.get_fiscal_data()
        fiscal_data["time"] = time_start
        fis_racun = self.l10n_hr_fiscal_number.split(self.company_id.l10n_hr_fiscal_separator)
        assert len(fis_racun) == 3, "Invoice must be assembled using 3 values!"
        fiscal_data["racun"] = fis_racun
        fisk = fiscal.Fiscalization(data=fiscal_data)
        invoice_data = self._prepare_fiscal_invoice(fisk, fiscal_data, 'promijeniPodatkeRacuna')
        if self.l10n_hr_fiscal_orig_payment_method:
            invoice_data.NacinPlac = self.l10n_hr_fiscal_orig_payment_method
            invoice_data.OibPrimateljaRacuna = self.l10n_hr_fiscal_orig_partner_oib or None
        invoice_data.PromijenjeniNacinPlac = payment_method
        invoice_data.PromijenjeniOibPrimateljaRacuna = self._l10n_hr_recipient_oib(partner)
        zaglavlje = fisk.create_request_header()
        return dict(Zaglavlje=zaglavlje, Racun=invoice_data)

    @api.model
    def _l10n_hr_fiscal_change_succeeded(self, response):
        """Whether ``response`` confirms the change of fiscal data (``p005``)."""
        if response is None or getattr(response, "Greske", None):
            return False
        reply = getattr(response, "PorukaOdgovora", None)
        return bool(reply) and (reply.SifraPoruke or "").lower() == "p005"

    def _l10n_hr_last_fiscal_log(self, msg_type):
        """Return the latest ``msg_type`` exchange logged for this document."""
        self.ensure_one()
        return self.env["l10n_hr.fiscal.log"].sudo().search([
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
            ("type", "=", msg_type),
        ], order="id desc", limit=1)

    def _l10n_hr_last_fiscal_error(self, msg_type):
        """Return the error of the latest ``msg_type`` exchange logged for this document."""
        log = self._l10n_hr_last_fiscal_log(msg_type)
        return log.error_msg if log.error_msg and log.error_msg != "OK" else False

    def _l10n_hr_change_fiscal_data(self, partner, payment_method):
        """Report a new recipient and payment method to FINA, and write them once confirmed.

        Nothing is written unless FINA confirms with ``p005``: the document must not say
        something the tax authority does not hold. A refusal or a lost reply is returned,
        not raised, so the logged attempt is kept; the change can be tried again until
        midnight. An error before anything was sent, such as a missing certificate, is
        raised. The document is locked first, so two changes are never reported at once.

        :return: why the change was not made, or ``False`` once it is written
        """
        self.ensure_one()
        msg_type = "promijeniPodatkeRacuna"
        try:
            self.lock_for_update(allow_referencing=True)
        except LockError:
            raise UserError(self.env._(
                "%(document)s is being changed by someone else. Try again in a moment.",
                document=self.display_name,
            )) from None
        errors = self._l10n_hr_fiscal_change_errors(partner, payment_method)
        if errors:
            raise UserError("\n".join(errors))
        last_log = self._l10n_hr_last_fiscal_log(msg_type)
        failure = False
        try:
            response = self.fiscalize_data_change(partner, payment_method)
        except UserError as error:
            if self._l10n_hr_last_fiscal_log(msg_type) == last_log:
                raise  # nothing was sent
            # fisc_handler raises after logging the exchange; returning keeps the log
            response, failure = None, str(error)
        if not self._l10n_hr_fiscal_change_succeeded(response):
            return (
                failure
                or self._l10n_hr_last_fiscal_error(msg_type)
                or self.env._("The tax authority did not confirm the change.")
            )
        # read now: after a failed write the transaction may refuse any query
        confirmed_log = self._l10n_hr_last_fiscal_log(msg_type).copy_data()[0]
        document = self.display_name
        old_partner, old_payment_method = self.partner_id, self.l10n_hr_payment_method
        try:
            self._l10n_hr_apply_fiscal_change(partner, payment_method)
            self._l10n_hr_log_fiscal_change(old_partner, old_payment_method, response)
        except Exception as error:
            # FINA holds the change; the rollback of this transaction would lose its log
            confirmed_log["error_msg"] = self.env._(
                "The tax authority confirmed the change, but %(document)s could not be "
                "updated: %(error)s",
                document=document,
                error=error,
            )
            self._l10n_hr_keep_fiscal_log(confirmed_log)
            raise
        return False

    @api.model
    def _l10n_hr_keep_fiscal_log(self, vals):
        """Create a fiscal log in a transaction of its own, which outlives this one."""
        with self.env.registry.cursor() as cr:
            self.env(cr=cr)["l10n_hr.fiscal.log"].sudo().create(vals)

    def _l10n_hr_apply_fiscal_change(self, partner, payment_method):
        """Write the recipient and payment method FINA confirmed.

        The first change also records what the document was issued with, which every
        later change has to repeat. Written as superuser: the change wizard is the
        permission, and an invoicing user need not be allowed to edit a POS order.
        """
        self.ensure_one()
        vals = {"partner_id": partner.id, "l10n_hr_payment_method": payment_method}
        if not self.l10n_hr_fiscal_orig_payment_method:
            vals.update(
                l10n_hr_fiscal_orig_payment_method=self.l10n_hr_payment_method,
                l10n_hr_fiscal_orig_partner_oib=self._l10n_hr_recipient_oib(self.partner_id),
            )
        self.sudo()._l10n_hr_write_fiscal_change(vals)

    def _l10n_hr_write_fiscal_change(self, vals):
        """Write ``vals`` on the fiscalized document. Models override to pass their guards."""
        self.ensure_one()
        self.write(vals)

    def _l10n_hr_log_fiscal_change(self, old_partner, old_payment_method, response):
        """Post the change FINA confirmed on the document's chatter."""
        self.ensure_one()
        lines = self._l10n_hr_fiscal_change_note(old_partner, old_payment_method, response)
        self.sudo().message_post(body=Markup("<br/>").join(lines))

    def _l10n_hr_fiscal_change_note(self, old_partner, old_payment_method, response):
        """Return the lines of the chatter note on a change FINA confirmed. Models add theirs."""
        self.ensure_one()
        methods = dict(self._fields["l10n_hr_payment_method"]._description_selection(self.env))
        none = self.env._("none")
        lines = [self.env._(
            "Fiscal data changed, confirmed by the tax authority: %(code)s %(message)s",
            code=response.PorukaOdgovora.SifraPoruke,
            message=response.PorukaOdgovora.Poruka or "",
        )]
        if old_partner != self.partner_id:
            lines.append(self.env._(
                "Customer: %(old)s (OIB %(old_oib)s) → %(new)s (OIB %(new_oib)s)",
                old=old_partner.display_name or none,
                old_oib=self._l10n_hr_recipient_oib(old_partner) or none,
                new=self.partner_id.display_name or none,
                new_oib=self._l10n_hr_recipient_oib(self.partner_id) or none,
            ))
        if old_payment_method != self.l10n_hr_payment_method:
            lines.append(self.env._(
                "Payment method: %(old)s → %(new)s",
                old=methods.get(old_payment_method, old_payment_method or none),
                new=methods.get(self.l10n_hr_payment_method, self.l10n_hr_payment_method),
            ))
        return lines

    def button_fiscalize_change(self):
        """Open the wizard that changes the recipient with FINA."""
        self.ensure_one()
        return {
            "name": self.env._("Change Fiscal Data"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_hr.change.fiscal.data",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"active_model": self._name, "active_id": self.id},
        }
