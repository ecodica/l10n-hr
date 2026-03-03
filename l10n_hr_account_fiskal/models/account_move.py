import base64
import io
import logging
from datetime import timedelta

import pytz
import qrcode

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from odoo.addons.l10n_hr_base.models.res_company import (
    FISCAL_DATETIME_FORMAT,
    INVOICE_DATETIME_FORMAT,
)

from ..fiskal import fiskal

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n_hr.xml.mixin"]

    # Fiskal fields (moved from l10n.hr.fiskal.mixin)
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
    l10n_hr_fiskal_qr = fields.Binary(
        compute="_compute_l10n_hr_fiskal_qr",
        help="Binary field visible in the interface",
    )
    l10n_hr_fiskal_user_id = fields.Many2one(
        comodel_name="res.partner",
        string="Fiscal Operator",
        copy=False,
        help="Partner (OIB holder) used for fiscalization. Defaults to invoice user.",
    )

    l10n_hr_fiskal_log_ids = fields.One2many(
        comodel_name="l10n.hr.fiskal.log",
        inverse_name="invoice_id",
        string="Fiskal message logs",
        help="Log of all messages sent and received for FINA",
    )

    # Fiskal methods (moved from l10n.hr.fiskal.mixin)
    def generate_fiskal_url(self):
        """Generate URL for fiscalisation"""
        self.ensure_one()
        url = "https://porezna.gov.hr/rn?"
        if self.l10n_hr_jir:
            url += "jir=" + self.l10n_hr_jir
        else:
            url += "zki=" + self.l10n_hr_zki
        datum = self.l10n_hr_invoice_time.strftime("%Y%m%d_%H%M")
        url += "&datv=" + datum
        iznos = "&izn=%.2f" % self.amount_total
        url += iznos.replace(".", "")
        return url

    def _generate_fiskal_qr_code(self):
        self.ensure_one()
        url = self.generate_fiskal_url()
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
            res = base64.b64encode(ret.getvalue()).decode("ascii")
        except Exception as e:
            _logger.error(repr(e))
            res = False
        return res

    @api.depends("l10n_hr_jir", "l10n_hr_zki")
    def _compute_l10n_hr_fiskal_qr(self):
        for inv in self:
            if not inv.l10n_hr_jir and not inv.l10n_hr_zki:
                inv.l10n_hr_fiskal_qr = False
                continue
            inv.l10n_hr_fiskal_qr = inv._generate_fiskal_qr_code()

    def _l10n_hr_post_fiskal_check(self):
        res = []
        if (
            self.l10n_hr_fiscal_device_id.fiskalisation_active
            and not self.company_id.partner_id.company_registry
        ):
            res.append(
                _("Company OIB is not not entered! It is required for fiscalisation")
            )
        if (
            self.l10n_hr_fiscal_device_id.fiskalisation_active
            and self.partner_id.is_company
            and not self.partner_id.company_registry
        ):
            res.append(
                _("To fiscalize an R1 invoice, an OIB must be set on the company %s")
                % self.partner_id.display_name
            )
        if (
            self.l10n_hr_fiscal_device_id.fiskalisation_active
            and self.partner_id.is_company
            and self.l10n_hr_account_payment_type_id.code == 'T'
        ):
            res.append(
                _("R1 invoice cannot be fiscalized with %s payment type")
                % self.l10n_hr_account_payment_type_id.display_name
            )
        if (
            self.l10n_hr_fiscal_device_id.fiskalisation_active
            and self.l10n_hr_account_payment_type_id.code == 'G'
            and float_compare(
                self.amount_total, 10000, precision_digits=self.currency_id.decimal_places
            )
            == 1
        ):
            res.append(
                _(
                    "Invoice total amount bigger than 10.000,00 € cannot be fiscalized "
                    "with the %s payment type"
                )
                % self.l10n_hr_account_payment_type_id.display_name
            )
        if (
            self.l10n_hr_fiscal_device_id.fiskalisation_active
            and self.l10n_hr_account_payment_type_id.code == 'G'
            and self.partner_id.is_company
            and float_compare(
                self.amount_total, 700, precision_digits=self.currency_id.decimal_places
            )
            == 1
        ):
            res.append(
                _(
                    "R1 invoice total amount bigger than 700,00 € cannot be fiscalized "
                    "with the %s payment type"
                )
                % self.l10n_hr_account_payment_type_id.display_name
            )
        if (
            self.l10n_hr_fiscal_device_id.fiskalisation_active
            and not self.l10n_hr_fiskal_user_id.company_registry
        ):
            res.append(
                _("User OIB is not not entered! It is required for fiscalisation")
            )
        if not self.company_id.l10n_hr_fiskal_cert_id:
            res.append(
                _(
                    "No fiscal certificate found, please install one "
                    "activate and select it on company setup!"
                )
            )
        if (
            self.move_type == 'out_refund'
            and self.reversed_entry_id
            and self.l10n_hr_account_payment_type_id
            != self.reversed_entry_id.l10n_hr_account_payment_type_id
        ):
            res.append(
                _(
                    "Croatia Payment Means on origin invoice %s is different from the "
                    "Croatia Payment Means on this invoice. Please change Croatia "
                    "Payment Means to the %s"
                )
                % (self.reversed_entry_id.name, self.l10n_hr_account_payment_type_id.name)
            )
        if (
            self.move_type == 'out_refund'
            and self.reversed_entry_id
            and self.l10n_hr_fiscal_device_id
            != self.reversed_entry_id.l10n_hr_fiscal_device_id
        ):
            res.append(
                _(
                    "Fiskal Device on origin invoice %s is different from the Fiskal "
                    "Device on this invoice. Please change Fiskal Device to the %s"
                )
                % (
                    self.reversed_entry_id.name,
                    self.reversed_entry_id.l10n_hr_fiscal_device_id.l10n_hr_name,
                )
            )
        if self.l10n_hr_fiscal_device_id.fiskalisation_active:
            product_lines_without_tax = self.line_ids.filtered(
                lambda l: l.display_type == 'product' and not l.tax_ids
            )
            if product_lines_without_tax:
                lines_info = ', '.join(
                    product_lines_without_tax[:5].mapped('name')
                )
                if len(product_lines_without_tax) > 5:
                    lines_info += _(' ... (%s more)') % (
                        len(product_lines_without_tax) - 5
                    )
                res.append(
                    _(
                        "The following invoice line(s) must have a tax assigned: %s"
                    ) % lines_info
                )
        return res

    def _l10n_hr_fiscalization_needed(self, message_type):
        """Check if invoice should be fiscalized"""
        l10n_hr_account_payment_type_T = self.env.ref(
            'l10n_hr_account_base.l10n_hr_account_payment_type_T', raise_if_not_found=True
        )
        if self.l10n_hr_fiscal_device_id.fiskalisation_active and (
            not self.company_id.l10n_hr_fiskal_transaction_type_skip
            or self.l10n_hr_account_payment_type_id.code
            != l10n_hr_account_payment_type_T.code
        ):
            return True
        return False

    def _get_fisk_tax_values(self):
        tax_data = {
            "Pdv": {},
            "Pnp": {},
            "OstaliPor": [],
            "Naknade": [],
        }
        iznos_oslob_pdv, iznos_ne_podl_opor, iznos_marza = 0.00, 0.00, 0.00

        for tax_line in self.line_ids.filtered(lambda l: l.display_type == 'tax'):
            if not tax_line.tax_line_id.l10n_hr_fiskal_type:
                raise ValidationError(
                    _("Tax '%s' missing fiskal type!") % tax_line.tax_line_id.name
                )
            fiskal_type = tax_line.tax_line_id.l10n_hr_fiskal_type
            stopa = tax_line.tax_line_id.amount
            osnovica = tax_line.tax_base_amount
            iznos = tax_line.balance * (-1)
            if self.move_type in ['in_refund', 'out_refund']:
                osnovica = osnovica * (-1)

            if fiskal_type in ['Pdv', 'Pnp']:
                if not tax_data[fiskal_type].get(stopa):
                    tax_data[fiskal_type][stopa] = {'Osnovica': osnovica, 'Iznos': 0.0}
                tax_data[fiskal_type][stopa]['Iznos'] += iznos
            elif fiskal_type == "OstaliPor":
                tax_data["OstaliPor"].append({
                    "Naziv": tax_line.tax_line_id.name,
                    "Stopa": stopa,
                    "Osnovica": osnovica,
                    "Iznos": iznos,
                })
            elif fiskal_type == "Naknade":
                tax_data["Naknade"].append({
                    "NazivN": tax_line.tax_line_id.name,
                    "IznosN": iznos,
                })

        for line in self.line_ids.filtered(
            lambda line: line.display_type == "product"
        ):
            for tax in line.tax_ids:
                if not tax.l10n_hr_fiskal_type:
                    raise ValidationError(
                        _("Tax '%s' missing fiskal type!") % tax.name
                    )
                fiskal_type = tax.l10n_hr_fiskal_type
                osnovica = line.balance * (-1)
                if fiskal_type not in ['oslobodenje', 'ne_podlijeze', 'marza']:
                    continue
                if fiskal_type == "oslobodenje":
                    iznos_oslob_pdv += osnovica
                elif fiskal_type == "ne_podlijeze":
                    iznos_ne_podl_opor += osnovica
                elif fiskal_type == "marza":
                    iznos_marza += osnovica

        if iznos_oslob_pdv:
            tax_data["IznosOslobPdv"] = fiskal.format_decimal(iznos_oslob_pdv)
        if iznos_ne_podl_opor:
            tax_data["IznosNePodlOpor"] = fiskal.format_decimal(iznos_ne_podl_opor)
        if iznos_marza:
            tax_data["IznosMarza"] = fiskal.format_decimal(iznos_marza)
        return tax_data

    def _prepare_fisk_racun_taxes(self, factory):
        res = {}
        if not self.company_id.l10n_hr_fiskal_taxative:
            return res
        tax_data = self._get_fisk_tax_values()
        for pdv in tax_data["Pdv"]:
            if not res.get("Pdv"):
                res["Pdv"] = []
            _pdv = tax_data["Pdv"][pdv]
            porez = factory.type_factory.PorezType(
                Stopa=fiskal.format_decimal(pdv),
                Osnovica=fiskal.format_decimal(_pdv["Osnovica"]),
                Iznos=fiskal.format_decimal(_pdv["Iznos"]),
            )
            res["Pdv"].append(porez)
        for pnp in tax_data["Pnp"]:
            if not res.get("Pnp"):
                res["Pnp"] = []
            _pnp = tax_data["Pnp"][pnp]
            porez = factory.type_factory.PorezType(
                Stopa=fiskal.format_decimal(pnp),
                Osnovica=fiskal.format_decimal(_pnp["Osnovica"]),
                Iznos=fiskal.format_decimal(_pnp["Iznos"]),
            )
            res["Pnp"].append(porez)

        for nak in tax_data["Naknade"]:
            if not res.get("Naknade"):
                res["Naknade"] = []
            naknada = factory.type_factory.Naknada(
                NazivN=nak["NazivN"],
                IznosN=fiskal.format_decimal(nak["IznosN"]),
            )
            res["Naknade"].append(naknada)

        if tax_data.get("IznosOslobPdv", None):
            res["IznosOslobPdv"] = tax_data["IznosOslobPdv"]
        return res

    def _prepare_fisk_racun_invoice_total(self):
        """Get total invoice amount"""
        inv_payment_term_lines = self.line_ids.filtered(
            lambda l: l.display_type == "payment_term"
        )
        amount_total = (
            inv_payment_term_lines and sum(il.balance for il in inv_payment_term_lines)
            or 0.0
        )
        return fiskal.format_decimal(amount_total)

    def _prepare_fisk_racun_dat_vrijeme(self):
        """Convert l10n_hr_invoice_time to fiskalization date format."""
        formatted_date = self.l10n_hr_invoice_time.replace(tzinfo=pytz.utc).astimezone(
            pytz.timezone(self.env.context.get("tz") or self.env.user.tz or "UTC")
        ).strftime(FISCAL_DATETIME_FORMAT)
        return formatted_date

    def _get_fisk_racun_type(self, factory, msg_type):
        return factory.type_factory.RacunType

    def _prepare_fisk_racun(self, factory, fiskal_data, msg_type):
        porezi = self._prepare_fisk_racun_taxes(factory)
        BrRac = factory.type_factory.BrojRacunaType(
            BrOznRac=fiskal_data["racun"][0],
            OznPosPr=fiskal_data["racun"][1],
            OznNapUr=fiskal_data["racun"][2],
        )
        pdv, pnp = None, None
        if porezi.get("Pdv", None):
            pdv = factory.type_factory.PdvType(Porez=porezi["Pdv"])
        if porezi.get("Pnp", None):
            pnp = factory.type_factory.PorezNaPotrosnjuType(Porez=porezi["Pnp"])
        oib_company = self.company_id.partner_id.company_registry
        if self.company_id.l10n_hr_fiskal_cert_id.cert_type == "demo":
            cert_oib = self.company_id.l10n_hr_fiskal_cert_id.cert_oib
            oib_company = cert_oib and cert_oib[2:] or False

        RacunType = self._get_fisk_racun_type(factory, msg_type)
        racun = RacunType(
            Oib=oib_company,
            USustPdv=self.company_id.l10n_hr_fiskal_taxative,
            DatVrijeme=self._prepare_fisk_racun_dat_vrijeme(),
            OznSlijed=self.l10n_hr_fiscal_device_id.l10n_hr_business_premise_id.l10n_hr_invoice_sequence_by,
            BrRac=BrRac,
            Pdv=pdv,
            Pnp=pnp,
            IznosOslobPdv=porezi.get("IznosOslobPdv", None),
            IznosMarza=porezi.get("IznosMarza", None),
            IznosNePodlOpor=porezi.get("IznosNePodlOpor", None),
            IznosUkupno=self._prepare_fisk_racun_invoice_total(),
            NacinPlac=self.l10n_hr_account_payment_type_id
            and self.l10n_hr_account_payment_type_id.code
            or 'O',
            OibOper=self.l10n_hr_fiskal_user_id.company_registry,
            ZastKod=self.l10n_hr_zki,
            NakDost=self.l10n_hr_late_delivery,
            ParagonBrRac=self.l10n_hr_paragon_br or None,
            OstaliPor=None,
            SpecNamj=None,
        )
        if self.partner_id.is_company:
            racun.OibPrimateljaRacuna = self.partner_id.company_registry or ''
        return racun

    def _validate_fisk_racun(self, racun):
        """Provjeri ispravnost generiranog fisk racuna prije slanja"""
        racun_osnovica = (
            (racun.Pdv and sum([float(porez.Osnovica) for porez in racun.Pdv.Porez]) or 0.0)
            + float(racun.IznosOslobPdv or 0.0)
        )
        pdv_iznos = (
            racun.Pdv and sum([float(porez.Iznos) for porez in racun.Pdv.Porez]) or 0.0
        )
        pnp_iznos = (
            racun.Pnp and sum([float(porez.Iznos) for porez in racun.Pnp.Porez]) or 0.0
        )
        if not racun.USustPdv:
            racun_osnovica = float(racun.IznosUkupno)
        amount_untaxed = (
            round(float(racun.IznosUkupno), self.currency_id.decimal_places) < 0
            and self.amount_untaxed * (-1)
            or self.amount_untaxed
        )
        tax_amount = (
            sum(
                self.line_ids.filtered(
                    lambda l: l.display_type == 'tax'
                    and l.tax_line_id.l10n_hr_fiskal_type == 'Pdv'
                ).mapped('balance')
            )
            * (-1)
        )
        if float_compare(
            pdv_iznos, tax_amount, precision_digits=self.currency_id.decimal_places
        ):
            raise ValidationError(
                _('Iznos poreza na fisk računu se razlikuje od iznosa poreza na Odoo računu')
            )
        if float_compare(
            racun_osnovica, amount_untaxed, precision_digits=self.currency_id.decimal_places
        ):
            raise ValidationError(
                _('Osnovica na fisk računu se razlikuje od osnovice na Odoo računu')
            )
        if float_compare(
            (racun_osnovica + pdv_iznos + pnp_iznos),
            float(racun.IznosUkupno),
            precision_digits=self.currency_id.decimal_places,
        ):
            raise ValidationError(
                _('Osnovica + Iznosi poreza ne odgovaraju ukupnom iznosu na fisk računu')
            )

    def _fisk_msg_type(self):
        """Return list of fisk message types that should be fiscalized."""
        return ["racuni", "provjera"]

    def _handle_fisk_response(self, response, msg_type):
        """Update invoice with received data"""
        if hasattr(response, "Jir") and not self.l10n_hr_jir:
            self.l10n_hr_jir = response.Jir

    def fiskaliziraj(self, msg_type="racuni", delay_fiscalization=False):
        """
        Fiskalizira jedan izlazni racun ili point of sale račun
        msg_type : Racun,
        delay_fiscalization : odgodi poziv servisa za fiskalizaciju (generira se samo ZKI broj),
        """
        if not self._l10n_hr_fiscalization_needed(msg_type):
            return False

        if self.l10n_hr_jir and len(self.l10n_hr_jir) > 30 and msg_type == 'racun':
            msg_type = 'provjera'
        if (
            self.l10n_hr_zki
            and not self.l10n_hr_jir
            and not self.l10n_hr_late_delivery
        ):
            self.l10n_hr_late_delivery = True

        time_start = self.company_id.get_l10n_hr_time_formatted()
        if not self.l10n_hr_fiskal_user_id:
            self.l10n_hr_fiskal_user_id = self.invoice_user_id.partner_id.id

        errors = self._l10n_hr_post_fiskal_check()
        if errors:
            msg = _("Fiscalisation not possible: \n")
            msg += "\n".join(errors)
            raise ValidationError(msg)

        fiskal_data = self.company_id.get_fiskal_data()
        fiskal_data["time"] = time_start
        fis_racun = self.l10n_hr_fiscal_number.split(
            self.company_id.l10n_hr_fiscal_separator
        )
        assert len(fis_racun) == 3, "Invoice must be assembled using 3 values!"
        fiskal_data["racun"] = fis_racun

        if not self.l10n_hr_zki:
            if fiskal_data["demo"]:
                oib = fiskal_data["cert_oib"]
            else:
                oib = fiskal_data["company_oib"]
            formatted_date = self.l10n_hr_invoice_time.replace(
                tzinfo=pytz.utc
            ).astimezone(
                pytz.timezone(self.env.context.get("tz") or self.env.user.tz or "UTC")
            ).strftime(INVOICE_DATETIME_FORMAT) or time_start["datum_racun"]
            zki_datalist = [
                oib,
                formatted_date,
                fis_racun[0],
                fis_racun[1],
                fis_racun[2],
                fiskal.format_decimal(self.amount_total),
            ]
            fisk = fiskal.Fiskalizacija(fiskal_data=fiskal_data)
            self.l10n_hr_zki = fiskal.generate_zki(
                zki_datalist=zki_datalist, signer=fisk.signer
            )

        fisk = fiskal.Fiskalizacija(fiskal_data=fiskal_data)
        try:
            service_proxy = fisk.client.service[msg_type]
        except Exception:
            raise ValidationError(_("Service proxy %s not found", msg_type))

        if msg_type in self._fisk_msg_type():
            racun = self._prepare_fisk_racun(fisk, fiskal_data, msg_type)
            self._validate_fisk_racun(racun)
            zaglavlje = fisk.create_request_header()
            req_kw = dict(Zaglavlje=zaglavlje, Racun=racun)
            response = None
            odoo_error = {}
            if delay_fiscalization:
                self.company_id.create_fiskal_log(
                    msg_type, fisk, {'delay_message': True}, time_start, self
                )
                return False
            try:
                response = fisk._call_service(service_proxy, req_kw)
                self.company_id.create_fiskal_log(
                    msg_type, fisk, response, time_start, self
                )
                self._handle_fisk_response(response, msg_type)
            except AttributeError as e:
                odoo_error = {'error_message': str(e) + '\n' + str(e.obj)}
            except Exception as e:
                odoo_error = {'error_message': e.args[0]}
            if odoo_error.get('error_message'):
                self.company_id.create_fiskal_log(
                    msg_type, fisk, odoo_error, time_start, self
                )
            error_message = (
                response
                and hasattr(response, 'error_message')
                and response['error_message']
            ) or odoo_error.get('error_message')
            if (
                error_message
                and not self.company_id.l10n_hr_fiskal_silent_error_logging
            ):
                raise ValidationError(_("Fiscalization Error:\n %s") % error_message)
            return True

    # Account move specific methods
    @api.constrains('invoice_date')
    def _check_invoice_date_fiscal_time(self):
        """Ensure that Invoice Date is not later than Time of Invoicing"""
        for move in self:
            if (
                not move.invoice_date
                or not move.l10n_hr_invoice_time
                or move.company_id.account_fiscal_country_id.code != 'HR'
            ):
                continue

            local_l10n_hr_invoice_time = fields.Datetime.context_timestamp(
                move, move.l10n_hr_invoice_time
            )
            fiscal_date = local_l10n_hr_invoice_time.date()
            if move.invoice_date > fiscal_date:
                raise ValidationError(
                    _(
                        "The Invoice Date (%s) cannot be later than the Time of Invoicing (%s)."
                    )
                    % (move.invoice_date, fiscal_date.strftime("%Y-%m-%d"))
                )

    @api.constrains('state')
    def _check_fiscalization_invoice_cancel(self):
        for invoice in self.filtered(
            lambda i: i.move_type in ["out_invoice", "out_refund"]
        ):
            if invoice.company_id.l10n_hr_fiskal_cancel_confirmed_invoice:
                continue
            if invoice.l10n_hr_zki and invoice.state != 'posted':
                raise ValidationError(
                    _(
                        "Canceling or returning fiscalized invoiced in draft is disabled. "
                        "If necessary, enable this feature on company."
                    )
                )

    def _check_zki_on_confirm(self):
        """Check if on confirmed invoice ZKI is set for invoiced that should be fiscalized"""
        for invoice in self.filtered(lambda i: i.state == 'posted'):
            if invoice._l10n_hr_fiscalization_needed(
                'racuni'
            ) and not invoice.l10n_hr_zki:
                raise ValidationError(
                    _(
                        "ZKI number is not set on invoice that should be fiscalized. "
                        "Check if fiscalization is properly configured."
                    )
                )

    def _post(self, soft=True):
        """Extend to verify if required fiscalization data is set on posted invoices"""
        invoices = super()._post(soft=soft)
        invoices._check_zki_on_confirm()
        return invoices

    def button_draft(self):
        """Extend to clear ZKI if not fully fiscalized"""
        for move in self:
            if move.l10n_hr_zki and not move.l10n_hr_jir:
                move.l10n_hr_zki = False
        super().button_draft()

    def action_cron_fiskaliziraj_batch(self):
        move_ids = self.search([
            ('l10n_hr_jir', '=', False),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', 'not in', ['draft']),
            ('l10n_hr_fiscal_device_id.fiskalisation_active', '=', True),
            ('l10n_hr_fiscal_device_id.enable_cron_fiskalisation', '=', True),
        ])

        moves_to_process = self.env['account.move']
        timestamp = fields.Datetime.now()
        for move in move_ids:
            delay_hours = (
                move.l10n_hr_fiscal_device_id.cron_fiskalisation_delay_hours or 0
            )
            required_processing_time = move.l10n_hr_invoice_time + timedelta(
                hours=delay_hours
            )

            if required_processing_time < timestamp:
                moves_to_process += move

        if len(moves_to_process) > 0:
            moves_to_process._fiskaliziraj_batch()

    def action_manual_fiskaliziraj_batch(self):
        total_selected_count = len(self)
        fiscalized_move_ids = self.filtered(
            lambda x: x.l10n_hr_jir and x.l10n_hr_zki
        )
        already_fiscalized_count = len(fiscalized_move_ids)
        not_fiscalized_move_ids = self - fiscalized_move_ids

        if not not_fiscalized_move_ids:
            return self._get_notification_action(
                _("Already Fiscalized"),
                _("All selected invoices are already fiscalized"),
                "info",
            )

        success, skipped, failed = not_fiscalized_move_ids._fiskaliziraj_batch()

        if success == 0 and failed == 0:
            return self._get_notification_action(
                _("Fiscalization Skipped"),
                _(
                    "All selected invoices are fiscalized or do not need fiscalization"
                ),
                "info",
            )

        elif failed == 0:
            return self._get_notification_action(
                _("Fiscalization Successfull"),
                _(
                    "Fiscalization result: Started: %s | Skipped: %s | Fiscalized: %s"
                )
                % (total_selected_count, already_fiscalized_count + skipped, success),
                "success",
            )
        else:
            return self._get_notification_action(
                _("Fiscalization Finished: Failures Detected"),
                _(
                    "Fiscalization result: Started: %s | Skipped: %s | Fiscalized: %s | Failed: %s"
                )
                % (
                    total_selected_count,
                    already_fiscalized_count + skipped,
                    success,
                    failed,
                ),
                "warning",
            )

    def _fiskaliziraj_batch(self):
        """Attempts fiscalization for records in the current set."""
        success_count = 0
        skipped_count = 0
        error_count = 0

        for move in self:
            try:
                res = move.fiskaliziraj()
                if res:
                    success_count += 1
                else:
                    skipped_count += 1
            except Exception:
                error_count += 1
                continue

        return success_count, skipped_count, error_count

    def _get_notification_action(self, title, message, type):
        """Returns notification action for client"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': type,
                'sticky': True,
            },
        }

    def button_fiskaliziraj(self):
        self.ensure_one()
        self.fiskaliziraj()

    def button_provjera_fiskalizacije(self):
        self.fiskaliziraj(msg_type='provjera')

    def _l10n_hr_post_out_invoice(self):
        res = super()._l10n_hr_post_out_invoice()
        delay_fiscalization = not self.l10n_hr_fiscal_device_id.enable_fiskalise_on_confirm
        if self.l10n_hr_fiscal_device_id.fiskalisation_active and not self.l10n_hr_jir:
            self.fiskaliziraj(delay_fiscalization=delay_fiscalization)
        return res

    @api.model
    def search_not_fiscalized_invoice_count(self, company_id):
        """Search for count of Account Moves that are not fiscalized"""
        domain = [
            ('l10n_hr_zki', '!=', False),
            ('l10n_hr_jir', '=', False),
            ('state', '=', 'posted'),
            ('company_id', '=', company_id),
        ]
        count = self.env['account.move'].sudo().search_count(domain)
        return {'count': count}
