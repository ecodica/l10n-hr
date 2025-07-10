# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source ERP Solution
#    Author: Uvid d.o.o.
#    Copyright: Uvid d.o.o.
#    web: https://uvid.hr/
#    e-mail: info@uvid.hr
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from collections import defaultdict
from io import BytesIO
from urllib.parse import urlencode

import qrcode

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509
import xml.etree.cElementTree as ET
import uuid
import logging
import time
import datetime
import hashlib
import base64

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_hr_formated_sequence(self, number=0):
        """
        Generates a formatted invoice sequence string according to Croatian fiscalization rules.

        The format follows: 'N/FISCAL_CODE/DEVICE_CODE/YEAR', where:
        - N  is sequence number
        - FISCAL_CODE is the business premise code
        - DEVICE_CODE is the fiscal device code

        Args:
            number (int): Sequence number to include in the formatted string (default is 0).

        Returns:
            str: The formatted fiscal sequence string.
        """
        fiscal_device = self.journal_id.l10n_hr_fiscal_device_ids
        fiscal_code = fiscal_device.l10n_hr_business_premise_id.l10n_hr_fiscal_code
        year = self.invoice_date and self.invoice_date.year or fields.Date().today().year
        sequence = rf'{number}/{fiscal_code}/{fiscal_device.l10n_hr_fiscal_device_code}/{year}'
        return sequence

    def _get_starting_sequence(self):
        """
        Returns the starting invoice sequence for the current move, localized for Croatia.

        If the company is Croatian (`country_id.code == 'HR'`), it generates a fiscalized
        starting sequence. Otherwise, it falls back to the base implementation.

        Returns:
            str: The localized starting sequence.
        """
        if (self.journal_id and
                self.company_id.country_id.code == 'HR' and
                self.journal_id.l10n_hr_fiscal_device_ids and
                self.journal_id.l10n_hr_fiscal_device_ids.l10n_hr_business_premise_id.l10n_hr_fiscal_code):
            return self._l10n_hr_formated_sequence()
        return super()._get_starting_sequence()

    @property
    def _sequence_yearly_regex(self):
        """
        Provides a regex pattern for parsing and validating invoice sequence formats.

        For Croatian companies, the regex matches sequences in the format:
        SEQ/PREFIX1/SUFFIX/YEAR (e.g., 0001/F1/1/2025). For other companies, the default
        or overridden pattern is used.

        Returns:
            str: A regex pattern string with named groups for `seq`, `prefix1`, and `suffix`.
        """
        company_id = self.company_id or self.env.user.company_id
        if company_id.country_id.code == 'HR':
            return r'^(?P<seq>\d*)/?(?P<prefix1>/[^/]*)?(?P<suffix>/[^.]/)?(?P<year>19\d{2}|20\d{2}|21\d{2}|22\d{2})?$'
        return self.journal_id.sequence_override_regex or super()._sequence_yearly_regex

    @property
    def _sequence_fixed_regex(self):
        """
        Provides a regex pattern for parsing and validating invoice sequence formats.

        For Croatian companies, the regex matches sequences in the format:
        SEQ/PREFIX1/SUFFIX/YEAR (e.g., 0001/F1/1/2025). For other companies, the default
        or overridden pattern is used.

        Returns:
            str: A regex pattern string with named groups for `seq`, `prefix1`, and `suffix`.
        """
        company_id = self.company_id or self.env.user.company_id
        if company_id.country_id.code == 'HR':
            return r'^(?P<seq>\d*)/?(?P<prefix1>/[^/]*)?(?P<suffix>/[^.]/)?(?P<year>19\d{2}|20\d{2}|21\d{2}|22\d{2})?$'
        return self.journal_id.sequence_override_regex or super()._sequence_fixed_regex

    def _get_last_sequence_domain(self, relaxed=False):
        """
        Customizes the SQL domain used to retrieve the last invoice sequence,
        incorporating Croatian-specific logic for invoice grouping.

        If the invoice sequence is defined per business premise (`invoice_sequence_by == 'P'`),
        the domain includes all journals linked to the premise.

        Args:
            relaxed (bool): Whether to use a more permissive search domain.

        Returns:
            tuple: A SQL WHERE clause string and corresponding parameter dictionary.
        """
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        company_id = self.company_id or self.env.user.company_id
        if not company_id.country_id.code == 'HR':
            return where_string, param
        business_premise_id = self.journal_id.l10n_hr_fiscal_device_ids.l10n_hr_business_premise_id
        if business_premise_id.l10n_hr_invoice_sequence_by == 'P':
            journal_ids = str(
                tuple(self.journal_id.l10n_hr_business_premise_id.mapped('l10n_hr_journal_ids.id') + [-1, -1]))
            where_string = where_string.replace('journal_id = %(journal_id)s', f'journal_id in {journal_ids}')
        where_string = where_string.replace('AND sequence_prefix !~ %(anti_regex)s ', '')
        return where_string, param

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        """
        Retrieves the last used invoice sequence.

        If invoice sequencing is configured per business premise, the returned sequence is
        formatted with the fiscal code and device code. This is necessary because all journals
        within the same premise share the same fiscal code but may have different device codes,
        and the sequence must continue from the last used number across those devices.

        Args:
            relaxed (bool): Whether to allow a more relaxed domain matching.
            with_prefix (str): Optional sequence prefix to filter by.

        Returns:
            str: The formatted last sequence string, or the fallback if not applicable.
        """
        last_sequence = super()._get_last_sequence(relaxed, with_prefix)
        if not last_sequence or self.company_id.country_id.code != 'HR':
            return last_sequence
        if self.journal_id.l10n_hr_business_premise_id.l10n_hr_invoice_sequence_by != 'P':
            return last_sequence
        seq_format, seq_values = self._get_sequence_format_param(last_sequence)
        last_sequence = self._l10n_hr_formated_sequence(seq_values.get('seq', 0))
        return last_sequence

    def _compute_made_sequence_gap(self):
        """
        Detects and marks gaps in posted invoice sequences, in compliance with
        Croatian fiscal.

        Gaps are identified per journal or per business premise, based on the
        configuration (`invoice_sequence_by`). Moves not yet posted are skipped
        and assumed to have sequence gaps.

        Sets:
            self.made_sequence_gap (bool): True if a gap is detected, otherwise False.
        """
        if self.company_id.country_id.code != 'HR':
            return super()._compute_made_sequence_gap()

        unposted = self.filtered(lambda move: move.sequence_number != 0 and move.state != 'posted')
        unposted.made_sequence_gap = True

        for journal, moves in (self - unposted).grouped(lambda m: m.journal_id).items():
            l10n_hr_invoice_sequence_by = moves.l10n_hr_fiscal_device_id.l10n_hr_business_premise_id.l10n_hr_invoice_sequence_by
            journal_ids = journal.l10n_hr_business_premise_id.mapped(
                'l10n_hr_journal_ids') if l10n_hr_invoice_sequence_by == 'P' else journal

            previous_numbers = set(self.env['account.move'].sudo().search([
                ('journal_id', 'in', list(set(journal_ids.mapped('id')))),
                ('sequence_number', '>=', min(moves.mapped('sequence_number')) - 1),
                ('sequence_number', '<=', max(moves.mapped('sequence_number')) - 1),
            ]).mapped('sequence_number'))
            for move in moves:
                move.made_sequence_gap = move.sequence_number > 1 and (move.sequence_number - 1) not in previous_numbers
        return None

    ####### FISCAL METHODS #######
    l10n_hr_payment_method = fields.Selection(
        selection_add=[('G', 'Cash'), ('K', 'Credit card'), ('C', 'Cheque'), ('T', 'Transaction account'),
                       ('O', 'Other')])

    number_zki = fields.Char(string='ZKI Number', size=64, readonly=True, tracking=101, default=False, copy=False)
    number_jir = fields.Char(string='JIR Number', size=64, readonly=True, tracking=102, default=False, copy=False)
    number_par = fields.Char(string='Paragon Number', size=64, default=False, copy=False)
    last_msg_snd = fields.Text(string='Fiscalisation send', readonly=True, default=False, copy=False)
    last_msg_rcv = fields.Text(string='Fiscalisation reply', readonly=True, default=False, copy=False)
    fisc_state = fields.Selection([
        ('draft', 'Draft'),
        ('error', 'Error'),
        ('done', 'Done'),
    ], string='Fiscalization state', readonly=True, index=True, tracking=100, default='draft', copy=False)
    fisc_user_id = fields.Many2one('res.users', string='Fisc User', readonly=True, default=False, copy=False)
    fisc_employee_id = fields.Many2one('hr.employee', string='Operator', readonly=True, default=False, copy=False)
    fisc_date = fields.Datetime(string='Fisc datetime', readonly=True, tracking=104, default=False, copy=False)
    invoice_date_time = fields.Datetime(string='Invoice datetime', readonly=True, default=False, copy=False)
    working_place_id = fields.Many2one(related='journal_id.l10n_hr_business_premise_id', string='Working Place',
                                       store=True,
                                       readonly=True, copy=False)
    journal_type = fields.Selection(related='journal_id.type', help="Technical field used for usability purposes",
                                    string="Journal Type")
    use_fiscalization = fields.Boolean(related='company_id.use_fiscalization')

    def button_draft(self):
        # fisc_state checks
        res = super().button_draft()
        for move in self:
            if move.fisc_state == 'done':
                raise UserError(_('You cannot reset to draft fiscalized invoices.'))
        return res

    def _invoice_paid_hook(self):
        fisc_paid_invoice = self.env.user.company_id.fisc_paid_invoice
        if fisc_paid_invoice and self.is_invoice(include_receipts=True):
            self.do_fiscal()

    def _get_fisc_user(self):
        # invoice user or logged in user
        if self.company_id.fisc_use_logged_user:
            if not self.env.user.employee_id:
                raise UserError(_('No employee found for user %s!') % self.env.user.name)
            return self.env.user.employee_id.id
        else:
            if not self.invoice_user_id.employee_id:
                raise UserError(_('No employee found for user %s!') % self.invoice_user_id.name)
            return self.invoice_user_id.employee_id.id

    def _number_parser(self, number, seq_id):
        if not number:
            raise UserError('Missing invoice number, Please refresh web page and try again!')
        if not seq_id or not seq_id.used_during_fiscalization or not seq_id.suffix:
            raise UserError(_('Something went wrong, Please check settings of invoice sequence and try again!'))
        try:
            suffix = seq_id.suffix.replace('-', '/').replace(' ', '/').split('/')
            suffix = [x.strip() for x in suffix if x]

            if not len(suffix) >= 2:
                raise ValueError

            opp, onu = suffix[:2]

            number = number.replace('-', '/').replace(' ', '/').split('/')
            number = [x.strip() for x in number if x]
            number = '-'.join(number)

            complete_suffix = number[number.index(f'-{opp}-{onu}'):]
            number_without_suffix = number.replace(complete_suffix, '').split('-')
            bor = number_without_suffix[-1]
            if not bor.isdigit():
                raise ValueError
        except:
            raise UserError(_('Wrong invoice number format!'))
        return bor, opp, onu

    def do_fiscal(self):

        for invoice in self:

            # fisc only invoices paid in full
            if invoice.payment_state not in ['paid', 'in_payment']:
                continue

            use_fiscal = self.env.company.use_fiscalization
            if not use_fiscal:
                return True

            # journal without fisc payment, do nothing
            payments = self.get_payments()
            paymentFisc = False
            for payment in payments:
                # Nikada ne fiskaliziramo plaćanja sa oznakom "Transakcijski račun" - Vlado 21032021
                # slucajevi kombinacije vise placanja - konzultanti?
                if payment.journal_id.l10n_hr_default_fiscal_payment_method == 'T':
                    paymentFisc = False
                    break
                if payment.journal_id.l10n_hr_default_fiscal_payment_method:
                    paymentFisc = True
            if not paymentFisc:
                return True

            if invoice.move_type in ('in_invoice', 'in_refund'):
                return True

            # jel vec fiskaliziran? - problem sa razvezivanjem i pon. placanjem
            if invoice.fisc_state == 'done':
                _logger.warning(u"Nemoguce ponovno fiskalizirati; račun: %s .." % invoice.name)
                return True

            if not invoice.fisc_date:
                self.write({'fisc_date': time.strftime('%Y-%m-%d %H:%M:%S')})
            if not invoice.fisc_employee_id:
                fisc_employee_id = self._get_fisc_user()
                self.write({'fisc_employee_id': fisc_employee_id})
            invoice = self.browse(invoice.id)
            if not invoice.working_place_id:
                raise UserError(_('No working place defined in invoice %s!') % invoice.name)
            if not invoice.journal_id.l10n_hr_business_premise_id:
                raise UserError(_('No working place defined in journal %s!') % invoice.journal_id.name)
            if not invoice.journal_id.l10n_hr_business_premise_id.l10n_hr_fiscal_code:
                raise UserError(
                    _('Working place %s has no code!') % invoice.journal_id.l10n_hr_business_premise_id.l10n_hr_name)
            if not invoice.l10n_hr_fiscal_device_id or not invoice.l10n_hr_fiscal_device_id.l10n_hr_fiscal_device_code:
                raise UserError(_('Missing fiscal device code'))
            if not invoice.name:
                raise UserError(_('Invoice has no number/sequence!'))

            # check tax type - raise if undefined
            for tax in invoice.invoice_line_ids.tax_ids:
                if not tax.l10n_hr_tax_type:
                    raise UserError(_('Invoice Tax is missing fiscalization type definition!'))

            # datum i vrijeme izdavanja racuna ne smije viti vece od datuma fiskalizacije
            if invoice.invoice_date_time > invoice.fisc_date:
                _logger.info(u"invoice_date_time: %s, fisc_date: %s " % (invoice.invoice_date_time, invoice.fisc_date))
                raise UserError(_('Fiscalization date/time can not be earlier than the invoice date!'))

            company_currency_id = self.env.company.currency_id.id
            if company_currency_id != invoice.currency_id.id:
                raise UserError(
                    _('You cannot fiscalize an invoice which is in foreign currency! Change the invoice currency or payment method!'))

            shop_fisced = invoice.journal_id.l10n_hr_business_premise_id.l10n_hr_state == 'active'

            if self.env.user.company_id and use_fiscal:
                # if self.env.user.company_id and use_fiscal and paymentFisc:
                _logger.info(u"-FISK- do_fiscal(): fiskaliziram - "
                             u"AI[ %s ]: %s !" % (invoice.id, invoice.name))
                if not shop_fisced:
                    raise UserError(
                        _('Shop %s is not in open state!') % invoice.journal_id.l10n_hr_business_premise_id.l10n_hr_name)
                cert = self.env.company.certificate_pem
                if cert:
                    if self.number_zki:
                        zki = self.number_zki
                    else:
                        zki = self.get_zki(invoice, invoice.name, cert)
                        if zki:
                            self.write({'number_zki': zki})
                    jir = self.get_jir(invoice, invoice.name, zki, cert)
                    if jir:
                        self.write({'number_jir': jir})
                    else:
                        message = _("Invoice '%s': fiscalization failed.") % invoice.name
                        _logger.info("-FISK- do_fiscal(): - AI[ %s ]: %s !" % (invoice.id, message))

        return True

    def get_zki(self, invoice, number, cert):
        uir = "%0.2f" % invoice.amount_total
        if not invoice.invoice_date_time:
            raise UserError(_('Invoice date/time missing!'))
        datVrijRac = fields.Datetime.context_timestamp(invoice, invoice.invoice_date_time)
        datVrij = datVrijRac.strftime("%d.%m.%Y %H:%M:%S")
        user = self.env.user
        vat = self.env.company.vat
        if not vat:
            raise UserError(_('No VAT code available for current Company!'))
        oib = vat[2:13]
        # seq_id = invoice.journal_id and invoice.journal_id.sequence_id or False
        # bor, opp, onu = self._number_parser(number, seq_id)
        bor, opp, onu = invoice.sequence_number, invoice.journal_id.l10n_hr_business_premise_id.l10n_hr_fiscal_code, invoice.l10n_hr_fiscal_device_id.l10n_hr_fiscal_device_code

        # sanity check - wp code must be equal to the one derived from the invoice number
        if opp != invoice.working_place_id.l10n_hr_fiscal_code:
            raise UserError(_('Mismatch between working place code and invoice number!'))

        # Construct the buffer
        buffer_tmp = str(oib + datVrij + str(bor) + opp + str(onu) + uir)

        # Decode the base64 certificate (assuming it contains both cert and private key)
        decoded = base64.decodebytes(cert)
        # Load certificate
        cert_x509 = x509.load_pem_x509_certificate(decoded)
        # Load private key
        private_key = serialization.load_pem_private_key(decoded, password=None)

        # Get signature hash algorithm used in certificate
        digest = cert_x509.signature_hash_algorithm

        # Sign the buffer
        signature = private_key.sign(
            buffer_tmp.encode('ascii'),
            padding.PKCS1v15(),
            digest
        )
        # signature = crypto.sign(private_key, buffer_tmp.encode('ascii'), digest)
        md5_hash = hashlib.md5()
        md5_hash.update(signature)
        zki = md5_hash.hexdigest()
        return zki

    def get_payments(self):
        all_lines = self.line_ids + \
                    self.line_ids.matched_debit_ids.debit_move_id + \
                    self.line_ids.matched_credit_ids.credit_move_id
        payments = all_lines.move_id.filtered(
            lambda move: move.origin_payment_id or move.matched_payment_ids or move.statement_line_id
        )
        return payments

    def get_payment_journal(self, type='mark'):
        payments = self.get_payments()
        if type != 'mark':
            # return payment names instead of marks.. used in report
            return '\n'.join(payments.mapped('journal_id.name')) if payments else ''
        payment_mark = ""
        for payment in payments:
            if not payment.journal_id.l10n_hr_default_fiscal_payment_method:
                payment_mark = "O"
            if payment_mark not in ("", payment.journal_id.l10n_hr_default_fiscal_payment_method):
                payment_mark = "O"
            if payment_mark == "":
                payment_mark = payment.journal_id.l10n_hr_default_fiscal_payment_method
        return payment_mark

    def get_jir(self, invoice, number, zki, cert):
        self.ensure_one()
        myuuid = uuid.uuid1()
        fiscal_obj = self.env['fiscalization.hr']
        datVrijRacDT = fields.Datetime.context_timestamp(invoice, invoice.fisc_date)
        datVrij = datVrijRacDT.strftime("%d.%m.%YT%H:%M:%S")

        is_refund = self.move_type in ('out_refund', 'in_refund')
        sign = -1 if is_refund else 1

        user = self.env.user
        vat = self.env.company.vat
        if not vat:
            raise UserError(_('No VAT code available for current Company!'))
        oibTvrtke = vat[2:13]

        vat_system = self.env.company.vat_system
        if not vat_system:
            raise UserError(_('No VAT system selection available for current Company!'))
        if vat_system == 'yes':
            uSusPDV = "true"
        else:
            uSusPDV = "false"

        if not invoice.fisc_date:
            raise ValidationError(_('No fisc date found in invoice!'))

        datVrijRacDT = fields.Datetime.context_timestamp(invoice, invoice.invoice_date_time)
        datVrijRacun = datVrijRacDT.strftime("%d.%m.%YT%H:%M:%S")
        oznSlijed = invoice.journal_id.l10n_hr_business_premise_id.l10n_hr_invoice_sequence_by

        # seq_id = invoice.journal_id and invoice.journal_id.sequence_id or False
        # bor, opp, onu = self._number_parser(number, seq_id)
        bor, opp, onu = invoice.sequence_number, invoice.journal_id.l10n_hr_business_premise_id.l10n_hr_fiscal_code, invoice.l10n_hr_fiscal_device_id.l10n_hr_fiscal_device_code

        rootEl = ET.Element("tns:RacunZahtjev")
        rootEl.set("Id", "RacunZahtjev")
        rootEl.set("xmlns:tns", "http://www.apis-it.hr/fin/2012/types/f73")
        rootEl.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        zagEl = ET.SubElement(rootEl, "tns:Zaglavlje")
        idPorEl = ET.SubElement(zagEl, "tns:IdPoruke")
        idPorEl.text = str(myuuid)
        datumVrijemeEl = ET.SubElement(zagEl, "tns:DatumVrijeme")
        datumVrijemeEl.text = datVrij

        racunEl = ET.SubElement(rootEl, "tns:Racun")
        oibEl = ET.SubElement(racunEl, "tns:Oib")
        oibEl.text = oibTvrtke
        uSusPDVEl = ET.SubElement(racunEl, "tns:USustPdv")
        uSusPDVEl.text = uSusPDV
        datVrijRacunEl = ET.SubElement(racunEl, "tns:DatVrijeme")
        datVrijRacunEl.text = datVrijRacun
        oznSlijedEl = ET.SubElement(racunEl, "tns:OznSlijed")
        oznSlijedEl.text = oznSlijed

        brRacEl = ET.SubElement(racunEl, "tns:BrRac")
        brOznRacEl = ET.SubElement(brRacEl, "tns:BrOznRac")
        brOznRacEl.text = str(bor)
        oznPosPrEl = ET.SubElement(brRacEl, "tns:OznPosPr")
        oznPosPrEl.text = str(opp)
        oznNapUrEl = ET.SubElement(brRacEl, "tns:OznNapUr")
        oznNapUrEl.text = str(onu)

        # porezi
        account_tax_obj = self.env['account.tax']
        pdvEl = ET.SubElement(racunEl, "tns:Pdv")
        pnpEl = ET.SubElement(racunEl, "tns:Pnp")
        foundPDV = 0
        foundPNP = 0
        foundOstali = 0
        ostaliPorEl = ET.SubElement(racunEl, "tns:OstaliPor")

        # [('PDV 25%', 338.25, 1353.0, '338,25 kn', '1.353,00 kn', 1, 4)]
        d_taxes = {}
        d_taxes_grouped = defaultdict(lambda: defaultdict(list))
        for taxes in invoice.invoice_line_ids.tax_ids:
            stopa = taxes.amount
            naziv = taxes.name
            tip = taxes.l10n_hr_tax_type
            p_grupa = taxes.tax_group_id.id
            d_taxes.update({p_grupa: (naziv, tip, stopa)})

        for tax_total in invoice.tax_totals['subtotals']:
            for tax_group in tax_total['tax_groups']:
                grouped_tax_ids = account_tax_obj.browse(tax_group['involved_tax_ids']).grouped(lambda t: (t.amount, t.amount_type))
                if len(grouped_tax_ids) > 1:
                    raise UserError(_("Taxes with id of %s belong to the same group but they have conflicted settings. ") % tax_group[
                        'involved_tax_ids'])
                stopa = list(set(account_tax_obj.browse(tax_group['involved_tax_ids']).mapped('amount')))[0]
                iznos = tax_group['tax_amount']
                osnovica = tax_group['base_amount']
                p_grupa = tax_group['group_name']
                d_taxes_grouped[stopa][tip].append(stopa)
                d_taxes_grouped[stopa][tip].append(iznos)
                d_taxes_grouped[stopa][tip].append(osnovica)

        foundTax = 0
        for stopa in d_taxes_grouped:
            for tip in d_taxes_grouped[stopa]:
                if tip == 'pdv':
                    porezEl = ET.SubElement(pdvEl, "tns:Porez")
                    foundTax = 1
                    foundPDV = 1
                if tip == 'pp':
                    porezEl = ET.SubElement(pnpEl, "tns:Porez")
                    foundTax = 1
                    foundPNP = 1

                if foundTax == 0:
                    porezEl = ET.SubElement(ostaliPorEl, "tns:Porez")
                    porNazivEl = ET.SubElement(porezEl, "tns:Naziv")
                    porNazivEl.text = d_taxes_grouped[stopa][tip][0]
                    foundOstali = 1

                stopaEl = ET.SubElement(porezEl, "tns:Stopa")
                stopaEl.text = "%.2f" % stopa
                osnovicaEl = ET.SubElement(porezEl, "tns:Osnovica")
                osnovicaEl.text = "%.2f" % (sign * d_taxes_grouped[stopa][tip][2])
                iznosEl = ET.SubElement(porezEl, "tns:Iznos")
                iznosEl.text = "%.2f" % (sign * d_taxes_grouped[stopa][tip][1])

        if foundPDV == 0:
            racunEl.remove(pdvEl)
        if foundPNP == 0:
            racunEl.remove(pnpEl)
        if foundOstali == 0:
            racunEl.remove(ostaliPorEl)

        # TODO
        # iznosOslobPdvEl = ET.SubElement(racunEl, "tns:IznosOslobPdv")
        # iznosOslobPdvEl.text = "0.00"
        # iznosMarzaEl = ET.SubElement(racunEl, "tns:IznosMarza")
        # iznosMarzaEl.text = "0.00"

        # povratna = 0
        # for line in invoice.invoice_line:
        #    if line.product_id and line.product_id.packaging_fee != 0:
        #        povratna = povratna + line.product_id.packaging_fee * line.quantity

        # if povratna > 0:
        #     nakMainEl = ET.SubElement(racunEl, "tns:Naknade")
        #     nakSubEl = ET.SubElement(nakMainEl, "tns:Naknada")
        #     nakPovNazEl = ET.SubElement(nakSubEl, "tns:NazivN")
        #     nakPovNazEl.text = "Povratna naknada"
        #     nakPovIznEl = ET.SubElement(nakSubEl, "tns:IznosN")
        #     nakPovIznEl.text = "%.2f" % povratna
        # END TODO

        iznosUkupnoEl = ET.SubElement(racunEl, "tns:IznosUkupno")
        iznosUkupnoEl.text = "%.2f" % (sign * invoice.amount_total)

        nacinPl = self.get_payment_journal()
        nacinPlacEl = ET.SubElement(racunEl, "tns:NacinPlac")
        nacinPlacEl.text = nacinPl

        oibOperEl = ET.SubElement(racunEl, "tns:OibOper")
        if not invoice.fisc_employee_id:
            raise UserError(_('No employee found in invoice!'))
        if not invoice.fisc_employee_id.l10n_hr_oib:
            raise UserError(_('No OIB number for employee %s!') % invoice.fisc_employee_id.name)
        oibText = invoice.fisc_employee_id.l10n_hr_oib
        if not oibText:
            raise UserError(_('No OIB number found for employee %s!') % invoice.fisc_employee_id.name)
        oibOperEl.text = oibText
        zastKodEl = ET.SubElement(racunEl, "tns:ZastKod")
        zastKodEl.text = zki
        nakDostEl = ET.SubElement(racunEl, "tns:NakDost")
        if invoice.fisc_state == 'error' or invoice.number_par:
            nakDostEl.text = "true"
        else:
            nakDostEl.text = "false"

        if invoice.number_par:
            nakDostEl = ET.SubElement(racunEl, "tns:ParagonBrRac")
            nakDostEl.text = invoice.number_par

        msg = ET.tostring(rootEl)

        signed_xml = fiscal_obj.sign_file(msg, 'RacunZahtjev')
        retMsg = fiscal_obj.soap_message(signed_xml)
        snd_xml = fiscal_obj.nice_xml(signed_xml)
        rcv_xml = retMsg['response']

        vals_to_write = {}
        jir_number = False
        if retMsg['state'] == 'ok':
            rcv_xml = fiscal_obj.nice_xml(rcv_xml)
            start_jir = rcv_xml.find('<tns:Jir>')
            end_jir = rcv_xml.find('</tns:Jir>')
            if start_jir > 0 and end_jir > 0:
                start_jir = start_jir + 9
                jir_number = rcv_xml[start_jir:end_jir].strip()
                vals_to_write['fisc_state'] = 'done'
            else:
                vals_to_write['fisc_state'] = 'error'
        else:
            vals_to_write['fisc_state'] = 'error'

        if retMsg['state'] == 'error':
            rcv_xml = fiscal_obj.nice_xml(rcv_xml)

        vals_to_write['last_msg_rcv'] = rcv_xml
        vals_to_write['last_msg_snd'] = snd_xml

        invoice.write(vals_to_write)
        return jir_number

        # invoice date can not be set in the past..
        # @api.onchange('invoice_date')
        # def _onchange_invoice_date(self):
        #     curr_date = fields.Date.today()
        #     if self.invoice_date and self.journal_type == 'sale':
        #         if self.invoice_date < curr_date:
        #             #force current date
        #             self.invoice_date = curr_date

        # when writing invoice date, write invoice_date_time field - combining date
        # part from invoice_date and current time (hours, mins, seconds)

    def write(self, values):
        if values.get('invoice_date', False):
            i_d = fields.Datetime.from_string(values.get('invoice_date'))
            curr_time = fields.Datetime.now().time()
            i_dt = datetime.datetime.combine(i_d, curr_time)
            values.update({'invoice_date_time': i_dt})
        return super().write(values)

        # when creating invoice, write the invoice_date_time field - combining date
        # part from invoice_date and current time (hours, mins, seconds)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('invoice_date', False):
                i_d = fields.Datetime.from_string(vals.get('invoice_date'))
                curr_time = fields.Datetime.now().time()
                i_dt = datetime.datetime.combine(i_d, curr_time)
                vals.update({'invoice_date_time': i_dt})
        return super().create(vals_list)

    def _get_name_invoice_report(self):
        super()._get_name_invoice_report()
        self.ensure_one()
        return 'fiscalization_hr.report_invoice_document_hr_fiscalization_fields'

    fisc_qr_code = fields.Binary("Fiscalization QR Code", default=False, copy=False, store=True, compute='_generate_fisc_qr_code')

    @api.depends("number_jir")
    def _generate_fisc_qr_code(self):
        for rec in self:
            is_fisc_move = rec.move_type in ('out_invoice', 'out_refund', 'out_receipt')
            if rec.is_invoice(include_receipts=True) and is_fisc_move:
                if rec.number_zki and rec.number_jir:
                    _logger.info(u"Generating Fiscal QR Code for invoice : %s " % rec.name)
                    qr = qrcode.QRCode(version=1,
                                       error_correction=qrcode.constants.ERROR_CORRECT_L,
                                       box_size=40,
                                       border=4, )
                    qr_data = rec._get_qr_code_vals()
                    qr.add_data(qr_data)
                    qr.make(fit=True)
                    img = qr.make_image()
                    temp = BytesIO()
                    img.save(temp, format="PNG")
                    gen_qr = base64.b64encode(temp.getvalue())
                    rec.fisc_qr_code = gen_qr

    def _get_qr_code_vals(self):
        """
        QR kod kao obvezni sadržaj računa, u skladu s čl. 18.b st. 1. Pravilnika o fiskalizaciji, treba minimalno sadržavati zapis sljedećih podataka:
        1. URL adresa do web-stranice Porezne uprave za provjeru računa
        2. JIR ili zaštitni kod obveznika fiskalizacije
        3. datum i vrijeme izdavanja računa
        4. ukupnu svotu računa.
        Pojedini dijelovi QR koda odvajaju se dodatnim separatorima. Pravilnik o fiskalizaciji uređuje kako se „stvara“ QR kod. Tako je u čl. 18.c Pravilnika o fiskalizaciji navedeno da se pri određivanju QR koda primjenjuje QR model 1 ili model 2 najmanje moguće inačice, a QR kod mora biti minimalne veličine 2 puta 2 cm, pri čemu prazan prostor sa svih strana QR koda mora biti minimalno 2 mm te usklađen sa standardom ISO/IEC 15415. Propisano je također da QR kod mora imati minimalno „L“ (ECC level) razinu korekcije pogreške. QR kod koji će se nalaziti na računu ne smije biti ispisan na slici ili logu niti sadržavati sliku ili logo.

        """
        Params = self.env['ir.config_parameter'].sudo()
        fisc_invoice_check_url = Params.get_param('fisc_invoice_qr_check_url')

        qr_code_vals = {
            'jir': self.number_jir or '',
            'datv': fields.Datetime.context_timestamp(self, self.invoice_date_time).strftime("%Y%m%d_%H%M"),
            'izn': int(self.amount_total * 100) or ''
        }
        return fisc_invoice_check_url + '?' + urlencode(qr_code_vals)
