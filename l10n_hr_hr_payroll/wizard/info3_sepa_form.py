from odoo import models, fields, api, _
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from . import salary_data_common as sdc
from unidecode import unidecode
from lxml import etree
import base64
from odoo.exceptions import ValidationError
from odoo import tools
import logging

logger = logging.getLogger(__name__)

NO_MODEL = 'HR99' #kada nije definiran model i poziv na broj
SALARY_REFERENCE = 'HR6940002'
CATEGORY_PURPOSE_CODE = 'SALA' #only for salary payment


class Info3SepaForm(models.TransientModel):
    _name = 'info3.sepa.form'
    _order = 'create_date desc'
    _description = 'Forma za generiranje SEPA datoteke u modulu Obračun plaća'

    _charge_bearer_sel = [
        ('SLEV', 'Following Service Level'),
        ('SHAR', 'Shared'),
        ('CRED', 'Borne by Creditor'),
        ('DEBT', 'Borne by Debtor'),
    ]

    _charge_bearer_help = "Following service level : transaction charges are to be "\
            "applied following the rules agreed in the service level and/or "\
            "scheme (SEPA Core messages must use this). Shared : transaction "\
            "charges on the debtor side are to be borne by the debtor, "\
            "transaction charges on the creditor side are to be borne by "\
            "the creditor. Borne by creditor : all transaction charges are "\
            "to be borne by the creditor. Borne by debtor : all transaction "\
            "charges are to be borne by the debtor."

    def _get_bank_accounts_domain(self):
        company_id = self.env.company
        return [('partner_id', '=', company_id.partner_id.id)]

    payment_date = fields.Date('Datum plaćanja', required=True, default=fields.Date.context_today, help="Koristi se kao filter za odabir obračuna plaće i vrijednost ReqdExctnDt taga u xml datoteci.")
    payslip_run_ids = fields.Many2many('hr.payslip.run', 'info3_sepa_payslip_run_rel', 'sepa_id', 'run_id', 'Obračuni plaće', required=True)
    bank_account_id = fields.Many2one('res.partner.bank',string='Bankovni račun', required=True, domain=lambda s: s._get_bank_accounts_domain() )
    company_id = fields.Many2one('res.company', 'Tvrtka', default=lambda self: self.env.company, index=True)
    date = fields.Date('Datum', default=fields.Date.context_today)
    filename = fields.Char('Naziv datoteke', size=256, readonly=True)
    use_batch_booking = fields.Boolean('Koristi batch booking')
    type_of_payment = fields.Selection([('salary','Plaća'), ('other','Other payments')], 'Vrsta')
    disability_fee = fields.Boolean('Naknada za invaliditet')
    file_id = fields.Many2one('banking.export.sepa', 'SEPA xml datoteka', readonly=True)
    sepa_file = fields.Binary(related='file_id.sepa_file', string="Datoteka", readonly=True)
    state = fields.Selection([
            ('create', 'Kreiraj'),
            ('finish', 'Završi'),
            ], 'Stanje', default='create', readonly=True)
    payment_order_ids = fields.Many2many('account.payment.order', 'wiz_sepa_payorders_rel', 'wizard_id', 'payment_order_id', 'Nalozi za plaćanje', readonly=True)
    charge_bearer = fields.Selection(_charge_bearer_sel, 'Troškovna opcija', default='SLEV', required=True, help=_charge_bearer_help)

    joppd_num = fields.Char('JOPPD', compute='_compute_joppd_num')

    @api.depends('payment_date')
    def _compute_joppd_num(self):
        self.joppd_num = self.payment_date and self.env['hr.joppd.form'].get_joppd_num(self.payment_date) or ''

    @api.onchange('payslip_run_ids')
    def onchange_payslip_runs(self):
        if self.payslip_run_ids:
            bank_accounts = self.payslip_run_ids.mapped('bank_account_id')
            self.bank_account_id = bank_accounts and bank_accounts[0]

    #get data for SEPA generate NEW WAY
    def get_data(self):
        line_list = []
        suma = 0      
        payment_type = self.type_of_payment
        batch_booking = self.use_batch_booking
        payslip_run_ids = [run.id for run in self.payslip_run_ids]
        payment_date = self.payment_date
        disability_fee = self.disability_fee
        pain_type = self.company_id.i3_config_sepa_pain_type or 'pain.001.001.09'
        if payment_type == False:
            payment_type = 'all'
        
        res = sdc.generate_309(self, suma, payment_type, disability_fee)
        for el in res:
            line_list.append({
                'nazbanprim': el['nazbanprim'],
                'nazivprim': el['nazivprim'],
                'opis': el['opis'],
                'primatelj': el['primatelj'],
                'ispl': el['ispl'],
                'modelprim': el['modelprim'],
                'modelplat': el['modelplat'],
                'ibanprim': el['ibanprim'],
                'bic': el['bic'],
                'oib': el['oib'] if 'oib' in el else None,
                'protbanprim': el['protbanprim'] if 'protbanprim' in el else None,
                'protiban': el['protiban'] if 'protiban' in el else None,
                'sum': el['sum'] if 'sum' in el else 0.0,
            })
        context = {}
        context['lines'] = line_list       
        context['payment_type'] = payment_type
        context['pain_type'] = pain_type

        view_ref = self.env['ir.model.data']._xmlid_lookup('l10n_hr_hr_payroll.view_info3_sepa_line_help')
        view_id = view_ref and view_ref[1] or False,
        return {
            'name': _(u'Uređivanje SEPA stavki'),
            'type': 'ir.actions.act_window',
            'res_model': 'info3.sepa.line.help',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context
        }

    def create_sepa(self, list_dict, manual_edit):
        """
        Creates the SEPA Credit Transfer file. That's the important code !
        """
        context = self.env.context.copy()
        payment_type = context.get('payment_type')
        sepa_export = self.browse(context.get('active_id'))

        run_ids = sepa_export.payslip_run_ids
        run = run_ids[0]
        requested_date = datetime.strftime(sepa_export.payment_date, DEFAULT_SERVER_DATE_FORMAT)
        #get bank account for debtor - company which pays salaries
        iban = sepa_export.bank_account_id.acc_number
        bic = sepa_export.bank_account_id.bank_id.bic
        bic = bic.replace(" ", "")

        use_end_to_end =  not(self.company_id.i3_config_use_end_to_end)

        if payment_type == 'salary':
            sepa_export.use_batch_booking = True
        pain_flavor = context.get('pain_type')
        category_purpose_code = 'SALA'
        convert_to_ascii = True

        if pain_flavor == 'pain.001.001.02':
            bic_xml_tag = 'BIC'
            name_maxsize = 70
            root_xml_tag = 'pain.001.001.02'
        elif pain_flavor == 'pain.001.001.03':
            bic_xml_tag = 'BIC'
            # size 70 -> 140 for <Nm> with pain.001.001.03
            # BUT the European Payment Council, in the document
            # "SEPA Credit Transfer Scheme Customer-to-bank
            # Implementation guidelines" v6.0 available on
            # http://www.europeanpaymentscouncil.eu/knowledge_bank.cfm
            # says that 'Nm' should be limited to 70
            # so we follow the "European Payment Council"category_purpose_code
            # and we put 70 and not 140
            name_maxsize = 70
            root_xml_tag = 'CstmrCdtTrfInitn'
        elif pain_flavor == 'pain.001.001.04':
            bic_xml_tag = 'BICFI'
            name_maxsize = 140
            root_xml_tag = 'CstmrCdtTrfInitn'
        elif pain_flavor == 'pain.001.001.05':
            bic_xml_tag = 'BICFI'
            name_maxsize = 140
            root_xml_tag = 'CstmrCdtTrfInitn'
        elif pain_flavor == 'pain.001.001.09':
            bic_xml_tag = 'BICFI'
            name_maxsize = 140
            root_xml_tag = 'CstmrCdtTrfInitn'
        else:
            raise ValidationError(
                _("Payment Type Code '%s' is not supported. The only "
                    "Payment Type Codes supported for SEPA Credit Transfers "
                    "are 'pain.001.001.02', 'pain.001.001.03', "
                    "'pain.001.001.04', 'pain.001.001.05'"
                    "and pain.001.001.09.")
                % pain_flavor)

        gen_args = {
            'bic_xml_tag': bic_xml_tag,
            'name_maxsize': name_maxsize,
            'convert_to_ascii': convert_to_ascii,
            'payment_method': 'TRF',
            'pain_flavor': pain_flavor,
            'sepa_export': sepa_export,
            'file_obj': self.env['banking.export.sepa'],
            'pain_xsd_file':
            'l10n_hr_pain_credit_transfer/data/scthr:%s.xsd'
            % pain_flavor,
            'category_purpose_code': category_purpose_code,
            'payslip_run_ids': run_ids.ids
        }
        pain_ns = {
            #'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            None: 'urn:iso:std:iso:20022:tech:xsd:scthr:%s' % pain_flavor,
            }

        xml_root = etree.Element('Document', nsmap=pain_ns)
        pain_root = etree.SubElement(xml_root, root_xml_tag)
        pain_03_to_09 = \
            ['pain.001.001.03', 'pain.001.001.04', 'pain.001.001.05','pain.001.001.09']

        # A. Group header
        group_header_1_0, nb_of_transactions_1_6, control_sum_1_7 = \
            self.generate_group_header_block(pain_root, gen_args)

        transactions_count_1_6 = 0
        total_amount = 0.0
        amount_control_sum_1_7 = 0.0

        lines = []
        diction = {}
        suma = 0
        diction = {}

        #data for sepa generation        
        res = list_dict
        line_number = ''
        debtor_data = sdc.generate_301(self, run, line_number, suma)

        context.update({'debtor_oib': debtor_data['debtor']['oib']})
            
        #TODO: rijesiti grupiranje, obavezno ako ima vise valuta
        reference = 'Grupa 1'
        priority = False
        debtor_name = debtor_data['debtor']['name']
        city = debtor_data['debtor']['address']
        country_code = debtor_data['debtor']['country_code']
        street = debtor_data['debtor']['street']
        zip_code = debtor_data['debtor']['zip_code']
        currency_name = debtor_data['debtor']['currency'] #TODO: get currency from line not only debtor
        payment_info_2_0, nb_of_transactions_2_4, control_sum_2_5 = \
            self.generate_start_payment_info_block(
                pain_root,
                reference,
                priority, False, False, requested_date, {
                    'sepa_export': sepa_export,
                    'priority': priority,
                    'requested_date': requested_date,
                }, gen_args)
                 
        self.with_context(**context).generate_party_block(payment_info_2_0, 'Dbtr', 'B', debtor_name, iban, bic, city, country_code, street, zip_code, currency_name,
                                    payment_type, {'sepa_export': sepa_export}, gen_args)

        transactions_count_2_4 = 0
        amount_control_sum_2_5 = 0.0

        #iterate through all result, assumption that all element in result have same currency
        i = 1
        for elem in res:

            transactions_count_1_6 += 1
            transactions_count_2_4 += 1
            # C. Credit Transfer Transaction Info
            credit_transfer_transaction_info_2_27 = etree.SubElement(
                payment_info_2_0, 'CdtTrfTxInf')
            payment_identification_2_28 = etree.SubElement(
                credit_transfer_transaction_info_2_27, 'PmtId')
            instruction_identification = etree.SubElement(
                payment_identification_2_28, 'InstrId')

            instruction_identification.text = "Nalog " + str(i)
            end2end_identification_2_30 = etree.SubElement(
                payment_identification_2_28, 'EndToEndId')
            
            end2end_identification_2_30.text = elem['modelplat']
      
            amount_2_42 = etree.SubElement(
                credit_transfer_transaction_info_2_27, 'Amt')
            instructed_amount_2_43 = etree.SubElement(
                amount_2_42, 'InstdAmt', Ccy=currency_name)
            instructed_amount_2_43.text = '%.2f' % elem['ispl'] 
            amount_control_sum_1_7 += elem['ispl']
            amount_control_sum_2_5 += elem['ispl']

            # check if all line have IBAN and BIC defined
            if not elem['ibanprim']:
                raise ValidationError(_("Bankovni račun partnera '%s' s opisom '%s' mora imati upisan IBAN.") % (elem['primatelj'], elem['opis'])) 
            if not elem['bic']:
                raise ValidationError(_("Bankovni račun partnera '%s' s opisom '%s' mora imati upisan BIC.") % (elem['primatelj'], elem['opis']))             
            #delete empty spaces from bic
            bic = elem['bic'].replace(" ", "")
            naziv = elem['primatelj'] if elem['primatelj'] else 'missing normal'
            ibanprim = elem['ibanprim']
            self.generate_party_block(
                credit_transfer_transaction_info_2_27, 'Cdtr', 'C', naziv, ibanprim, bic, 
                city, country_code, street, zip_code, currency_name,payment_type, {'line': elem}, gen_args)
            elem['state'] = '' #empty because not relevant for salary payment, but need for function to work
            elem['struct_communication_type'] = ''#empty because not relevant for salary payment, but need for function to work
            
            model = elem['modelprim']
            self.generate_remittance_info_block(credit_transfer_transaction_info_2_27, elem, model, gen_args)
            
            if pain_flavor in pain_03_to_09:
                nb_of_transactions_2_4.text = str(transactions_count_2_4)
                control_sum_2_5.text = '%.2f' % amount_control_sum_2_5
            i+=1

        if pain_flavor in pain_03_to_09:
            nb_of_transactions_1_6.text = str(transactions_count_1_6)
            control_sum_1_7.text = '%.2f' % amount_control_sum_1_7
        else:
            nb_of_transactions_1_6.text = str(transactions_count_1_6)
            control_sum_1_7.text = '%.2f' % amount_control_sum_1_7
        
        return self.finalize_sepa_file_creation(xml_root, total_amount, transactions_count_1_6, gen_args, list_dict, manual_edit)

    #function generates header for sepa, called once
    def generate_group_header_block(self, parent_node, gen_args):
        number = 1
        group_header_1_0 = etree.SubElement(parent_node, 'GrpHdr')

        #gets file with same date, if exist increase number
        date_today = datetime.today()       
        sepa_obj = self.env['info3.sepa']

        ids = sepa_obj.search([('date', '=', date_today.date())])
        if len(ids)> 0:
            for i in ids:
                number += 1

        #generates reference for header
        reference = 'UN' + date_today.strftime('%Y') + date_today.strftime('%m') + date_today.strftime('%d') + str(number).zfill(4)
        message_identification_1_1 = etree.SubElement(
            group_header_1_0, 'MsgId')
        value = unidecode(reference)
        unallowed_ascii_chars = [
            '"', '#', '$', '%', '&', '*', ';', '<', '>', '=', '@',
            '[', ']', '^', '_', '`', '{', '}', '|', '~', '\\', '!']
        for unallowed_ascii_char in unallowed_ascii_chars:
            value = value.replace(unallowed_ascii_char, '-')   
        message_identification_1_1.text = value

        #creation date and time
        creation_date_time_1_2 = etree.SubElement(group_header_1_0, 'CreDtTm')
        creation_date_time_1_2.text = datetime.strftime(
            datetime.today(), '%Y-%m-%dT%H:%M:%S')
      
        #add total number of transaction - sum of individual transaction
        nb_of_transactions_1_6 = etree.SubElement(
            group_header_1_0, 'NbOfTxs')

        #sum of all amount no matter of currency
        control_sum_1_7 = etree.SubElement(group_header_1_0, 'CtrlSum')     
        self.generate_initiating_party_block(group_header_1_0, gen_args)
        return group_header_1_0, nb_of_transactions_1_6, control_sum_1_7

    #sets data for debtor, in our case company
    def generate_initiating_party_block(self, parent_node, gen_args):
        user = self.env.user
        for us in user:
            my_company_name = us.company_id.name
        initiating_party_1_8 = etree.SubElement(parent_node, 'InitgPty')
        initiating_party_name = etree.SubElement(initiating_party_1_8, 'Nm')
        initiating_party_name.text = my_company_name
        return True

    def generate_start_payment_info_block(
            self, parent_node, payment_info_ident,
            priority, local_instrument, sequence_type, requested_date,
            eval_ctx, gen_args):
        payment_info_2_0 = etree.SubElement(parent_node, 'PmtInf')
        payment_info_identification_2_1 = etree.SubElement(
            payment_info_2_0, 'PmtInfId')
        payment_info_identification_2_1.text = payment_info_ident
        payment_method_2_2 = etree.SubElement(payment_info_2_0, 'PmtMtd')
        payment_method_2_2.text = gen_args['payment_method']
        if gen_args.get('pain_flavor') != 'pain.001.001.02':
            batch_booking_2_3 = etree.SubElement(payment_info_2_0, 'BtchBookg')
            batch_booking_2_3.text = \
                str(gen_args['sepa_export'].use_batch_booking).lower()
        # The "SEPA Customer-to-bank
        # Implementation guidelines" for SCT and SDD says that control sum
        # and nb_of_transactions should be present
        # at both "group header" level and "payment info" level
            nb_of_transactions_2_4 = etree.SubElement(
                payment_info_2_0, 'NbOfTxs')
            control_sum_2_5 = etree.SubElement(payment_info_2_0, 'CtrlSum')
        payment_type_info_2_6 = etree.SubElement(
            payment_info_2_0, 'PmtTpInf')
        if priority:
            instruction_priority_2_7 = etree.SubElement(
                payment_type_info_2_6, 'InstrPrty')
            instruction_priority_2_7.text = priority
        service_level_2_8 = etree.SubElement(
            payment_type_info_2_6, 'SvcLvl')
        service_level_code_2_9 = etree.SubElement(service_level_2_8, 'Cd')
        service_level_code_2_9.text = 'SEPA'
        if local_instrument:
            local_instrument_2_11 = etree.SubElement(
                payment_type_info_2_6, 'LclInstrm')
            local_instr_code_2_12 = etree.SubElement(
                local_instrument_2_11, 'Cd')
            local_instr_code_2_12.text = local_instrument
        if sequence_type:
            sequence_type_2_14 = etree.SubElement(
                payment_type_info_2_6, 'SeqTp')
            sequence_type_2_14.text = sequence_type
        # Set CtgyPurp for pain.001.001.002 and pain.001.001.003
        if gen_args.get('pain_flavor') == 'pain.001.001.02' or gen_args.get('pain_flavor') == 'pain.001.001.03' or gen_args.get('pain_flavor') == 'pain.001.001.04' or gen_args.get('pain_flavor') == 'pain.001.001.05':
            category_purpose_2_14 = etree.SubElement(
                payment_type_info_2_6, 'CtgyPurp')
            category_purpose_code_2_14 = etree.SubElement(
                category_purpose_2_14, 'Cd')
            category_purpose_code_2_14.text = gen_args.get('category_purpose_code')
        if gen_args['payment_method'] == 'DD':
            request_date_tag = 'ReqdColltnDt'
        else:
            request_date_tag = 'ReqdExctnDt'
        requested_date_2_17 = etree.SubElement(
            payment_info_2_0, request_date_tag)
        if gen_args.get('pain_flavor') == 'pain.001.001.09':
            requested_date_2_18 = etree.SubElement(requested_date_2_17, 'Dt')
            requested_date_2_18.text = requested_date
        else:
            requested_date_2_17.text = requested_date
        return payment_info_2_0, nb_of_transactions_2_4, control_sum_2_5

    def generate_party_block(self, parent_node, party_type, order, name, iban, bic, city, country_code, street, zip_code, currency_name, type, eval_ctx, gen_args):
        '''Generate the piece of the XML file corresponding to Name+IBAN+BIC
        This code is mutualized between TRF and DD'''
        assert order in ('B', 'C'), "Order can be 'B' or 'C'"
        if party_type == 'Cdtr':
            party_type_label = 'Creditor'
        elif party_type == 'Dbtr':
            party_type_label = 'Debtor'
        #problem with latin characters
        name = name.encode('windows-1250', errors='ignore').decode('windows-1250')
        party_name = name #if name else 'doprinos' #OVO OBAVEZNO OBRISATI
        viban = iban.replace(' ', '')
        # At C level, the order is : BIC, Name, IBAN
        # At B level, the order is : Name, IBAN, BIC
        if order == 'B':
            gen_args['initiating_party_country_code'] = viban[0:2]
        elif order == 'C':
            self.generate_party_agent(
                parent_node, party_type, party_type_label,
                order, party_name, viban, bic,
                eval_ctx, gen_args)
        party = etree.SubElement(parent_node, party_type)
        party_nm = etree.SubElement(party, 'Nm')
        party_nm.text = party_name
        party_account = etree.SubElement(
            parent_node, '%sAcct' % party_type)
        party_account_id = etree.SubElement(party_account, 'Id')
        if party_type == 'Dbtr':       
            party_pstl = etree.SubElement(party, 'PstlAdr')     
            if gen_args.get('pain_flavor') == 'pain.001.001.09':       
                if street:
                    party_strtnm = etree.SubElement(party_pstl, 'StrtNm')
                    party_strtnm.text = street
                if zip_code:
                    party_pstcd = etree.SubElement(party_pstl, 'PstCd')
                    party_pstcd.text = zip_code
                party_twnnm = etree.SubElement(party_pstl, 'TwnNm')
                party_twnnm.text = city
                party_ctry = etree.SubElement(party_pstl, 'Ctry')
                party_ctry.text = country_code
            else:
                party_addr = etree.SubElement(party_pstl, 'AdrLine')
                party_addr.text = city
            if type == 'salary':
                oib = self.env.context.get('debtor_oib')
                party_id = etree.SubElement(party, 'Id')
                party_org_id = etree.SubElement(party_id, 'OrgId')
                party_other = etree.SubElement(party_org_id, 'Othr')
                party_other_id = etree.SubElement(party_other, 'Id')
                party_other_id.text = oib
            party_ccy = etree.SubElement(party_account, 'Ccy')
            party_ccy.text = currency_name

        party_account_iban = etree.SubElement(
            party_account_id, 'IBAN')
        party_account_iban.text = viban or ''
        if order == 'B':
            self.generate_party_agent(
                parent_node, party_type, party_type_label,
                order, party_name, viban, bic,
                eval_ctx, gen_args)
        return True

    def generate_party_agent(
            self, parent_node, party_type, party_type_label,
            order, party_name, iban, bic, eval_ctx, gen_args):
        '''Generate the piece of the XML file corresponding to BIC
        This code is mutualized between TRF and DD'''
        context = self.env.context
        assert order in ('B', 'C'), "Order can be 'B' or 'C'"
        try:
            party_agent = etree.SubElement(parent_node, '%sAgt' % party_type)
            party_agent_institution = etree.SubElement(
                party_agent, 'FinInstnId')
            party_agent_bic = etree.SubElement(
                party_agent_institution, gen_args.get('bic_xml_tag'))
            party_agent_bic.text = bic
            payment_type = context.get('payment_type') == 'salary'
            if party_type == 'Dbtr' and payment_type:
                oib = context.get('debtor_oib')
                party_ultm_debtr = etree.SubElement(parent_node,'UltmtDbtr')
                party_ultm_debtr_name = etree.SubElement(party_ultm_debtr,'Nm')
                party_ultm_debtr_name.text = party_name
                party_id = etree.SubElement(party_ultm_debtr,'Id')
                party_org_id = etree.SubElement(party_id,'OrgId')
                party_other = etree.SubElement(party_org_id,'Othr')
                party_other_id = etree.SubElement(party_other,'Id')
                party_other_id.text = oib
        except Exception as e:
            if order == 'C':
                if iban[0:2] != gen_args['initiating_party_country_code']:
                    raise ValidationError(_("Bankovni račun s IBAN-om '%s' partnera '%s' mora imati upisan BIC jer je riječ o inozemnom plaćanju.") % (iban, party_name))
            if order == 'B' or (
                    order == 'C' and gen_args['payment_method'] == 'DD'):
                party_agent = etree.SubElement(
                    parent_node, '%sAgt' % party_type)
                party_agent_institution = etree.SubElement(
                    party_agent, 'FinInstnId')
                party_agent_other = etree.SubElement(
                    party_agent_institution, 'Othr')
                party_agent_other_identification = etree.SubElement(
                    party_agent_other, 'Id')
                party_agent_other_identification.text = 'NOTPROVIDED'
            # for Credit Transfers, in the 'C' block, if BIC is not provided,
            # we should not put the 'Creditor Agent' block at all,
            # as per the guidelines of the EPC
        return True

    def generate_remittance_info_block(self, parent_node, line, communication_str, gen_args):
        remittance_info_2_91 = etree.SubElement(
            parent_node, 'RmtInf')
        if line['state'] == 'normal':
            remittance_info_unstructured_2_99 = etree.SubElement(
                remittance_info_2_91, 'Ustrd')
            remittance_info_unstructured_2_99.text = \
                self._prepare_field(
                    'Remittance Unstructured Information',
                    communication_str, {'line': line}, 140,
                    gen_args=gen_args)
        else:
            line['opis'] = line['opis'] or ''
            opis = line['opis'].encode('windows-1250', errors='ignore').decode('windows-1250')
            remittance_info_structured_2_100 = etree.SubElement(
                remittance_info_2_91, 'Strd')
            creditor_ref_information_2_120 = etree.SubElement(
                remittance_info_structured_2_100, 'CdtrRefInf')
            creditor_addt = etree.SubElement(
                remittance_info_structured_2_100, 'AddtlRmtInf')
            creditor_addt.text = opis
            if gen_args.get('pain_flavor') == 'pain.001.001.02':
                creditor_ref_info_type_2_121 = etree.SubElement(
                    creditor_ref_information_2_120, 'CdtrRefTp')
                creditor_ref_info_type_code_2_123 = etree.SubElement(
                    creditor_ref_info_type_2_121, 'Cd')
                creditor_ref_info_type_issuer_2_125 = etree.SubElement(
                    creditor_ref_info_type_2_121, 'Issr')
                creditor_reference_2_126 = etree.SubElement(
                    creditor_ref_information_2_120, 'CdtrRef')
            else:
                creditor_ref_info_type_2_121 = etree.SubElement(
                    creditor_ref_information_2_120, 'Tp')
                creditor_ref_info_type_or_2_122 = etree.SubElement(
                    creditor_ref_info_type_2_121, 'CdOrPrtry')

                creditor_ref_info_type_code_2_123 = etree.SubElement(
                    creditor_ref_info_type_or_2_122, 'Cd')
                creditor_reference_2_126 = etree.SubElement(
                    creditor_ref_information_2_120, 'Ref')
            
            creditor_ref_info_type_code_2_123.text = 'SCOR'
            creditor_reference_2_126.text = communication_str or ''
        return True

    def _validate_xml(self, xml_string, gen_args):
        xsd_etree_obj = etree.parse(tools.file_open(gen_args['pain_xsd_file']))
        official_pain_schema = etree.XMLSchema(xsd_etree_obj)

        try:
            root_to_validate = etree.fromstring(xml_string)
            official_pain_schema.assertValid(root_to_validate)
        except Exception as e:
            logger.warning("The XML file is invalid against the XML Schema Definition")
            logger.warning(xml_string)
            logger.warning(e)
            raise ValidationError(
                _("The generated XML file is not valid against the official "
                    "XML Schema Definition. The generated XML file and the "
                    "full error have been written in the server logs. Here "
                    "is the error, which may give you an idea on the cause "
                    "of the problem : %s")
                % str(e))
        return True


    def finalize_sepa_file_creation(self, xml_root, total_amount, transactions_count, gen_args, list_dict, manual_edit):
        xml_string = etree.tostring(xml_root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        self._validate_xml(xml_string, gen_args)
        #AFTER VALIDATION REPLACEMENT: problem with adding scthr to xmlns
        xml_string = xml_string.replace("urn:iso:std:iso:20022:tech:xsd:pain.001.001.03".encode('utf-8'), "urn:iso:std:iso:20022:tech:xsd:scthr:pain.001.001.03".encode('utf-8'))
        xml_string = xml_string.replace("urn:iso:std:iso:20022:tech:xsd:pain.001.001.09".encode('utf-8'), "urn:iso:std:iso:20022:tech:xsd:scthr:pain.001.001.09".encode('utf-8'))
        date_today = datetime.today()       
        sepa_ids = self.env['info3.sepa'].search([('date', '=', datetime.today())])
        number = len(sepa_ids) + 1
        #generates reference for header
        ref = 'UN' + date_today.strftime('%Y') + date_today.strftime('%m') + date_today.strftime('%d') + str(number).zfill(4) + '.xml'
        

        gen_args['sepa_export'].filename = ref
        file_id = gen_args['file_obj'].create(
            self._prepare_export_sepa(total_amount, transactions_count, xml_string, gen_args)
        )
          
        sepa = self.env['info3.sepa']
        lines = []
        for line in list_dict:
            lines.append((0, 0, {
                'nazbanprim': line['nazbanprim'],
                'nazivprim': line['nazivprim'],
                'opis': line['opis'],
                'primatelj': line['primatelj'],
                'ispl': line['ispl'],
                'modelprim': line['modelprim'],
                'ibanprim': line['ibanprim'],
                'bic': line['bic'],
                'oib': line['company_registry'] if 'company_registry' in line else None,
                'protbanprim': line['protbanprim'] if 'protbanprim' in line else None,
                'protiban': line['protiban'] if 'protiban' in line else None,
                'sum': line['sum'] if 'sum' in line else 0.0,
            })) 

        sepa_id = sepa.create({
            'lines': lines,
            'name': ref,
            'date': datetime.strftime(datetime.today(),'%Y-%m-%d'),
            'file_id': file_id.id,
            'filename': ref,
            'payslip_run_ids': [(4, run_id) for run_id in gen_args['payslip_run_ids']],
            'user_edit': manual_edit,
        })
        
        gen_args['sepa_export'].write({
                'file_id': file_id.id,
                'state': 'finish',
                'filename': ref
            })
        
        return True

    def _prepare_export_sepa(self, total_amount, transactions_count, xml_string, gen_args):
        return {
            'batch_booking': gen_args['sepa_export'].use_batch_booking,
            'charge_bearer': gen_args['sepa_export'].charge_bearer,
            'total_amount': total_amount,
            'nb_transactions': transactions_count,           
            'sepa_file': base64.encodebytes(xml_string),
            'filename': gen_args['sepa_export'].filename,
            'payment_order_ids': [(
                6, 0, [x.id for x in gen_args['sepa_export'].payment_order_ids]
            )],
        }


class Info3SepaLineHelp(models.TransientModel):
    _name = 'info3.sepa.line.help'
    _description = 'Pomoćni model za prikaz i uređivanje stavki SEPE na formi'
    
    lines = fields.One2many('info3.sepa.line', 'sepa_line_id', 'lines')
    manual_edit = fields.Boolean('Ručno uređivano', default=False, readonly=True)
    number_of_created_lines = fields.Integer('Broj generiranih stavki', readonly=True)

    @api.onchange('lines')
    def onchange_sepa_lines(self):
        """
        Update manual edit flag if lines are deleted or edited.
        """
        if not self.manual_edit:
            manual_edit = False
            if len(self.lines) != self.number_of_created_lines:
                manual_edit = True
            for line in self.lines:
                if line.user_edit:
                    manual_edit = True
            self.manual_edit = manual_edit
    
    @api.model
    def default_get(self, fields):
        """
        Get lines from previous step to enable edit.
        """
        data = super(Info3SepaLineHelp, self).default_get(fields)
        lines = self.env.context.get('lines')
        data.update({
            'lines': [(0, 0, line) for line in lines],
            'number_of_created_lines': len(lines),
        })
        return data

    def create_sepa(self):
        list_dict = []
        for line in self.lines:
            list_dict.append({
                'nazbanprim': line['nazbanprim'],
                'nazivprim': line['nazivprim'],
                'opis': line['opis'],
                'primatelj': line['primatelj'],
                'ispl': line['ispl'],
                'modelprim': line['modelprim'],
                'modelplat': line['modelplat'],
                'ibanprim': line['ibanprim'],
                'bic': line['bic'],
                'oib': line['company_registry'] if 'company_registry' in line else None,
                'protbanprim': line['protbanprim'] if 'protbanprim' in line else None,
                'protiban': line['protiban'] if 'protiban' in line else None,
                'sum': line['sum'] if 'sum' in line else 0.0,
            })
        sepa_obj = self.env["info3.sepa.form"]
        sepa_obj.create_sepa(list_dict, self.manual_edit)
        action = {
            'name': _(u'SEPA datoteka'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form,list',
            'res_model': 'info3.sepa.form',
            'res_id': self.env.context.get('active_id'),
            'target': 'new',
            }
        return action 


class Info3SepaLine(models.TransientModel):
    _name = 'info3.sepa.line'
    _description = 'Payment line for info3.sepa.line.help model'

    sepa_line_id = fields.Many2one('info3.sepa.line.help', 'Sepa id')
    nazbanprim = fields.Char('Banka primatelja', size=50)
    nazivprim = fields.Char('Naziv primatelja', size=128)
    primatelj = fields.Char('Primatelj', size=128)
    opis = fields.Char('Opis', size=140)
    ispl = fields.Float('Iznos')
    modelplat = fields.Char('modelplat', size=26, help='EndToEndId u SEPA xml datoteci')
    modelprim = fields.Char('modelprim', size=26, help='Ref u SEPA xml datoteci')
    ibanprim = fields.Char('IBAN primatelja', size=35)
    amount_sum = fields.Float('Sum amount')
    protbanprim = fields.Char('Zaštićeni račun primatelja', size=34)
    protiban = fields.Char('IBAN zaštićenog računa', size=34)
    oib = fields.Char('OIB primatelja', size=34)
    bic = fields.Char('BIC', size=34)
    user_edit = fields.Boolean('Ručno uređivano', default=False)
    sum = fields.Float('Zbroj')

    def write(self, vals):
        if 'user_edit' not in vals.keys():
            vals['user_edit']=True 
        return super(Info3SepaLine, self).write(vals)

    @api.onchange(
        'nazivprim',
        'primatelj',
        'ibanprim',
        'bic',
        'opis',
        'modelplat',
        'modelprim',
        'amount_sum',
    )
    def onchange_sepa_line(self):
        self.user_edit = True
