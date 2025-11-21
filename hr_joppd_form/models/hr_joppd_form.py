#-*- coding:utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from lxml import etree
import uuid
from odoo.modules import get_module_path
import logging
from io import BytesIO

_logger = logging.getLogger(__name__)


class HrJoppdForm(models.Model):
    _name='hr.joppd.form'
    _description = 'JOPPD form'
    _order = 'datum desc'
    
    ###########################################################################
    # A1
    _oznaka_help = "Upisuje se oznaka izvješća u obliku GG001 do GG365(366),\n"\
               "a sastoji se od kombinacije oznake zadnje dvije znamenke godine\n"\
               "i rednog broja dana u godini na koji je izvršena isplata primitka\n"\
               "ili na koji su obračunani i uplaćeni doprinosi, odnosno na koji je\n"\
               "podnesen Obrazac.\n Svaki dan u godini ima svoju oznaku te se oznaka izvješća ne može ponavljati."
    ############################################################################
    # A2
    _vrsta_sel = [('1','Izvorno izvješće'),
                  ('2','Ispravak izvješća'),
                  ('3','Dopuna izvješća'),
                  ('4','Naknada za invaliditet')]
    _vrsta_help = "Upisuje se oznaka :\n"\
                "1 kada se podnosi prvo (izvorno) izvješće, \n"\
                "2 kada se podnosi ispravak već podnesenog izvješća koje je zaprimljeno od nadležne ispostave Porezne uprave,\n"\
                "3 kada se dopunjuju podaci iskazani na izvornom izvješću. \n"\
                "Oznaka 1 pod vrstom izvješća može se upisati samo jednom za istu oznaku izvješća,\n"\
                "istog podnositelja izvješća i istog obveznika plaćanja."
    ###############################################################################################################################
    def _populate_new_stranaA(self):
        report = self.env['hr.report'].search([('code','=','JOPPD-A')])[0]
        stranaA_ids = self.env['hr.report.line'].search(['&',('report_id','=',report.id),('field_type','=','float')])
        res = []
        for a in stranaA_ids:
            res.append((0,0, {'position':a}))
        return res
    ###############################################################################################################################
    
    @api.depends('oznaka', 'vrsta')
    def _compute_display_name(self):
        for r in self:
            r.display_name = '%s-%s' %(r['oznaka'],r['vrsta'])
    
    name = fields.Char('Name')
    state = fields.Selection([
                        ('draft','Nacrt'),
                        ('add','Dopuna'),
                        ('corr','Ispravak'),
                        ('sent','Poslano'),
                        ('finish','Zaključano'),
                        ('cancel','Odustani')], 'Status', readonly=True, default='draft', copy=False)
    parent_id = fields.Many2one('hr.joppd.form','Izvorni dokument', copy=False)
    child_ids = fields.One2many('hr.joppd.form','parent_id','Verzije', copy=False)
    datum = fields.Date('Datum izvješća', default=fields.Date.context_today)
    date_from = fields.Date('Datum od', help="Početni datum razdoblja za koje se kreira JOPPD obrazac")
    date_to = fields.Date('Datum do', help="Završni datum razdoblja za koje se kreira JOPPD obrazac")
    oznaka = fields.Char('Oznaka izvješća', size=5, help=_oznaka_help)
    vrsta = fields.Selection(_vrsta_sel ,'Vrsta izvješća', required=True, help=_vrsta_help, default='1')
    stranaA_ids = fields.One2many('hr.joppd.form.a','joppd_id','Strana A', default=_populate_new_stranaA, copy=True)
    stranaB_ids = fields.One2many('hr.joppd.form.b','joppd_id','Strana B', copy=True)

    check_ids = fields.One2many('hr.joppd.form.check.line','joppd_id', 'Provjera')
    is_modified = fields.Boolean('Izvješće ručno modificirano', compute='_is_report_modified')
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                default=lambda self: self.env.company, index=True)
    number_of_employees = fields.Integer('Number of employees', compute='_get_number_of_employees')
    form_type = fields.Selection([('payroll', 'Obračun plaće'), ('travel_order', 'Putni nalog')], 'Form type', default='payroll')

    @api.depends('stranaB_ids')
    def _get_number_of_employees(self):
        for joppd in self:
            employees = []
            for line in joppd.stranaB_ids:
                if line.hr_employee_id and line.hr_employee_id.id not in employees:
                    employees.append(line.hr_employee_id.id)
            joppd.number_of_employees = len(employees)

    @api.depends('stranaB_ids')
    def _is_report_modified(self):
        """
        Form is considered modified if B side was edited, which is indicated by user_edit flag on each B side line.
        """
        b_obj = self.env['hr.joppd.form.b']
        for joppd in self:
            is_modified = False
            modified_b_ids = b_obj.search([('joppd_id', '=', joppd.id), ('user_edit', '=', True)])
            if modified_b_ids:
                is_modified = True
            joppd.is_modified = is_modified

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'oznaka' not in vals.keys():
                vals['oznaka'] = vals['datum'] and self.get_joppd_num(datetime.strptime(vals['datum'],"%Y-%m-%d")) or False
        return super(HrJoppdForm, self).create(vals_list)
    
    def unlink(self):
        """
        Override to add constrains for deletion.
        """
        for joppd in self:
            if joppd.state == 'finish':
                raise ValidationError((u'Nije moguće brisanje potvrđenog obrasca'))
            
            child = self.search([('parent_id','=',joppd.id)])
            if child:
                raise ValidationError((u'Nije moguće brisanje obrasca koji ima dopune ili izmjene. Prvo ih obrišite!'))
        return super(HrJoppdForm, self).unlink()
    
    def copy(self, default=None):
        default = dict(default or {})
        datum = datetime.now()
        default.update({
            'datum': datum,
            'oznaka': self.get_joppd_num(datum)
        })
        return super(HrJoppdForm, self).copy(default)
    
    def get_joppd_num(self, date):
        return date.strftime("%y")+date.strftime("%j")

    # # added so joppd can be edited even after being set to finish
    def button_draft_joppd(self):
        return self.write({'state':'draft'})

    def button_obrazac_finish(self):
        return self.write({'state':'finish'})
    
    def button_joppd_ispravak(self):
        new_joppd = self.copy({
            'vrsta': '2',
            'state': 'corr',
            'parent_id': self.id
        })
        stranaB = self.env['hr.joppd.form.b']
        new_B_ids = stranaB.search([('joppd_id','=', new_joppd.id)])
        new_B_ids.write({'user_edit': False})
        return self.return_new_joppd_view(new_joppd.id)
    
    def button_joppd_dopuna(self):
        new_joppd = self.copy({
            'vrsta': '3',
            'state': 'add',
            'parent_id': self.id,
            'stranaB_ids': False
        })
        stranaA = self.env['hr.joppd.form.a']
        new_A_ids = stranaA.search([('joppd_id','=', new_joppd.id)] )
        new_A_ids.write({'val': 0.00})
        return self.return_new_joppd_view(new_joppd.id)
    
    def return_new_joppd_view(self, new_joppd_id):
        view_ref = self.env['ir.model.data']._xmlid_lookup('hr_joppd_form.hr_joppd_form_form_view')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': 'JOPPD obrazac',
            'res_model': 'hr.joppd.form',
            'res_id': new_joppd_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': False,
        }
    
    def stranaB_view_all(self):
        view_ext = 'hr_joppd_form_b_tree_view'
        if self.state == 'finish':
            view_ext='hr_joppd_form_b_tree_view_locked'
        view_ref = self.env['ir.model.data']._xmlid_lookup('hr_joppd_form.%s' % view_ext)
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': 'Strana B',
            'res_model': 'hr.joppd.form.b',
            'view_mode': 'list',
            'domain':[('joppd_id','=',self.id)],
            'view_id': view_id,
            'target': 'current',
            'nodestroy': False,
        }
    
    def action_order_by_employee_name(self):
        """ Order StranaB items by employee name.
            If same employee has more than one item, keep original order by using ID as secondary key.
        """
        if len(self.stranaB_ids) == 0:
            return True
        query = f"""
            SELECT b.id
            FROM hr_joppd_form_b AS b
            JOIN hr_employee AS e ON (e.id = b.hr_employee_id)
            WHERE joppd_id = {self.id}
            ORDER BY e.last_name, e.first_name, b.id
        """
        self._cr.execute(query)
        res = self._cr.dictfetchall()
        # start from the same index as the non-sorted version
        # non-sorted version index is supposed to be handled in create method of StranaB
        index = min(self.stranaB_ids.mapped('b1'))
        for item in res:
            b = self.env['hr.joppd.form.b'].browse(item.get('id'))
            b.b1 = index
            index += 1

    def clear_joppd_B(self):
        """
        Izbrisi B stranu i napomene.
        """
        check_obj = self.env['hr.joppd.form.check.line']
        self.env.cr.execute("DELETE FROM hr_joppd_form_b WHERE joppd_id=" + str(self.id))
        check_ids = check_obj.search([('joppd_id', '=', self.id)])
        check_ids.unlink()
        return True
        
