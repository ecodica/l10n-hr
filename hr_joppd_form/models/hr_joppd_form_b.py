#-*- coding:utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HrJoppdFormB(models.Model):
    _name='hr.joppd.form.b'
    _description = 'B strana JOPPD obrasca'
    # order by b1 so that this is the default order on JOPPD form
    # before adding option to order items by employee name we didn't have this problem because the order could never be changed
    # add joppd_id as primary key just in case a list of all B items will be used and not just those from a single JOPPD
    _order = 'joppd_id, b1'
    
    ##############################################################################
    # B7.1
    _b71_sel = [('0','Nema dodatnog doprinosa'),
                ('1','Obveza za 12=14 mjes.'),
                ('2','Obveza za 12=15 mjes.'),
                ('3','Obveza za 12=16 mjes.'),
                ('4','Obveza za 12=18 mjes.')]
    _b71_help = "Obveza dodatnog doprinosa za mirovinsko osiguranje\n"\
                "za staž osiguranja s povećanim trajanjem – upisuje se:\n"\
                "0 – ukoliko podnositelj po osnovi isplaćenog primitka/obračunane naknade ili\n"\
                "    osnovice za obračun doprinosa nema obvezu obračuna dodatnog doprinosa za \n"\
                "    mirovinsko osiguranje za staž osiguranja s povećanim trajanjem,\n"\
                "1 – ukoliko podnositelj po osnovi isplaćenog primitka/osnovice za obračun doprinosa\n"\
                "    ima obvezu obračuna dodatnog doprinosa za mirovinsko osiguranje za \n"\
                "    staž osiguranja s povećanim trajanjem kada se 12 mjeseci računa kao 14 mjeseci,\n"\
                "2 – ukoliko podnositelj po osnovi isplaćenog primitka/osnovice za obračun doprinosa\n"\
                "    ima obvezu obračuna dodatnog doprinosa za mirovinsko osiguranje za \n"\
                "    staž osiguranja s povećanim trajanjem kada se 12 mjeseci računa kao 15 mjeseci,\n"\
                "3 – ukoliko podnositelj po osnovi isplaćenog primitka/osnovice za obračun doprinosa \n"\
                "    ima obvezu obračuna dodatnog doprinosa za mirovinsko osiguranje za \n"\
                "    staž osiguranja s povećanim trajanjem kada se 12 mjeseci računa kao 16 mjeseci,\n"\
                "4 – ukoliko podnositelj po osnovi isplaćenog primitka/osnovice za obračun doprinosa\n"\
                "    ima obvezu obračuna dodatnog doprinosa za mirovinsko osiguranje za \n"\
                "    staž osiguranja s povećanim trajanjem kada se 12 mjeseci računa kao 18 mjeseci."
    #######################################################################################################
    # B 7.2
    def _b72_sel(self):
        """
        Returned using method because we need the same selection on salary.parameters.
        """
        return [
            ('0','Nema pravo na umanjenje'),
            ('1','Ima jednog poslodavca'),
            ('2','Koriste mu se podaci Porezne uprave o iznosu umanjenja mjesečne osnovice'),
            ('3','Ima više poslodavaca i dostavlja izjavu o iznosima mjesečnih bruto plaća')
        ]
    _b72_help = "Tip umanjenja osnovice – upisuje se:\n"\
                "0 – ukoliko stjecatelj nema pravo na umanjenje,\n"\
                "1 – ukoliko stjecatelj ima jednog poslodavca,\n"\
                "2 – ukoliko se za stjecatelja koriste podaci Porezne uprave o iznosu umanjenja mjesečne osnovice,\n"\
                "3 – ukoliko stjecatelj ima više poslodavaca i dostavlja izjavu o iznosima mjesečnih bruto plaća"
    #######################################################################################################
    # B 8
    _b8_sel = [('0','Nema prethodne obveze'),
               ('1','Prvi mjesec po osnovi'),
               ('2','Zadnji mjesec po osnovi'),
               ('3','Mjeseci unutar perioda osnove'),
               ('4','Početak i kraj u istom mjesecu'),
               ('5','Obveza nastala nakon perioda')]
    _b8_help = "Oznaka prvog/zadnjeg mjeseca u obveznom osiguranju po istoj osnovi – upisuje se:\n"\
               "0 – ukoliko po osnovi isplaćenog primitka/obračunane naknade ili osnovice \n"\
               "    za obračun doprinosa ne postoji obveza prethodnog obveznog osiguranja ili utvrđivanja prava po toj osnovi,\n"\
               "1 – ukoliko je to prvi mjesec obveznog osiguranja/korištenja prava po osnovi za koju je izvršen obračun,\n"\
               "2 – ukoliko je to zadnji mjesec obveznog osiguranja/korištenja prava po osnovi za koju je izvršen obračun,\n"\
               "3 – ukoliko su to ostali mjeseci unutar obveznog osiguranja/korištenja prava po osnovi za koju je izvršen obračun,\n"\
               "4 – ukoliko obvezno osiguranje/korištenje prava po osnovi za koju je izvršen obračun počinje i završava unutar jednog (izvještajnog) mjeseca,\n"\
               "5 – ukoliko je obveza doprinosa nastala nakon prestanka obveznog osiguranja i ne odnosi se na određeni mjesec proveden u tom osiguranju.\n"\
               "\nOznake od 1 do 5 unose se za sve skupine stjecatelja primitka/osiguranika za koje se pod razdoblje \n"\
               "za koje se obračunava obveza doprinosa i/ili razdoblje za koje se primitak isplaćuje (pod 10.1. i 10.2.)\n"\
               "upisuje mjesec dana ili kraće od mjesec dana, odnosno više od mjesec dana ako se isplaćuju zaostale plaće i mirovine,\n"\
               "te za ostale primitke od nesamostalnog rada iz članka 22. stavka 3. Zakona o doprinosima,"
    ##################################################################################################################3
    # B 9
    def _b9_sel(self):
        """
        Returned using method because we need the same selection on salary.parameters.
        """
        return [
            ('0','Bez radnog vremena'),
            ('1','Puno radno vrijeme'),
            ('2','Nepuno radno vrijeme'),
            ('3','Pola rad.vr.-njega djeteta')
        ]
        
    _b9_help = "Oznaka punog, nepunog radnog vremena ili rada s polovicom radnog vremena  – upisuje se:\n" \
               "0 – ukoliko ne postoji radno vrijeme,\n"\
               "1 – ukoliko je osiguranik prijavljen na puno radno vrijeme,\n"\
               "2 – ukoliko je osiguranik prijavljen na nepuno radno vrijeme,\n"\
               "3 – za osobe koje rade s polovicom punog radnog vremena radi njege djeteta s teškoćama u razvoju.\n"\
               "\nOznake od 1 do 3 unose se za sljedeće skupine oznaka stjecatelja primitka/osiguranika iz Priloga 2.\n"\
               "Stjecatelj primitka/osiguranik: 0001-0019; 0021-0029; 0031-0039; 5701-5799,\n"\
               "a oznaka 0 za sve ostale skupine oznaka stjecatelja primitka/osiguranika"
    ######################################################################################################################
    # B10
    _b10_help = "Upisuje se broj obračunanih sati rada za isplatu plaće, za slijedeće skupine \n"\
                "oznaka stjecatelja primitka/osiguranika iz Priloga 2. Stjecatelj primitka/osiguranik:\n"\
                "0001-0019, 0021-0029, 0031-0039, 5701-5799,\n"\
                "a kada izvješće o korištenju prava iz obveznih osiguranja podnosi poslodavac,\n"\
                "odnosno osoba koja je obveznik doprinosa, te obveznik obračunavanja i obveznik plaćanja doprinosa\n"\
                "sukladno članku 182. stavku 3. Zakona o doprinosima upisuje se broj obračunanih \n"\
                "sati rada za vrijeme korištenja prava.\n"\
                "Oznaka 0 upisuje se za sve ostale skupine oznaka stjecatelja primitka/osiguranika.\n"\
                "Kod isplate zaostale plaće ne upisuje se broj sati rada za mjesece za koje se plaća isplaćuje\n"\
                "ako je isti iskazan u ranijim razdobljima kod podnošenja izvješća za obračunane doprinose\n"\
                "za obvezna osiguranja po osnovi plaće. Obračunani sati rada za pojedini mjesec iskazuju se samo jednom,\n"\
                "kod isplate redovne plaće odnosno obračuna obveznih doprinosa,\n"\
                "a kod svih ostalih isplata u tijeku jednog mjeseca (za ostale primitke koji se isplaćuju uz plaću,\n"\
                "za isplatu određenog primitka u naravi i drugo) ne upisuje se broj sati rada. odnosno upisuje se 0,"
    #######################################################################################################################
    # B 10.1 i B10.2
    _b_101_102_help = "Razdoblje za koje se obračunava obveza doprinosa i/ili razdoblje za koje se primitak isplaćuje\n"\
                    "odnosno u kojem se isplaćuje. Razdoblje može biti:\n"\
                    "1 - mjesec dana ili kraće od mjesec dana ako u jednom mjesecu počinje i/ili završava razdoblje \n"\
                    "    osiguranja prema istoj osnovi osiguranja, što se upisuje u formatu od DD.MM.GGGG. do DD.MM.GGGG\n"\
                    "2 - više mjeseci, a manje od godinu dana (kalendarske godine), što se upisuje u formatu od DD.MM.GGGG. do DD.MM.\n"\
                    "3 - te kalendarska godina što se upisuje u formatu od 01.01.GGGG. do 31.12.GGGG."
    ########################################################################################################################
    # B12
    _b12_help = "Osnovica za obračun doprinosa (pod 12.). Kada je osnovica viša od najviše mjesečne ili \n"\
                "najviše godišnje osnovice za obračun doprinosa za obvezno mirovinsko osiguranje, \n"\
                "upisuje se stvarni iznos osnovice (ne upisuje se iznos najviše mjesečne ili godišnje osnovice)."
    #########################################################################################################################
    # B12.1
    _b121_help = "Iznos obračunanih doprinosa za mirovinsko osiguranje na temelju generacijske solidarnosti\n"\
                    "primjenom propisane stope na osnovicu za obračun doprinosa."
    #########################################################################################################################
    
    def _default_b61(self):
        return self.get_joppd_sifra(code_type='P-2', name='0')

    def _default_b62(self):
        return self.get_joppd_sifra(code_type='P-3', name='0')


    joppd_id = fields.Many2one('hr.joppd.form','JOPPD obrazac', ondelete="cascade")
    user_edit = fields.Boolean('Ručno uređivano', default=False)
    hr_employee_id = fields.Many2one('hr.employee','5. Ime i prezime stjecatelja/osiguranika', required=True)
    hr_employee_state = fields.Char('Djelatnik prirez(KOD)' ,size=5)#DB,SL : samo za izvjestaj... nema nikakav uticaj 
    hr_department = fields.Char(related='hr_employee_id.department_id.name', string='Department')

    b1 = fields.Integer('1. Redni broj', required=True)
    b2 =  fields.Many2one('res.city', '2. Šifra općine/grada prebivališta/boravišta', required=True, domain=[('code','!=',False)])
    b3 =  fields.Many2one('res.city', '3. Šifra općine/grada rada', required=True, domain=[('code','!=',False)])
    b4 = fields.Char(related='hr_employee_id.oib', required=True, string='4. OIB') 
    b61 = fields.Many2one('l10n.hr.joppd.sifre','6.1. Oznaka stjecatelja/ osiguranika', required=True, domain=[('code_type','=','P-2')], default=_default_b61)
    b62 = fields.Many2one('l10n.hr.joppd.sifre','6.2. Oznaka primitka/ obveze doprinosa', required=True, domain=[('code_type','=','P-3')], default=_default_b62)
    b71 = fields.Selection(_b71_sel,'7.1. Dodatni doprinosi MO', default='0', required=True, help = _b71_help)
    b72 = fields.Selection(_b72_sel,'7.2. Tip umanjenja osnovice', required=True, help = _b72_help)
    b8 = fields.Selection(_b8_sel, '8. Oznaka mjeseca osiguranja', default='1', required=True, help = _b8_help)
    b9 = fields.Selection(_b9_sel, '9. Oznaka radnog vremena', default='1', required=True, help = _b9_help)
    b10 = fields.Float('10. Ukupni sati rada',digits=(15,2), help = _b10_help)
    b100 = fields.Float('10.0. Ukupni neodrađeni sati rada', help = _b10_help)
    b101 = fields.Date('10.1. Razdoblje obračuna od', required=True, help = _b_101_102_help)
    b102 = fields.Date('10.2. Razdoblje obračuna do', required=True, help = _b_101_102_help)
    b11 = fields.Float('11. Iznos primitka (oporezivi)', digits=(15,2))
    b12 = fields.Float('12. Osnovica za obračun doprinosa', digits=(15,2), help = _b12_help)
    b121 = fields.Float('12.1. Doprinos za mirovinsko osiguranje',digits=(15,2),  help = _b121_help)
    b122 = fields.Float('12.2. Dopr. za mir. osig. II Stup',digits=(15,2))
    b123 = fields.Float('12.3. Zdravstveno osig.',digits=(15,2))
    b124 = fields.Float('12.4. Doprinos za zašt.zdravlja na radu',digits=(15,2))
    b125 = fields.Float('12.5. Doprinosi za zapošljavanje',digits=(15,2))
    b126 = fields.Float('12.6. Dodatni dop. za mir. osig. - staž pov. traj.',digits=(15,2))
    b127 = fields.Float('12.7. Dod.dop. za mir. osig.- staž pov. traj. II STUP',digits=(15,2))
    b128 = fields.Float('12.8. Poseban dop. - zdrav.zašt.ino.',digits=(15,2))
    b129 = fields.Float('12.9. Iznos umanjenja osnovice',digits=(15,2))
    b131 = fields.Float('13.1. Izdatak',digits=(15,2))
    b132 = fields.Float('13.2. Izdatak -upla.dop. mir.osig',digits=(15,2))
    b133 = fields.Float('13.3. Dohodak',digits=(15,2))
    b134 = fields.Float('13.4. Osobni odbitak',digits=(15,2))
    b135 = fields.Float('13.5. Porezna osnovica',digits=(15,2))
    b141 = fields.Float('14.1. Izn.obr. poreza na dohodak',digits=(15,2))
    b142 = fields.Float('14.2. Izn.obr. prireza por.na doh.',digits=(15,2))
    b151 = fields.Many2one('l10n.hr.joppd.sifre','15.1. Oznaka neopor. primitka', required=True, domain=[('code_type','=','P-4')])
    b152 = fields.Float('15.2. Iznos neopor. primitka',digits=(15,2))
    b161 = fields.Many2one('l10n.hr.joppd.sifre','16.1. Oznaka načina isplate', required=True, domain=[('code_type','=','P-5')])
    b162 = fields.Float('16.2. Iznos za isplatu',digits=(15,2))
    b17 = fields.Float('17. Obračun. prim. od nesam. rada (plaća)')
    
    def get_joppd_sifra(self, code_type, name):
        return self.env['l10n.hr.joppd.sifre'].search(['&',('code_type','=', code_type),('name','=',name)]).id

    
    @api.onchange('hr_employee_id')    
    def onchange_employee(self):
        """
        Return b2 and b3 on employee change.
        """
        b2 = False
        b3 = False
        if self.hr_employee_id:
            emp_home_address = self.hr_employee_id.partner_id
            emp_work_address = self.hr_employee_id.address_work_id
            b2 = emp_home_address.state_id.id if emp_home_address and emp_home_address.state_id else False
            b3 = emp_work_address.state_id.id if emp_work_address and emp_work_address.state_id else False
        self.b2 = b2
        self.b3 = b3
    
    def unlink_action(self):
        #developer: Dobro odradi renumeraciju,
        # ali ne refresha view, potrebno je ponovo učitati view da se vidi rezultat
        j_id = self.env.context.get('active_id')
        stay_ids = self.search(['&', ('id', 'not in', self.ids), ('joppd_id', '=' , j_id)])
        rbr = 1

        #check if joppd type is add (3)
        joppd_obj = self.env['hr.joppd.form']
        joppd = joppd_obj.browse(j_id)
        if joppd.vrsta == '2': #if joppd type is 2 then do nothing
            return True
        elif joppd.vrsta == '3': #get max number from original joppd
            self.env.cr.execute("SELECT MAX(b1) FROM hr_joppd_form_b WHERE joppd_id = " + str(joppd.parent_id.id))
            r = self.env.cr.fetchone()[0]
            if r and r != 0:
                rbr = r + 1

        for stayB in stay_ids:
            stayB.write({'b1':rbr})
            rbr += 1
        return True
    
    def unlink(self):
        self.unlink_action()
        return super(HrJoppdFormB, self).unlink()
    
    def write(self, vals):
        if 'user_edit' not in vals.keys():
            vals['user_edit']=True 
        return super(HrJoppdFormB, self).write(vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.validate_data(vals)
            if 'joppd_id' not in vals.keys():
                vals['joppd_id'] = self.env.context.get('active_id')
            if 'b1' not in vals or vals['b1']==0:
                r = 0
                #check if joppd type is add (3)
                joppd_obj = self.env['hr.joppd.form']
                joppd = joppd_obj.browse(vals['joppd_id'])
                if joppd.vrsta == '2':
                    raise ValidationError(u'Kod ispravka nije moguće dodavati nove stavke već samo uređivati postojeće')
                if joppd.vrsta == '3': 
                    self.env.cr.execute("SELECT MAX(b1) FROM hr_joppd_form_b WHERE joppd_id = " + str(vals['joppd_id']))
                    r = self.env.cr.fetchone()[0]
                    if not r or r == 0: #if r == 0 then get id from parent
                        self.env.cr.execute("SELECT MAX(b1) FROM hr_joppd_form_b WHERE joppd_id = " + str(joppd.parent_id.id))
                        r = self.env.cr.fetchone()[0]
                else:
                    self.env.cr.execute("SELECT MAX(b1) FROM hr_joppd_form_b WHERE joppd_id = " + str(vals['joppd_id']))
                    r = self.env.cr.fetchone()[0]
                rbr =  r and r+1 or 1
                vals['b1']= rbr
        return super(HrJoppdFormB, self).create(vals_list)
    
    def validate_data(self, vals):
        emp = self.env['hr.employee'].browse(vals.get('hr_employee_id'))
        if not vals.get('b2'):
            raise UserError(_(u'City for employee {0} address has not been entered'.format(emp.name)))
        if not vals.get('b3'):
            raise UserError(_(u'City for employee {0} work address has not been entered'.format(emp.name)))
        return True
