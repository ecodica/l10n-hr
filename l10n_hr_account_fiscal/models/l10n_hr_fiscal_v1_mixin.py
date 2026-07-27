import base64
import io
import logging
import pytz
import qrcode
from datetime import datetime
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from odoo.addons.l10n_hr_base.models.res_company import FISCAL_DATETIME_FORMAT, INVOICE_DATETIME_FORMAT
from ..fiscal import fiscal
from ..helpers.fiscal_wrapper import fisc_handler

_logger = logging.getLogger(__name__)


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

    @api.model
    def _get_fiscal_amount_field_name(self):
        return NotImplementedError('Must be defined in subclass!')

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
        amount = "&izn=%.2f" % self[self._get_fiscal_amount_field_name()]
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
            if not self.l10n_hr_fiscal_user_id.company_registry:
                res.append(
                    _("User OIB is not not entered! It is required for fiscalization")
                )
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
            if (
                    self.l10n_hr_fiscal_device_id.fiscalization_active and
                    self.partner_id.is_company and
                    not self.partner_id.company_registry
            ):
                res.append(
                    _("To fiscalize an R1 invoice, an OIB must be set on the company %s") % self.partner_id.display_name
                )
            if (
                    self.l10n_hr_fiscal_device_id.fiscalization_active and
                    self.partner_id.is_company and
                    self.l10n_hr_payment_method == 'T'
            ):
                res.append(
                    _("R1 invoice cannot be fiscalized with %s payment type") % self.l10n_hr_payment_method
                )
            if (
                    self.l10n_hr_fiscal_device_id.fiscalization_active and
                    self.l10n_hr_payment_method == 'G' and
                    float_compare(self.amount_total, 10000, precision_digits=self.currency_id.decimal_places) == 1
            ):
                res.append(
                    _("Invoice total amount bigger than 10.000,00 € cannot be fiscalized with the %s payment type") %
                    self.l10n_hr_payment_method
                )
            if (
                    self.l10n_hr_fiscal_device_id.fiscalization_active and
                    self.l10n_hr_payment_method == 'G' and
                    self.partner_id.is_company and
                    float_compare(self.amount_total, 700, precision_digits=self.currency_id.decimal_places) == 1
            ):
                res.append(
                    _("R1 invoice total amount bigger than 700,00 € cannot be fiscalized with the %s payment type") %
                    self.l10n_hr_payment_method
                )
        return res

    def _l10n_hr_fiscalization_needed(self):
        """"Check if invoice should be fiscalized"""
        if self.l10n_hr_fiscal_device_id.fiscalization_active and (
                not self.company_id.l10n_hr_fiscal_transaction_type_skip or
                self.l10n_hr_payment_method != "T"
        ):
            return True
        return False

    def _get_fisc_tax_values(self):
        tax_data = {
            "Pdv": {},
            "Pnp": {},
            "OstaliPor": [],
            "Naknade": [],
        }
        iznos_oslob_pdv, iznos_ne_podl_opor, iznos_marza = 0.00, 0.00, 0.00

        for tax_line in self.line_ids.filtered(lambda l: l.display_type == 'tax'):
            if not tax_line.tax_line_id.l10n_hr_fiscal_type:
                raise ValidationError(_("Tax %s missing fiscal type!") % tax_line.tax_line_id.name)
            fiscal_type = tax_line.tax_line_id.l10n_hr_fiscal_type
            rate = tax_line.tax_line_id.amount
            # NOTE: base_amount and amount should be on credit side so balance will be negative
            base_amount = tax_line.tax_base_amount
            amount = tax_line.balance * (-1)
            # if the move is a refund, reverse the base_amount
            if self.move_type in ['in_refund', 'out_refund']:
                base_amount = base_amount * (-1)

            if fiscal_type in ['Pdv', 'Pnp']:
                if not tax_data[fiscal_type].get(rate):
                    tax_data[fiscal_type][rate] = {'Osnovica': base_amount, 'Iznos': 0.0}
                tax_data[fiscal_type][rate]['Iznos'] += amount
            elif fiscal_type == "OstaliPor":
                tax_data["OstaliPor"].append({
                    "Naziv": tax_line.tax_line_id.name,
                    "Stopa": rate,
                    "Osnovica": base_amount,
                    "Iznos": amount,
                })

            elif fiscal_type == "Naknade":
                tax_data["Naknade"].append({"NazivN": tax_line.tax_line_id.name, "IznosN": amount})

        # NOTE: Stavke oslobodjene od poreza, Odoo ne kreira stavke temeljnice ako je stop 0.0
        # TODO: provjeriti kako slati stavke sa stopom 0 i da li ima takvih slucajeva u praksi
        for line in self.line_ids.filtered(lambda line: line.display_type == "product"):
            for tax in line.tax_ids:
                if not tax.l10n_hr_fiscal_type:
                    raise ValidationError(_("Tax '%s' missing fiskal type!") % tax.name)
                fiscal_type = tax.l10n_hr_fiscal_type
                # TODO verify if this logic is valid to get invoice and refund amounts
                base_amount = line.balance * (-1)
                if fiscal_type not in ['oslobodenje', 'ne_podlijeze', 'marza']:
                    continue
                if fiscal_type == "oslobodenje":
                    iznos_oslob_pdv += base_amount
                elif fiscal_type == "ne_podlijeze":
                    iznos_ne_podl_opor += base_amount
                elif fiscal_type == "marza":
                    iznos_marza += base_amount

        # TODO: ovi porezi se ne salju, potrebno ih je ukljuciti ako ih ima
        if iznos_oslob_pdv:
            tax_data["IznosOslobPdv"] = fiscal.format_decimal(iznos_oslob_pdv)
        if iznos_ne_podl_opor:
            tax_data["IznosNePodlOpor"] = fiscal.format_decimal(iznos_ne_podl_opor)
        if iznos_marza:
            tax_data["IznosMarza"] = fiscal.format_decimal(iznos_marza)
        return tax_data

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
            naziv, iznos = nak
            naknada = factory.type_factory.Naknada(
                NazivN=naziv, IznosN=fiscal.format_decimal(iznos)
            )
            res["Naknade"].append(naknada)
        return res

    def _prepare_fiscal_invoice_total(self):
        """"Get total invoice amount"""
        inv_payment_term_lines = self.line_ids.filtered(lambda l: l.display_type == "payment_term")
        amount_total = inv_payment_term_lines and sum(il.balance for il in inv_payment_term_lines) or 0.0
        return fiscal.format_decimal(amount_total)

    def _prepare_fiscal_date_time(self):
        """Convert l10n_hr_vrijeme_izdavanja to fiskalization date format.s"""
        # TODO: v19 use self.env.tz?
        formatted_date = self.l10n_hr_vrijeme_izdavanja.replace(tzinfo=pytz.utc).astimezone(
            pytz.timezone(self.env.context.get("tz") or self.env.user.tz or "UTC")).strftime(FISCAL_DATETIME_FORMAT)
        return formatted_date

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
            OibOper=self.l10n_hr_fiscal_user_id.company_registry,
            ZastKod=self.l10n_hr_zki,
            NakDost=self.l10n_hr_late_delivery,
            ParagonBrRac=self.l10n_hr_paragon_br or None,
            # See Fiskalizacija Tehnička specifikacija, section 13: Errors
            # error v125: "Trenutno ne postoje 'Ostali porezi'"
            OstaliPor=None,
            # error v141: Polje 'Specifična namjena' je namijenjeno za buduće potrebe.
            SpecNamj=None,
        )
        if self.partner_id.is_company:
            if self.partner_id.company_registry:
                # this is valid OIB, for B2C and B2B customers, without a country prefix
                racun.OibPrimateljaRacuna = self.partner_id.company_registry
            else:
                raise ValidationError(
                    _("Partner {} is defined as R1 but missing VAT").format(self.partner_id.display_name))
        return racun

    def _validate_fiscal_invoice(self, racun):
        """Provjeri ispravnost generiranog fisk racuna prije slanja"""
        racun_osnovica = racun.Pdv and sum([float(porez.Osnovica) for porez in racun.Pdv.Porez]) or 0.0
        pdv_iznos = racun.Pdv and sum([float(porez.Iznos) for porez in racun.Pdv.Porez]) or 0.0
        pnp_iznos = racun.Pnp and sum([float(porez.Iznos) for porez in racun.Pnp.Porez]) or 0.0
        # NOTE: ako je ukupni iznos računa negativan tada je negativna i osnovica računa
        # NOTE: ako tvrtka nije u sustava PDV_a, tada j iznos racuna jednak ukupnom iznosu racuna
        if not racun.USustPdv:
            racun_osnovica = float(racun.IznosUkupno)
        amount_untaxed = (
                round(float(racun.IznosUkupno), self.currency_id.decimal_places) < 0 and
                self.amount_untaxed * (-1) or
                self.amount_untaxed)
        # NOTE: provjera da li iznos poreza na fisk racunu odgovora iznosu odoo poreza
        tax_amount = sum(self.line_ids.filtered(
            lambda l: l.display_type == 'tax' and l.tax_line_id.l10n_hr_fiscal_type == 'Pdv').mapped('balance')) * (-1)
        if float_compare(pdv_iznos, tax_amount, precision_digits=self.currency_id.decimal_places):
            raise ValidationError(_('Iznos poreza na fisk računu se razlikuje od iznosa poreza na Odoo računu'))
        # NOTE: provjera da li je osnovica na Odoo računu isto osnovici koju fiskaliziramo
        # kao iznos osnovice koji fiskaliziramo dovoljno dobro je uzeti osnovice Pdv-a koje fiskaliziramo
        # TODO: za sada nisu podržani dodani porezi, naknade, ...
        if float_compare(racun_osnovica, amount_untaxed, precision_digits=self.currency_id.decimal_places):
            raise ValidationError(_('Osnovica na fisk računu se razlikuje od osnovice na Odoo računu'))
        # NOTE: provjera da li suma osnovice i poreza sa fisk računa odgovara ukupno iznosu odoo računa
        if float_compare(
                (racun_osnovica + pdv_iznos + pnp_iznos),
                float(racun.IznosUkupno),
                precision_digits=self.currency_id.decimal_places):
            raise ValidationError(_('Osnovica + Iznosi poreza ne odgovaraju ukupnom iznosu na fisk računu'))

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

        errors = self._l10n_hr_post_fiscal_check()
        if errors:
            msg = _("Fiscalization not possible: \n")
            msg += "\n".join(errors)
            raise ValidationError(msg)
        # don't fiscalize invoice if invoice already has jir
        if self.l10n_hr_jir and len(self.l10n_hr_jir) > 30 and msg_type == 'racun':
            msg_type = 'provjera'
        if self.l10n_hr_zki and not self.l10n_hr_jir and not self.l10n_hr_late_delivery:
            self.l10n_hr_late_delivery = True
        time_start = self.company_id.get_l10n_hr_time_formatted()
        if not self.l10n_hr_fiscal_user_id:
            # MUST USE CURRENT user for fiscalization!
            # Except in case of paragon račun? or naknadna dostava?
            # but then it should be manually entered already!
            self.l10n_hr_fiscal_user_id = self.invoice_user_id.id
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
                fiscal.format_decimal(self[self._get_fiscal_amount_field_name()]),
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
            # self._validate_fiscal_invoice(racun)
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

    @fisc_handler(msg_type='promijeniPodatkeRacuna')
    def fiscalize_data_change(self, partner, payment_method):
        if not self._l10n_hr_fiscalization_needed():
            return
        time_start = self.company_id.get_l10n_hr_time_formatted()
        fiscal_data = self.company_id.get_fiscal_data()
        fiscal_data["time"] = time_start
        fis_racun = self.l10n_hr_fiscal_number.split(self.company_id.l10n_hr_fiscal_separator)
        assert len(fis_racun) == 3, "Invoice must be assembled using 3 values!"
        fiscal_data["racun"] = fis_racun
        fisk = fiscal.Fiscalization(data=fiscal_data)
        invoice_data = self._prepare_fiscal_invoice(fisk, fiscal_data, 'promijeniPodatkeRacuna')
        invoice_data.PromijenjeniNacinPlac = payment_method
        invoice_data.PromijenjeniOibPrimateljaRacuna = partner and partner.company_registry or None
        zaglavlje = fisk.create_request_header()
        return dict(Zaglavlje=zaglavlje, Racun=invoice_data)
