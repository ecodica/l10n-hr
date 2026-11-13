from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from lxml import etree

from odoo.addons.l10n_hr_pain_base.models.account_payment_order import (
    HR_PAIN_09_FLAVORS,
    HR_SCT_03,
    HR_SCT_INST_09,
)


def _check_partner_address(partner, label):
    """Check that a partner has the address fields required for HR PAIN v09.
    Returns a list of missing-field descriptions (empty list if OK).
    """
    missing = []
    if not partner.city:
        missing.append(_("City"))
    if not partner.country_id:
        missing.append(_("Country"))
    # street is always available; street_name/street_number are provided by
    # base_address_extended — the splitter can parse a raw street later, so
    # only flag it when there is no street at all
    if not partner.street and not partner.street_name and not partner.street_number:
        missing.append(_("Street"))
    if missing:
        return [_("Partner '%(name)s' (%(label)s): %(fields)s.") % {
            "name": partner.name,
            "label": label,
            "fields": ", ".join(missing),
        }]
    return []


def _check_partner_oib(partner, label):
    """Check that a partner has the OIB (company_registry) required for the
    debtor in HR PAIN v09. Returns a list of error messages.
    """
    if not partner.company_registry:
        return [_("Partner '%(name)s' (%(label)s): Company ID (OIB) is required.") % {
            "name": partner.name,
            "label": label,
        }]
    return []


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    def _check_hr_pain_partner_addresses(self):
        """Validate partner addresses for HR PAIN v09 flavors before confirming.
        Checks the debtor (company) and every creditor (payment line partner).
        """
        self.ensure_one()
        if self.payment_method_id.pain_version not in HR_PAIN_09_FLAVORS:
            return

        errors = []

        # --- Debtor (company partner) ---
        debtor_bank = self.company_partner_bank_id
        if debtor_bank:
            debtor_partner = debtor_bank.partner_id
            errors.extend(_check_partner_address(debtor_partner, _("Debtor")))
            errors.extend(_check_partner_oib(debtor_partner, _("Debtor")))

        # --- Creditors (one check per unique partner across all payment lines) ---
        partners_checked = set()
        for line in self.payment_line_ids:
            creditor_bank = line.partner_bank_id
            if not creditor_bank:
                errors.append(_("Partner '%(name)s' (reference '%(ref)s'): "
                                "Bank account is required.") % {
                    "name": line.partner_id.name,
                    "ref": line.name,
                })
                continue
            creditor_partner = creditor_bank.partner_id
            if creditor_partner.id in partners_checked:
                continue
            partners_checked.add(creditor_partner.id)
            errors.extend(_check_partner_address(
                creditor_partner, _("Creditor")))

        if errors:
            raise UserError(_(
                "The following address fields are missing or incomplete. "
                "Please complete them before confirming the payment order:\n\n"
            ) + "\n".join(errors))

    def draft2open(self):
        """Validate HR PAIN v09 partner addresses before confirming."""
        for order in self:
            order._check_hr_pain_partner_addresses()
        return super().draft2open()

    def generate_remittance_info_block(self, parent_node, line, gen_args):
        res = super().generate_remittance_info_block(parent_node, line, gen_args)
        communication_type = line.payment_line_ids[:1].communication_type
        if communication_type == "HR ref":
            remittance_info = parent_node.find('RmtInf')
            structured = remittance_info.find('Strd')
            if structured is not None:
                additional_remittance_info = etree.SubElement(structured, 'AddtlRmtInf')
                additional_remittance_info.text = self._prepare_field('Additional Remittance Information',
                                                                      "line._get_payment_desc()", {'line': line}, 35,
                                                                      gen_args=gen_args)
                payment_ref = structured.find('CdtrRefInf/Ref')
                if payment_ref is not None:
                    payment_ref.text = payment_ref.text.replace(' ', '')
        return res

    def generate_payment_file(self):  # noqa: C901
        """Creates the SEPA Credit Transfer file. That's the important code!"""
        self.ensure_one()
        if not self.payment_method_id.code.startswith('sepa_credit_transfer_hr'):
            return super().generate_payment_file()
        pain_flavor = self.payment_method_id.pain_version
        # We use pain_flavor.startswith('pain.001.001.xx')
        # to support country-specific extensions such as
        # pain.001.001.03.ch.02 (cf l10n_ch_sepa)
        if not pain_flavor:
            raise UserError(_("PAIN version '%s' is not supported.") % pain_flavor)
        if pain_flavor == HR_SCT_03:
            bic_xml_tag = "BIC"
            # size 70 -> 140 for <Nm> with pain.001.001.03
            # BUT the European Payment Council, in the document
            # "SEPA Credit Transfer Scheme Customer-to-bank
            # Implementation guidelines" v6.0 available on
            # http://www.europeanpaymentscouncil.eu/knowledge_bank.cfm
            # says that 'Nm' should be limited to 70
            # so we follow the "European Payment Council"
            # and we put 70 and not 140
            name_maxsize = 70
            root_xml_tag = "CstmrCdtTrfInitn"
        elif pain_flavor in HR_PAIN_09_FLAVORS:
            bic_xml_tag = 'BICFI'
            # size 70 -> 140 for <Nm> with pain.001.001.03
            # BUT the European Payment Council, in the document
            # "SEPA Credit Transfer Scheme Customer-to-bank
            # Implementation guidelines" v6.0 available on
            # http://www.europeanpaymentscouncil.eu/knowledge_bank.cfm
            # says that 'Nm' should be limited to 70
            # so we follow the "European Payment Council"
            # and we put 70 and not 140
            name_maxsize = 70
            root_xml_tag = 'CstmrCdtTrfInitn'
        else:
            raise UserError(_("PAIN version '%s' is not supported.") % pain_flavor)
        xsd_file = self.payment_method_id.get_xsd_file_path()
        gen_args = {
            "bic_xml_tag": bic_xml_tag,
            "name_maxsize": name_maxsize,
            "convert_to_ascii": self.payment_method_id.convert_to_ascii,
            "payment_method": "TRF",
            "file_prefix": self.l10n_hr_get_file_prefix(),
            "pain_flavor": pain_flavor,
            "pain_xsd_file": xsd_file,
        }
        nsmap = self.generate_pain_nsmap()
        attrib = self.generate_pain_attrib()
        xml_root = etree.Element("Document", nsmap=nsmap, attrib=attrib)
        pain_root = etree.SubElement(xml_root, root_xml_tag)
        # A. Group header
        header = self.generate_group_header_block(pain_root, gen_args)
        group_header, nb_of_transactions_a, control_sum_a = header
        transactions_count_a = 0
        amount_control_sum_a = 0.0
        lines_per_group = {}
        # key = (requested_date, priority, local_instrument, categ_purpose)
        # values = list of lines as object
        for line in self.payment_ids:
            payment_line = line.payment_line_ids[:1]
            priority = payment_line.priority
            # namespace and XSD are per file, so the whole order is instant or
            # none of it is; forcing it here keeps the group key, the PmtInfId
            # eval context and LclInstrm/Cd in agreement
            local_instrument = (
                'INST' if pain_flavor == HR_SCT_INST_09
                else payment_line.local_instrument
            )
            categ_purpose = payment_line.category_purpose
            # The field line.date is the requested payment date
            # taking into account the 'date_prefered' setting
            # cf account_banking_payment_export/models/account_payment.py
            # in the inherit of action_open()
            key = (line.date, priority, local_instrument, categ_purpose)
            if key in lines_per_group:
                lines_per_group[key].append(line)
            else:
                lines_per_group[key] = [line]
        for (requested_date, priority, local_instrument, categ_purpose), lines in list(
            lines_per_group.items()
        ):
            # B. Payment info
            requested_date = fields.Date.to_string(requested_date)
            (
                payment_info,
                nb_of_transactions_b,
                control_sum_b,
            ) = self.generate_start_payment_info_block(
                pain_root,
                "self.name + '-' "
                "+ requested_date.replace('-', '')  + '-' + priority + "
                "'-' + local_instrument + '-' + category_purpose",
                priority,
                local_instrument,
                categ_purpose,
                False,
                requested_date,
                {
                    "self": self,
                    "priority": priority,
                    "requested_date": requested_date,
                    "local_instrument": local_instrument or "NOinstr",
                    "category_purpose": categ_purpose or "NOcateg",
                },
                gen_args,
            )
            self.generate_party_block(
                payment_info, "Dbtr", "B", self.company_partner_bank_id, gen_args
            )
            charge_bearer = etree.SubElement(payment_info, "ChrgBr")
            if self.sepa:
                charge_bearer_text = "SLEV"
            else:
                charge_bearer_text = self.charge_bearer
            charge_bearer.text = charge_bearer_text
            transactions_count_b = 0
            amount_control_sum_b = 0.0
            for line in lines:
                transactions_count_a += 1
                transactions_count_b += 1
                # C. Credit Transfer Transaction Info
                credit_transfer_transaction_info = etree.SubElement(
                    payment_info, "CdtTrfTxInf"
                )
                payment_identification = etree.SubElement(
                    credit_transfer_transaction_info, "PmtId"
                )
                instruction_identification = etree.SubElement(
                    payment_identification, "InstrId"
                )
                instruction_identification.text = self._prepare_field(
                    "Instruction Identification",
                    "'/'.join(line.payment_line_ids.mapped('name'))",
                    {"line": line},
                    35,
                    gen_args=gen_args,
                )
                end2end_identification = etree.SubElement(
                    payment_identification, "EndToEndId"
                )
                end2end_identification.text = 'HR99'
                currency_name = self._prepare_field(
                    "Currency Code",
                    "line.currency_id.name",
                    {"line": line},
                    3,
                    gen_args=gen_args,
                )
                amount = etree.SubElement(credit_transfer_transaction_info, "Amt")
                instructed_amount = etree.SubElement(
                    amount, "InstdAmt", Ccy=currency_name
                )
                instructed_amount.text = "%.2f" % line.amount
                amount_control_sum_a += line.amount
                amount_control_sum_b += line.amount
                if not line.partner_bank_id:
                    raise UserError(
                        _(
                            "Bank account is missing on the bank payment line "
                            "of partner '{partner}' (reference '{reference}')."
                        ).format(partner=line.partner_id.name, reference=line.name)
                    )

                self.generate_party_block(
                    credit_transfer_transaction_info,
                    "Cdtr",
                    "C",
                    line.partner_bank_id,
                    gen_args,
                    line,
                )
                line_purpose = line.payment_line_ids[:1].purpose
                if line_purpose:
                    purpose = etree.SubElement(credit_transfer_transaction_info, "Purp")
                    etree.SubElement(purpose, "Cd").text = line_purpose
                self.generate_remittance_info_block(
                    credit_transfer_transaction_info, line, gen_args
                )
            if not pain_flavor.startswith("pain.001.001.02"):
                nb_of_transactions_b.text = str(transactions_count_b)
                control_sum_b.text = "%.2f" % amount_control_sum_b
        if not pain_flavor.startswith("pain.001.001.02"):
            nb_of_transactions_a.text = str(transactions_count_a)
            control_sum_a.text = "%.2f" % amount_control_sum_a
        else:
            nb_of_transactions_a.text = str(transactions_count_a)
            control_sum_a.text = "%.2f" % amount_control_sum_a
        return self.finalize_sepa_file_creation(xml_root, gen_args)
