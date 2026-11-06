# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from lxml import etree

from odoo import models
from odoo.addons.l10n_hr_address_split.tools import hr_street_split

HR_SCT_03 = 'scthr:pain.001.001.03'
HR_SCT_09 = 'scthr:pain.001.001.09'
HR_SCT_INST_09 = 'sctinsthr:pain.001.001.09'
HR_PAIN_FLAVORS = (HR_SCT_03, HR_SCT_09, HR_SCT_INST_09)
# structured PstlAdr, OIB in Dbtr/Id, ReqdExctnDt wrapped in <Dt>, BICFI
HR_PAIN_09_FLAVORS = (HR_SCT_09, HR_SCT_INST_09)


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    def _get_file_prefix(self):
        self.ensure_one()
        date_today = datetime.today().strftime('%Y%m%d')
        return 'UN' + date_today + str(1).zfill(4)

    def compute_sepa_final_hook(self, sepa):
        self.ensure_one()
        sepa = super().compute_sepa_final_hook(sepa)
        pain_flavor = self.payment_mode_id.payment_method_id.pain_version
        if pain_flavor in HR_PAIN_FLAVORS:
            sepa = True
        return sepa

    def generate_pain_nsmap(self):
        self.ensure_one()
        nsmap = super().generate_pain_nsmap()
        pain_flavor = self.payment_mode_id.payment_method_id.pain_version
        # In Croatia it is scthr:pain.001.001.03
        # <Document xmlns="="urn:iso:std:iso:20022:tech:xsd:scthr:pain.001.001.03">
        if pain_flavor in HR_PAIN_FLAVORS:
            nsmap[None] = 'urn:iso:std:iso:20022:tech:xsd:%s' % pain_flavor
        return nsmap

    def generate_pain_attrib(self):
        self.ensure_one()
        pain_flavor = self.payment_mode_id.payment_method_id.pain_version
        if pain_flavor in HR_PAIN_FLAVORS:
            pass
        else:
            return super().generate_pain_attrib()

    def generate_group_header_block(self, parent_node, gen_args):
        group_header, nb_of_transactions, control_sum = super().generate_group_header_block(parent_node, gen_args)
        if gen_args.get('pain_flavor') in HR_PAIN_FLAVORS:
            msg_id = group_header.find('.//MsgId')
            if msg_id is not None:
                prefix = gen_args['file_prefix'].replace('.', '')
                msg_id.text = prefix + msg_id.text
        return group_header, nb_of_transactions, control_sum

    def generate_start_payment_info_block(self, parent_node, payment_info_ident, priority, local_instrument,
                                          category_purpose, sequence_type, requested_date, eval_ctx, gen_args):
        pain_flavor = gen_args.get('pain_flavor')
        if pain_flavor in HR_PAIN_FLAVORS:
            # the SCT Inst schema's LocalInstrument2Choice offers no <Prtry>
            gen_args['local_instrument_type'] = (
                'code' if pain_flavor == HR_SCT_INST_09 else 'proprietary')
            gen_args['structured_remittance_issuer'] = True
        res = super().generate_start_payment_info_block(
            parent_node, payment_info_ident, priority, local_instrument,
            category_purpose, sequence_type, requested_date, eval_ctx,
            gen_args,
        )
        if pain_flavor in HR_PAIN_09_FLAVORS:
            payment_info = res[0]
            requested_date_node = payment_info.find('./ReqdExctnDt')
            # Remove requested date from node, before appending <Dt> tag
            requested_date_node.text = ''
            requested_date_node_date_sub = etree.SubElement(requested_date_node, 'Dt')
            requested_date_node_date_sub.text = requested_date
        return res


    def generate_address_block(self, parent_node, partner, gen_args):
        """Generate the piece of the XML corresponding to PstlAdr"""
        if gen_args.get('pain_flavor') in HR_PAIN_09_FLAVORS:
            return self._generate_structured_address_block(
                parent_node, partner, gen_args)
        if partner.country_id:
            postal_address = etree.SubElement(parent_node, 'PstlAdr')
            country = etree.SubElement(postal_address, 'Ctry')
            country.text = self._prepare_field(
                'Country', 'partner.country_id.code',
                {'partner': partner}, 2, gen_args=gen_args)
            if partner.street or partner.street2:
                adrline1 = etree.SubElement(postal_address, 'AdrLine')
                adrline1.text = ', '.join(
                    filter(None, [partner.street, partner.street2])
                )
                if partner.zip and partner.city:
                    adrline2 = etree.SubElement(postal_address, 'AdrLine')
                    adrline2.text = ' '.join([partner.zip, partner.city])
        return True

    def _generate_structured_address_block(self, parent_node, partner, gen_args):
        """HR XSD pain.001.001.09hr requires a structured PstlAdr; <AdrLine>
        is forbidden. <TwnNm> and <Ctry> are the only mandatory
        sub-elements, so skip the whole block rather than emit one the bank
        would reject when either is missing."""
        if not (partner.country_id and partner.city):
            return True
        street_name = partner.street_name
        street_number = partner.street_number
        if not street_name and not street_number and partner.street:
            split = hr_street_split(partner.street)
            street_name = split['street_name']
            street_number = split['street_number']
        postal_address = etree.SubElement(parent_node, 'PstlAdr')
        if street_name:
            strtnm = etree.SubElement(postal_address, 'StrtNm')
            strtnm.text = self._prepare_field(
                'Street Name', 'street_name',
                {'street_name': street_name}, 70, gen_args=gen_args)
        if street_number:
            bldgnb = etree.SubElement(postal_address, 'BldgNb')
            bldgnb.text = self._prepare_field(
                'Building Number', 'street_number',
                {'street_number': street_number}, 16, gen_args=gen_args)
        if partner.zip:
            pstcd = etree.SubElement(postal_address, 'PstCd')
            pstcd.text = self._prepare_field(
                'Post Code', 'partner.zip', {'partner': partner}, 16,
                gen_args=gen_args)
        twnnm = etree.SubElement(postal_address, 'TwnNm')
        twnnm.text = self._prepare_field(
            'Town Name', 'partner.city', {'partner': partner}, 35,
            gen_args=gen_args)
        country = etree.SubElement(postal_address, 'Ctry')
        country.text = self._prepare_field(
            'Country', 'partner.country_id.code', {'partner': partner}, 2,
            gen_args=gen_args)
        return True

    def generate_party_id(self, parent_node, party_type, partner):
        """Dbtr/Id/OrgId/Othr/Id = OIB, required by HR banks for
        pain.001.001.09hr even though the XSD itself marks it optional."""
        res = super().generate_party_id(parent_node, party_type, partner)
        pain_flavor = self.payment_mode_id.payment_method_id.pain_version
        if (
            pain_flavor in HR_PAIN_09_FLAVORS
            and party_type == 'Dbtr'
            and partner.company_registry
        ):
            party_id = etree.SubElement(parent_node, 'Id')
            org_id = etree.SubElement(party_id, 'OrgId')
            othr = etree.SubElement(org_id, 'Othr')
            othr_id = etree.SubElement(othr, 'Id')
            othr_id.text = partner.company_registry[:35]
        return res

    def generate_remittance_info_block(self, parent_node, line, gen_args):
        communication_type = line.payment_line_ids[:1].communication_type
        if communication_type == "HR ref":
            gen_args['structured_remittance_issuer'] = True
        super().generate_remittance_info_block(parent_node, line, gen_args)
