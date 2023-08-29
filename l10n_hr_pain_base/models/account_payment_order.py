# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, _
from lxml import etree
from datetime import datetime


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    def _get_file_prefix(self):
        self.ensure_one()
        number = 1  # TODO: this is hardcoded :(
        date_today = datetime.today().strftime('%Y%m%d')
        return 'UN.' + date_today + '.' + str(number).zfill(4) + '.'

    def compute_sepa_final_hook(self, sepa):
        self.ensure_one()
        sepa = super().compute_sepa_final_hook(sepa)
        pain_flavor = self.payment_mode_id.payment_method_id.pain_version
        if pain_flavor and 'scthr' in pain_flavor:
            sepa = True
        return sepa

    def generate_pain_nsmap(self):
        self.ensure_one()
        nsmap = super().generate_pain_nsmap()
        pain_flavor = self.payment_mode_id.payment_method_id.pain_version
        # In Croatia it is scthr:pain.001.001.03
        # <Document xmlns="="urn:iso:std:iso:20022:tech:xsd:scthr:pain.001.001.03">
        if pain_flavor == 'scthr:pain.001.001.03':
            nsmap[None] = 'urn:iso:std:iso:20022:tech:xsd:%s' % pain_flavor
        return nsmap

    def generate_pain_attrib(self):
        self.ensure_one()
        pain_flavor = self.payment_mode_id.payment_method_id.pain_version
        if pain_flavor == 'scthr:pain.001.001.03':
            pass
        else:
            return super().generate_pain_attrib()

    def generate_group_header_block(self, parent_node, gen_args):
        group_header, nb_of_transactions, control_sum = super().generate_group_header_block(parent_node, gen_args)
        if gen_args.get('pain_flavor') == 'scthr:pain.001.001.03':
            msg_id = group_header.find('.//MsgId')
            if msg_id is not None:
                prefix = gen_args['file_prefix'].replace('.', '')
                msg_id.text = prefix + msg_id.text
        return group_header, nb_of_transactions, control_sum

    def generate_start_payment_info_block(self, parent_node, payment_info_ident, priority, local_instrument,
                                          category_purpose, sequence_type, requested_date, eval_ctx, gen_args):
        if gen_args.get('pain_flavor') == 'scthr:pain.001.001.03':
            gen_args['local_instrument_type'] = 'proprietary'
            gen_args['structured_remittance_issuer'] = True
        return super().generate_start_payment_info_block(
            parent_node, payment_info_ident, priority, local_instrument,
            category_purpose, sequence_type, requested_date, eval_ctx,
            gen_args,
        )

    def generate_address_block(self, parent_node, partner, gen_args):
        """Generate the piece of the XML corresponding to PstlAdr"""
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

    def generate_remittance_info_block(self, parent_node, line, gen_args):
        if line.communication_type == "HR ref":
            gen_args['structured_remittance_issuer'] = True
        super().generate_remittance_info_block(parent_node, line, gen_args)