#     ###########################################################################################
#     #########        GENERIRANJE XML datoteke                               ###################
#     ###########################################################################################

    def _validate_joppd_B(self):
        city_list = []
        for b in self.stranaB_ids:
            b2 = b.b2
            b3 = b.sudo().b3
            if not b2.code and b2.name not in city_list:
                city_list.append(b2.name)
            if not b3.code and b3.name not in city_list:
                city_list.append(b3.name)
        if city_list:
            cities = '\n' + '\n'.join(city_list)
            raise UserError('Nije moguće generirati XML datoteku JOPPD obrasca jer na nekim gradovima nije upisana šifra: {0}'.format(cities))
        return True


    def action_obrazac_joppd_generate_xml(self):
        self.ensure_one()
        company = self.company_id
        
        #raise errors if mandatory fields for joppd A form are not set
        if self.stranaB_ids == [] and self.vrsta != '4':
            raise ValidationError(u'Nije moguće generiranje XML datoteke jer nema podataka na strani B')
        
        if not company.joppd_applicant_id:
            raise ValidationError('Na tvrtki nije postavljena oznaka podnositelja')

        if not company.city_id:
            raise ValidationError('Na tvrtki nije postavljen grad') #TODO get joppd city list?

        if not company.street:
            raise ValidationError('Na tvrtki nije postavljena ulica')

        if not company.company_registry:
            raise ValidationError('Na tvrtki nije postavljen OIB')

        if not company.joppd_applicant_email:
            raise ValidationError('Na tvrtki nije postavljen email podnositelja')
            
        self._validate_joppd_B()

        #get home address data
        house_address = company.street.rpartition(' ')[0] or False
        house_number = company.street.rpartition(' ')[2] or False
        
        if not house_address or not house_number:
            raise ValidationError('Adresa nije ispravno upisana. Treba biti sljedećeg formata: Naziv ulice broj')
        # else:
        #    pAdresa = self.sAdresa(Mjesto = company.city, Ulica = house_address, Broj = house_number) 
        
        #get author of joppd form
        izvjesce_sastavio = self.get_izvjesce_sastavio()

        #remove 'hr' from oib if oib contains it
        oib = company.company_registry

        #get number of employees for joppd A from
        broj_osoba = []   
        for b in self.stranaB_ids: 
            if b.hr_employee_id.id not in broj_osoba:
                broj_osoba.append(b.hr_employee_id.id)

        #get joppd A form data
        str_A = self.get_stranaA_data2()
                
        joppd_root = etree.Element('ObrazacJOPPD')
        #METAPODACI
        joppd_meta = etree.SubElement(joppd_root,'Metapodaci')
        meta_naslov = etree.SubElement(joppd_meta,'Naslov')
        meta_autor = etree.SubElement(joppd_meta,'Autor')
        meta_datum = etree.SubElement(joppd_meta,'Datum' ) #UZMI PRAVI DATUM!
        meta_format = etree.SubElement(joppd_meta,'Format')
        meta_jezik = etree.SubElement(joppd_meta,'Jezik')
        meta_identifikator = etree.SubElement(joppd_meta,'Identifikator') # UUID !!!
        meta_uskl = etree.SubElement(joppd_meta,'Uskladjenost')
        meta_tip = etree.SubElement(joppd_meta,'Tip')
        meta_adresant = etree.SubElement(joppd_meta,'Adresant')

        joppd_root.attrib['verzijaSheme']='1.1'
        joppd_root.attrib['xmlns']='http://e-porezna.porezna-uprava.hr/sheme/zahtjevi/ObrazacJOPPD/v1-1'
        joppd_meta.attrib['xmlns']='http://e-porezna.porezna-uprava.hr/sheme/Metapodaci/v2-0'
        meta_naslov.attrib['dc']='http://purl.org/dc/elements/1.1/title'
        meta_autor.attrib['dc']='http://purl.org/dc/elements/1.1/creator'
        meta_datum.attrib['dc']='http://purl.org/dc/elements/1.1/date'
        meta_format.attrib['dc']='http://purl.org/dc/elements/1.1/format'
        meta_jezik.attrib['dc']='http://purl.org/dc/elements/1.1/language'
        meta_identifikator.attrib['dc']='http://purl.org/dc/elements/1.1/identifier'
        meta_uskl.attrib['dc']='http://purl.org/dc/terms/conformsTo'
        meta_tip.attrib['dc']='http://purl.org/dc/elements/1.1/type'


        ######## PUNIM META
        meta_naslov.text=  u'Izvješće o primicima, porezu na dohodak i prirezu te doprinosima za obvezna osiguranja'
        meta_autor.text = izvjesce_sastavio['ime'] + ' ' + izvjesce_sastavio['prezime']         #get name of current user
        meta_datum.text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        meta_format.text = 'text/xml'
        meta_jezik.text = 'hr-HR'
        meta_identifikator.text = str(uuid.uuid4())
        meta_uskl.text = 'ObrazacJOPPD-v1-1'
        meta_tip.text = u'Elektronički obrazac'
        meta_adresant.text = u'Ministarstvo Financija, Porezna uprava, Zagreb'
        #############################################        
        ########STRANA A
        joppd_stranaA = etree.SubElement(joppd_root,'StranaA')
        sA_datum = etree.SubElement(joppd_stranaA,'DatumIzvjesca') 
        sA_oznaka = etree.SubElement(joppd_stranaA,'OznakaIzvjesca')
        sA_vrsta = etree.SubElement(joppd_stranaA, 'VrstaIzvjesca')
            
        sA_podnosi = etree.SubElement(joppd_stranaA, 'PodnositeljIzvjesca')
        pod_naziv = etree.SubElement(sA_podnosi,'Naziv')
        pod_adresa = etree.SubElement(sA_podnosi,'Adresa')
        adr_mjesto = etree.SubElement(pod_adresa,'Mjesto')
        adr_ulica = etree.SubElement(pod_adresa, 'Ulica')
        adr_broj = etree.SubElement(pod_adresa, 'Broj')
            
        pod_email = etree.SubElement(sA_podnosi,'Email')
        pod_oib = etree.SubElement(sA_podnosi,'OIB')
        pod_oznaka = etree.SubElement(sA_podnosi,'Oznaka')
            
        #Obveznik plaćanja nisam stavljao.. samo za drzavne... 
        sA_osoba = etree.SubElement(joppd_stranaA, 'BrojOsoba')
        sA_redaka = etree.SubElement(joppd_stranaA, 'BrojRedaka')
        #Strana A Predujam poreza
        sA_pred_por = etree.SubElement(joppd_stranaA, 'PredujamPoreza')
        PP_P1 = etree.SubElement(sA_pred_por, 'P1')
        PP_P11 = etree.SubElement(sA_pred_por, 'P11')
        PP_P12 = etree.SubElement(sA_pred_por, 'P12')
        PP_P2 = etree.SubElement(sA_pred_por, 'P2')
        PP_P3 = etree.SubElement(sA_pred_por, 'P3')
        PP_P4 = etree.SubElement(sA_pred_por, 'P4')
        PP_P5 = etree.SubElement(sA_pred_por, 'P5')
            
        #Strana Doprinosi
        sA_doprinosi = etree.SubElement(joppd_stranaA, 'Doprinosi')
        dop_GS = etree.SubElement(sA_doprinosi, 'GeneracijskaSolidarnost')
        GS_P1 = etree.SubElement(dop_GS, 'P1')
        GS_P2 = etree.SubElement(dop_GS, 'P2')
        GS_P3 = etree.SubElement(dop_GS, 'P3')
        GS_P4 = etree.SubElement(dop_GS, 'P4')
        GS_P5 = etree.SubElement(dop_GS, 'P5')
        GS_P6 = etree.SubElement(dop_GS, 'P6')
            
        dop_KS = etree.SubElement(sA_doprinosi, 'KapitaliziranaStednja')
        KS_P1 = etree.SubElement(dop_KS, 'P1')
        KS_P2 = etree.SubElement(dop_KS, 'P2')
        KS_P3 = etree.SubElement(dop_KS, 'P3')
        KS_P4 = etree.SubElement(dop_KS, 'P4')
        KS_P5 = etree.SubElement(dop_KS, 'P5')
            
        dop_ZO = etree.SubElement(sA_doprinosi, 'ZdravstvenoOsiguranje')
        ZO_P1 = etree.SubElement(dop_ZO, 'P1')
        ZO_P2 = etree.SubElement(dop_ZO, 'P2')
        ZO_P3 = etree.SubElement(dop_ZO, 'P3')
        ZO_P4 = etree.SubElement(dop_ZO, 'P4')
        ZO_P5 = etree.SubElement(dop_ZO, 'P5')
        ZO_P6 = etree.SubElement(dop_ZO, 'P6')
        ZO_P7 = etree.SubElement(dop_ZO, 'P7')
        ZO_P8 = etree.SubElement(dop_ZO, 'P8')
        ZO_P9 = etree.SubElement(dop_ZO, 'P9')
        ZO_P10= etree.SubElement(dop_ZO, 'P10')
            
        dop_ZA = etree.SubElement(sA_doprinosi, 'Zaposljavanje')
        ZA_P1 = etree.SubElement(dop_ZA, 'P1')
        ZA_P2 = etree.SubElement(dop_ZA, 'P2')
            
        sA_neopor = etree.SubElement(joppd_stranaA, 'IsplaceniNeoporeziviPrimici')
        sA_ktaMO2 = etree.SubElement(joppd_stranaA, 'KamataMO2')

        nak_INV = etree.SubElement(joppd_stranaA, 'NaknadaZaposljavanjeInvalida')
        INV_P1 = etree.SubElement(nak_INV, 'P1')
        INV_P2 = etree.SubElement(nak_INV, 'P2')
            
        sA_sastavio = etree.SubElement(joppd_stranaA, 'IzvjesceSastavio')
        sas_ime = etree.SubElement(sA_sastavio, 'Ime')
        sas_prez = etree.SubElement(sA_sastavio, 'Prezime')

            #fill xml with data
        sA_datum.text = datetime.strftime(self.datum, DEFAULT_SERVER_DATE_FORMAT)
        sA_oznaka.text = self.oznaka
        sA_vrsta.text = self.vrsta
        pod_naziv.text = company.name
        adr_mjesto.text = company.city_id.name
        adr_ulica.text = house_address
        adr_broj.text = house_number
        pod_email.text = company.joppd_applicant_email
        pod_oib.text = oib
        pod_oznaka.text = company.joppd_applicant_id
        sA_osoba.text = str(len(broj_osoba))
        sA_redaka.text = str(len(self.stranaB_ids))

        #hardcoded values
        #PredujamPoreza 
        PP_P1.text = "{0:.2f}".format(str_A['V.1'])
        PP_P11.text = "{0:.2f}".format(str_A['V.1.1'])
        PP_P12.text = "{0:.2f}".format(str_A['V.1.2'])
        PP_P2.text = "{0:.2f}".format(str_A['V.2'])
        PP_P3.text = "{0:.2f}".format(str_A['V.3'])
        PP_P4.text = "{0:.2f}".format(str_A['V.4'])
        PP_P5.text = "{0:.2f}".format(str_A['V.5'])
            
        #Strana Doprinosi
        #GeneracijskaSolidarnost
        GS_P1.text = "{0:.2f}".format(str_A['VI.1.1'])
        GS_P2.text = "{0:.2f}".format(str_A['VI.1.2'])
        GS_P3.text = "{0:.2f}".format(str_A['VI.1.3'])
        GS_P4.text = "{0:.2f}".format(str_A['VI.1.4'])
        GS_P5.text = "{0:.2f}".format(str_A['VI.1.5'])
        GS_P6.text = "{0:.2f}".format(str_A['VI.1.6'])
            
        #KapitaliziranaStednja
        KS_P1.text = "{0:.2f}".format(str_A['VI.2.1'])
        KS_P2.text = "{0:.2f}".format(str_A['VI.2.2'])
        KS_P3.text = "{0:.2f}".format(str_A['VI.2.3'])
        KS_P4.text = "{0:.2f}".format(str_A['VI.2.4'])
        KS_P5.text = "{0:.2f}".format(str_A['VI.2.5'])
            
        #ZdravstvenoOsiguranje
        ZO_P1.text = "{0:.2f}".format(str_A['VI.3.1'])
        ZO_P2.text = "{0:.2f}".format(str_A['VI.3.2'])
        ZO_P3.text = "{0:.2f}".format(str_A['VI.3.3'])
        ZO_P4.text = "{0:.2f}".format(str_A['VI.3.4'])
        ZO_P5.text = "{0:.2f}".format(str_A['VI.3.5'])
        ZO_P6.text = "{0:.2f}".format(str_A['VI.3.6'])
        ZO_P7.text = "{0:.2f}".format(str_A['VI.3.7'])
        ZO_P8.text = "{0:.2f}".format(str_A['VI.3.8'])
        ZO_P9.text = "{0:.2f}".format(str_A['VI.3.9'])
        ZO_P10.text = "{0:.2f}".format(str_A['VI.3.10'])
            
        #Zaposljavanje
        ZA_P1.text = "{0:.2f}".format(str_A['VI.4.1'])
        ZA_P2.text = "{0:.2f}".format(str_A['VI.4.2'])
            
        sA_neopor.text = "{0:.2f}".format(str_A['VII'])
        sA_ktaMO2.text = "{0:.2f}".format(str_A['VIII'])

        INV_P1.text = "{0}".format(int(str_A['X.1']))
        INV_P2.text = "{0:.2f}".format(str_A['X.2'])
            
        sas_ime.text = izvjesce_sastavio['ime']                    #get real user name
        sas_prez.text = izvjesce_sastavio['prezime']                 #get real user last name

        #STRANA B
        joppd_stranaB = etree.SubElement(joppd_root,'StranaB')
        sB_primatelji = etree.SubElement(joppd_stranaB,'Primatelji')
            
        for b in self.stranaB_ids:
            bP = etree.SubElement(sB_primatelji,'P')
            ####################Ovo nije na strani b .. potegni od negdje
            P1 = etree.SubElement(bP, 'P1') #Redni broj             ######################################
            P2 = etree.SubElement(bP, 'P2') # Šifra općine /grada prebivališta                           #
            P3 = etree.SubElement(bP, 'P3') #Šifra općine grada rada                                     # 
            P4 = etree.SubElement(bP, 'P4') # OIB                                                        #
            P5 = etree.SubElement(bP, 'P5') # Ime i prezime djelatnika                                   #
            ##############################################################################################
                
            P61 = etree.SubElement(bP, 'P61') #Oznaka stjecatelja - Prilog 2
            P62 = etree.SubElement(bP, 'P62') # Oznaka obveze Prilog 3
            P71 = etree.SubElement(bP, 'P71') 
            P72 = etree.SubElement(bP, 'P72')
            P8 = etree.SubElement(bP, 'P8')
            P9 = etree.SubElement(bP, 'P9')
            P10 = etree.SubElement(bP, 'P10') # Sati rada
            P100 = etree.SubElement(bP, 'P100') # Sati neodradjeni
            P101 = etree.SubElement(bP, 'P101') # period OD
            P102 = etree.SubElement(bP, 'P102') # period DO
            P11 = etree.SubElement(bP, 'P11') 
            P12 = etree.SubElement(bP, 'P12')
            P121 = etree.SubElement(bP, 'P121')
            P122 = etree.SubElement(bP, 'P122')
            P123 = etree.SubElement(bP, 'P123')
            P124 = etree.SubElement(bP, 'P124')
            P125 = etree.SubElement(bP, 'P125')
            P126 = etree.SubElement(bP, 'P126')
            P127 = etree.SubElement(bP, 'P127')
            P128 = etree.SubElement(bP, 'P128')
            P129 = etree.SubElement(bP, 'P129')
            P131 = etree.SubElement(bP, 'P131')
            P132 = etree.SubElement(bP, 'P132')
            P133 = etree.SubElement(bP, 'P133')
            P134 = etree.SubElement(bP, 'P134')
            P135 = etree.SubElement(bP, 'P135')
            P141 = etree.SubElement(bP, 'P141')
            P142 = etree.SubElement(bP, 'P142')
            P151 = etree.SubElement(bP, 'P151')
            P152 = etree.SubElement(bP, 'P152')
            P161 = etree.SubElement(bP, 'P161')
            P162 = etree.SubElement(bP, 'P162')
            P17 = etree.SubElement(bP, 'P17')

            #fill B form with data
            P1.text = str(b.b1)
            P2.text = "{:0>5}".format(str(b.b2.code))
            P3.text = "{:0>5}".format(str(b.sudo().b3.code))
            P4.text = str(b.b4)
            P5.text = self.env['hr.employee']._get_display_name_format('first_name_first').format(b.hr_employee_id.first_name, b.hr_employee_id.last_name)
            P61.text = str(b.b61.name).zfill(4)
            P62.text = str(b.b62.name).zfill(4)
            P71.text = str(b.b71)
            P72.text = str(b.b72)
            P8.text = str(b.b8)
            P9.text = str(b.b9)
            P10.text = str(int(b.b10))
            P100.text = str(int(b.b100))
            P101.text = str(b.b101)
            P102.text = str(b.b102)
            P11.text = "{0:.2f}".format(b.b11)
            P12.text = "{0:.2f}".format(b.b12)
            P121.text = "{0:.2f}".format(b.b121)
            P122.text = "{0:.2f}".format(b.b122)
            P123.text = "{0:.2f}".format(b.b123)
            P124.text = "{0:.2f}".format(b.b124)
            P125.text = "{0:.2f}".format(b.b125)
            P126.text = "{0:.2f}".format(b.b126)
            P127.text = "{0:.2f}".format(b.b127)
            P128.text = "{0:.2f}".format(b.b128)
            P129.text = "{0:.2f}".format(b.b129)
            P131.text = "{0:.2f}".format(b.b131)
            P132.text = "{0:.2f}".format(b.b132)
            P133.text = "{0:.2f}".format(b.b133)
            P134.text = "{0:.2f}".format(b.b134)
            P135.text = "{0:.2f}".format(b.b135)
            P141.text = "{0:.2f}".format(b.b141)
            P142.text = "{0:.2f}".format(b.b142)
            P151.text = str(b.b151.name)
            P152.text = "{0:.2f}".format(b.b152)
            P161.text = str(b.b161.name)
            P162.text = "{0:.2f}".format(b.b162) #different in examples
            P17.text = "{0:.2f}".format(b.b17)

        xml = etree.tounicode(joppd_root, pretty_print="True").encode('utf-8')
        xml = b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml # add declaration on top
        validate = self.joppd_validate_xml(xml)
        if validate:
            # change state only if validation is successful
            self.write({'state':'sent'})
            attach_id = self._attach_xml_file(xml)
            view_ref = self.env['ir.model.data']._xmlid_lookup('hr_joppd_form.joppd_xml_attachment_form')
            view_id = view_ref and view_ref[1] or False,
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ir.attachment',
                'res_id': attach_id.id,
                'name': attach_id.name,
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'new',
            }

    def joppd_validate_xml(self, xml_string=''):
        """
        Validate Joppd and change state to 'sent' if succesful.
        """
        message = ''
        mod_path = get_module_path('hr_joppd_form')
        path = mod_path + '/schema/ObrazacJOPPD-v1-1.xsd'
        #check if xml schema is valid
        xml = etree.parse(BytesIO(xml_string))
        try:
            xsd_schema = etree.parse(path)
            schema = etree.XMLSchema(xsd_schema)
            result = schema.validate(xml) 
        except BaseException as e:
            message = 'Nije ispravna shema ili putanja do sheme ' + str(e)
            _logger.warning('Nije ispravna shema ili putanja do sheme (%s)', str(e))
            return False, message
        #check if xml is valid
        if result:
            return True
        else:
            try:
                schema.assertValid(xml) 
            except BaseException as e:
                raise ValidationError('Generirana XML datoteka nije u skladu s JOPPD shemom. {0}'.format(str(e)))
                return False

    def get_izvjesce_sastavio(self):
        company = self.company_id
        if not company.joppd_create_name or not company.joppd_create_surname:
            raise ValidationError(u'Na tvrtki nije postavljeno ime ili prezime podnositelja za JOPPD.')
        data = {
            'ime': company.joppd_create_name,
            'prezime': company.joppd_create_surname,
        }
        return data
    
    def _attach_xml_file(self, xml_string):
        import base64
        self.ensure_one()
        file_name = '-'.join(['JOPPD' , self.oznaka, self.vrsta])+'.xml'
        attach_name = file_name
        attach_obj = self.env['ir.attachment']
        context = {'default_res_id': self.id, 'default_res_model': 'hr.joppd.form'}
        attach_id = attach_obj.with_context(context).create({
            'name': attach_name, 
            # 'datas_fname': file_name,
            'datas': base64.encodebytes(xml_string), 
        })
        return attach_id
        
# #     ############################################################################################
# #     ###            Izračun A strane iz podataka sa B strane                                  ###
# #     ############################################################################################
    def calc_stranaA(self):
        self.env.cr.execute("UPDATE hr_joppd_form_a SET val=0.0 WHERE joppd_id=" + str(self.id))
        stranaB = self.get_stranaB_data()
        stranaA_vals = self.get_stranaA_data()
        stranaA, a_ids = [], []
        strana_A = {}
        for a in stranaA_vals:
            stranaA.append(a['val'])
            strana_A.update({a['code']: 0.00})
     

        for b in stranaB:
            OP = int(b['b61']) if b['b61'] else 0  #if b[61] field is not set then it is 0
            sA_B121 = b['b121']             # B12.1
            sA_B122 = b['b122']             # B12.2
            sA_B123 = b['b123']             # B12.3
            sA_B124 = b['b124']             # B12.4
            sA_B125 = b['b125']             # B12.5
            sA_B126 = b['b126']             # B12.6
            sA_B127 = b['b127']             # B12.7
            sA_B128 = b['b128']             # B12.8
            #sA_B129 = b['b129']            # B12.9 # Iznos umanjenja osnovice
            sA_V = b['b141'] + b['b142']        # B14.1 + B14.2 
            sA_B152 = b['b152']             # B15.2
            #Strana A - V - ukupni predujam poreza i prireza , Šifre Prilog 2

            if 1<=OP<=39 or OP in [201,5403]: 
                strana_A['V.1.1'] += sA_V                 #V.1.1.
            if 101<=OP<=119 or OP==121:
                strana_A['V.1.2']+= sA_V                #V.1.2

            strana_A['V.1'] = strana_A['V.1.1'] + strana_A['V.1.2']  #V.1 --- V.1.1 + V.2.2

            if 1001<=OP<=1009:
                strana_A['V.2']+= sA_V                           #V.2.
            if 2001<=OP<=2009:
                strana_A['V.3']+= sA_V                           #V.3.
            if 3001<=OP<=3009:
                strana_A['V.3']+= sA_V                           #V.4.
            if 4001<=OP<=4009  or OP==5501:
                strana_A['V.5']+= sA_V                           #V.5.
            ##############################################################
            if 1<=OP<=3 or 5<=OP<=10 or 21<=OP<=29 or 5701<=OP<=5799 or OP in [13,14,26]:
                strana_A['VI.1.1']+= sA_B121                    #VI.1.1
                strana_A['VI.2.1'] += sA_B122                  #VI.2.1

            if OP==201 or OP==4002:
                strana_A['VI.1.2']+= sA_B121                        #VI.1.2
                strana_A['VI.2.2'] += sA_B122                      #VI.2.2

            if 31<=OP<=39:
                strana_A['VI.1.3'] += sA_B121                       #VI.1.3
                strana_A['VI.2.3'] += sA_B122                      #VI.2.3

            if 5401<=OP<=5403 or OP==5608:
                strana_A['VI.1.4']+= sA_B121                   #VI.1.4

            if OP in [5302, 5501, 5604, 5606, 5607]:
                strana_A['VI.1.5']+= sA_B121                   #VI.1.5

            strana_A['VI.1.6']+= sA_B126                           #VI.1.6

            if 5101<=OP<=5103 or 5201<=OP<=5299 or 5401<=OP<=5403 or OP in [5301, 5608]:
                strana_A['VI.2.4'] += sA_B122                  #VI.2.4

            strana_A['VI.2.5'] += sA_B127                          #VI.2.5

            if OP in[1,5,8,9] or 21<=OP<=29 or 5701<=OP<=5799 or OP in [13,14,26]:
                strana_A['VI.3.1'] += sA_B123                  #VI.3.1
                strana_A['VI.3.2'] += sA_B124                  #VI.3.2

            if 31<=OP<=39:
                strana_A['VI.3.3'] += sA_B123                  #VI.3.3
                strana_A['VI.3.4'] += sA_B124                  #VI.3.4

            if OP in [201,4002]:
                strana_A['VI.3.5'] += sA_B123                  #VI.3.5

            if 1<=OP<=39 or 5001<=OP<=5009 or OP == 5402: 
                strana_A['VI.3.6'] += sA_B128                  #VI.3.6

            if 101<=OP<=119:
                stranaA['VI.3.7'] += sA_B123                  #VI.3.7

            if OP in[5401,5403,5601,5602,5603,5605,5608]:
                strana_A['VI.3.8'] += sA_B123                  #VI.3.8

            if OP in [5401,5403,5608]:
                strana_A['VI.3.9'] += sA_B124                  #VI.3.9

            if OP in [5302,5501,5604,5606,5607]:
                strana_A['VI.3.10 '] += sA_B124                  #VI.3.10 
                 
            strana_A['VI.4.1'] += sA_B125                      #VI.4.1
            strana_A['VI.4.2'] = 0                            #VI.4.2 
            strana_A['VII'] += sA_B152                      #VII
            #stranaA[31]               #VII

        vals = []
        for a in self.stranaA_ids:
            vals.append((1, a.id, {'val': strana_A[a.position.code]}))   #[1] edit/change: [[1, 25, {...}]]
            
        self.write({'stranaA_ids': vals})
        return True 
    
    def get_stranaA_data(self):
        sql="""
            SELECT sA.id, val, rl.code 
            FROM hr_joppd_form_a as sA
            JOIN hr_report_line as rl ON(sA.position=rl.id)
            WHERE joppd_id=%s
            ORDER BY sA.id
            """ %(self.id)
        self.env.cr.execute(sql)
        return self.env.cr.dictfetchall()

    def get_stranaA_data2(self):
        """
        Returns data for xml.
        """
        data = {}
        for line in self.stranaA_ids:
            data.update({line.position.code: line.val})
        return data

    def get_stranaB_data(self):
        sql="""
            SELECT coalesce(b71,'0') as b71, coalesce(b72,'0') as b72, 
                b8, b9, b10, b101, b102,
                coalesce(b11,'0') as b11, coalesce(b12,'0') as b12, coalesce(b121,'0') as b121, coalesce(b122,'0') as b122, coalesce(b123,'0') as b123, 
                coalesce(b124,'0') as b124, coalesce(b125,'0') as b125, coalesce(b126,'0') as b126, coalesce(b127,'0') as b127, coalesce(b128,'0') as b128, 
                coalesce(b129,'0') as b129, coalesce(b131,'0') as b131, coalesce(b132,'0') as b132, coalesce(b133,'0') as b133, coalesce(b134,'0') as b134, 
                coalesce(b135,'0')as b135, coalesce(b141,'0') as b141, coalesce(b142,'0') as b142, 
                j151.name as b151, coalesce(b152,'0') as b152, 
                j161.name as b161, coalesce(b162,'0') as b162, coalesce(b17,'0') as b17, b1, 
                j61.name as b61, j62.name as b62
      
            FROM hr_joppd_form_b as sB
            JOIN l10n_hr_joppd_sifre as j61 ON(sB.b61=j61.id)
            JOIN l10n_hr_joppd_sifre as j62 ON(sB.b62=j62.id)
            JOIN l10n_hr_joppd_sifre as j151 ON(sB.b151=j151.id)
            JOIN l10n_hr_joppd_sifre as j161 ON(sB.b161=j161.id)
            WHERE joppd_id=%s
            ORDER BY b1
            """ %(self.id)

        self.env.cr.execute(sql)
        b_data = self.env.cr.dictfetchall()
        return b_data



    ####################################################################################
    ###        Punjenje strane B podacima
    ####################################################################################
    
    @api.onchange('datum')
    def onchange_datum(self):
        if self.datum:
            datum = self.datum
            oznaka = self.get_joppd_num(datum)
            self.oznaka = oznaka
            if self.form_type == 'payroll':
                self.date_from = self.date_to = False
            elif self.form_type == 'travel_order':
                to_date = datum.replace(day=1) - timedelta(days=1)
                from_date = to_date.replace(day=1)
                self.date_from = from_date
                self.date_to = to_date
