# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrPayslipSuspensionBankAccountDistributionLine(models.Model):
    
    _name = 'hr.payslip.suspension.bank.account.distribution.line'
    _description = 'Ova klasa se koristi za definiranje raspodjele po računima za obustave'

    suspension_id = fields.Many2one('hr.payslip.employee.salary.suspension', 'Obustave', ondelete='cascade', required=True)
    bank_account_id = fields.Many2one('res.partner.bank', 'Bankovni račun', help='Bankovni račun za plaćanje', required=True, ondelete='restrict')
    partner_id = fields.Many2one(related='bank_account_id.partner_id', string='Partner')
    share = fields.Float('Udio (%)', digits=(12,8))


class HrPayslipEmployeeSalarySuspension(models.Model):
    """
    This class is used as an overview of employee's suspensions on payslip form.
    Upon payslip creation active suspensions are copied from hr.salary.suspension class.
    Suspension calculation is based on this class.
    System user and payroll officer have read access, payroll manager has all access.
    """
    _name = 'hr.payslip.employee.salary.suspension'
    _description = 'Kopija modela za obustave koja se koristi za verzioniranje na listiću'
    _inherit = ['mail.thread']  # Inherit from mail.thread to get message fields
    _order = "sequence ASC"

    _suspension_type_help = 'Vrsta obustave '\
                            '\n* fiksno - fiksni iznos obustave, može biti u lokalnoj ili stranoj valuti (koristi se sredji tečaj HNB-a).  '\
                            '\n* alimentacija - fiksni iznos za alimentaciju. '\
                            '\n* ovrha - obustava za ovrhu'\
                            '\n* članarina - članarina na temelju neto ili bruto plaće'
    _suspension_ratio_help =    'Maksimalni omjer neto plaće za obustavu (zbrojeno sa iznosima prethodnih obustava) '\
                                '\n* 1/4 - jedna četvrtina (za bankovne kredite i ovrhe). '\
                                '\n* 1/2 - jedna polovina (za alimentaciju). '\
                                '\n* 3/4 - tri četvrtine. '\
                                '\n* 1/1 - puni iznos, bez ograničenja (uz pristanak zaposlenika). '

    employee_id = fields.Many2one('hr.employee', 'Zaposlenik', required=True, ondelete='cascade', help='Zaposlenik kojem obustava pripada.')
    payslip_id = fields.Many2one('hr.payslip', 'Isplatni listić', required=True, ondelete='cascade', help='Listić kojem obustava pripada')
    name = fields.Char('Naziv',size=50, help='Naziv obustave')
    amount = fields.Float('Mjesečni iznos obustave', digits=('Payroll'), help='Iznos obustave')
    start_amount = fields.Float('Plaćeni iznos prije korištenja programa', digits=('Payroll'), help='Početni iznos npr. kredita.')
    end_amount = fields.Float('Ukupan iznos obustave', digits=('Payroll'), help='Završni iznos koji se koristi kod izračuna posljednjeg anuiteta.')
    currency_id = fields.Many2one('res.currency', 'Valuta', help='Valuta iznosa')
    start_date = fields.Date('Početni datum',required=True, help='Početni datum obustave ili kredita' )
    due_date = fields.Date('Datum dospijeća', help='Datum dospijeća (npr. Kredit)')
    annuity_number = fields.Integer('Broj anuiteta', required=True, help='Broj anuiteta ovrhe')
    bank_account_id = fields.Many2one('res.partner.bank', 'Bankovni račun', help='Bankovni račun za plaćanje', required=False, ondelete='restrict')
    paid_amount = fields.Float("Plaćeni iznos")
    number_of_annuities_paid = fields.Integer('Broj plaćenih anuiteta', readonly=True, help='Broj plaćenih anuiteta.')
    ref = fields.Char('Poziv na broj', size=50, help='Broj reference za plaćanje', required=True)
    model = fields.Char('Model', size=10, help='Model na broj pozivatelja', required=True)
    suspension_type = fields.Selection([
                        ('fixed', 'Fiksni iznos'),
                        ('alimony', 'Alimentacija'),
                        ('distraint', 'Ovrha'),
                        ('membership', 'Sindikalna članarina')
                    ], 'Vrsta obustave', required=True, help=_suspension_type_help)
    max_ratio = fields.Selection([
                        ('4', '1/4'),
                        ('2', '1/2'),
                        ('34', '3/4'),
                        ('1', '1/1'),
                    ], 'Max. iznos obustave', required=False, help=_suspension_ratio_help)
    sequence = fields.Integer('Sekvenca', required=True, help='Redni broj koji se koristi za sortiranje obustava po prioritetu. Manji redni broj ima veći prioritet.')
    company_id = fields.Many2one('res.company', 'Tvrtka', help='Tvrtka')
    i3_active = fields.Boolean("Aktivno", default=True)
    suspension_id = fields.Many2one('hr.salary.suspension', 'Obustave', required=True, help="Koristi se za očuvanje veze prema stvarnoj obustavi", ondelete='restrict')

    membership_base = fields.Selection([('brutto', 'Bruto plaća'), ('netto', 'Neto plaća')], 'Osnovica za članarinu')
    membership_base_pct = fields.Float('Postotak osnovice (%)')
    bank_account_distribution_ids = fields.One2many('hr.payslip.suspension.bank.account.distribution.line', 'suspension_id', 'Raspodjela po računima')
    even_split = fields.Boolean('Razdijeli ravnomjerno', default=True)
    paid_this_month = fields.Float('Plaćeno ovaj mjesec')


    @api.onchange('even_split', 'bank_account_distribution_ids')
    def update_bank_account_distribution(self):
        if self.even_split:
            for acc in self.bank_account_distribution_ids:
                acc.share = 100.0 / len(self.bank_account_distribution_ids)

    @api.onchange('suspension_type')
    def on_change_type(self):
        """
        Sets max_ratio based on type change. Fixed|Distraint=1/4, Alimony=1/2.
        Reset bank account distribution settings - else domain on bank account field makes no sense:
            If suspension_type == 'membership', only bank accounts from syndicates are allowed.
            If we change suspension_type and don't reset account distribution:
                => we are in conflict because a syndicate's account is entered for non-syndicate suspension type
            Same principle applies if some other suspension_type is chosen, non-syndicate bank account entered and then suspension_type changed to 'membership'.
        """
        self.bank_account_distribution_ids = []
        ratio = False
        if self.suspension_type != 'membership':
            ratio = '4'
            if self.suspension_type == 'alimony':
                ratio = '2'
            if self.suspension_type == 'distraint':
                self.currency_id = self._get_currency()
            self.membership_base = False
            self.membership_base_pct = 0
        self.max_ratio = ratio

# class MailFollowers(models.Model):
#     _inherit = 'mail.followers'


class HrSalarySuspensionPayment(models.Model):
    """Record of all paid salary suspensions"""
    _name = 'hr.salary.suspension.payment'
    _description = 'History of salary suspension payments'

    payslip_id = fields.Many2one('hr.payslip', 'Isplatni listić', required=True)
    suspension_id = fields.Many2one('hr.salary.suspension', 'Obustave', required=True, ondelete='restrict')
    amount = fields.Float('Mjesečni iznos obustave', digits=('Payroll'))


class HrSalarySuspensionBankAccountDistributionLine(models.Model):
    
    _name = 'hr.salary.suspension.bank.account.distribution.line'
    _description = 'This class is used to define bank account distribution for salary suspensions'

    suspension_id = fields.Many2one('hr.salary.suspension', 'Obustave', required=True, ondelete='cascade')
    bank_account_id = fields.Many2one('res.partner.bank', 'Bankovni račun', help='Bankovni račun za plaćanje', required=True, ondelete='restrict')
    partner_id = fields.Many2one(related='bank_account_id.partner_id', string='Partner')
    share = fields.Float('Udio (%)', digits=(12,8))



class HrSalarySuspension(models.Model):
    """
    This class is used as an overview of employee's suspensions.
    Upon creating payslips, active suspensions are copied to payslip (into hr.payslip.employee.salary.suspension class, on which calculation is based).
    System user and payroll officer have read access so they are able to view employee form.
    Payroll manager has all access rights and is the only type of user who can see the tab.
    """
    _name = 'hr.salary.suspension'
    _description = 'Obustava plaće'
    _inherit='mail.thread'
    _order = "sequence ASC"

    _suspension_type_help = 'Vrsta obustave '\
                            '\n* fiksno - fiksni iznos obustave, može biti u lokalnoj ili stranoj valuti (koristi se sredji tečaj HNB-a).  '\
                            '\n* alimentacija - fiksni iznos za alimentaciju. '\
                            '\n* ovrha - obustava za ovrhu'\
                            '\n* članarina - članarina na temelju neto ili bruto plaće'
    _suspension_ratio_help =    'Maksimalni omjer neto plaće za obustavu (zbrojeno sa iznosima prethodnih obustava) '\
                                '\n* 1/4 - jedna četvrtina (za bankovne kredite i ovrhe). '\
                                '\n* 1/2 - jedna polovina (za alimentaciju). '\
                                '\n* 3/4 - tri četvrtine. '\
                                '\n* 1/1 - puni iznos, bez ograničenja (uz pristanak zaposlenika). '

    def _get_currency(self):
        return self.company_id.currency_id.id

    def _get_company(self):
        user = self.env.user
        return user.company_id.id

    employee_id = fields.Many2one('hr.employee', 'Zaposlenik', required=True, ondelete='cascade', help='Zaposlenik kojem obustava pripada.')
    name = fields.Char('Naziv', size=50, help='Naziv obustave', tracking=True)
    amount = fields.Float('Mjesečni iznos obustave', digits=('Payroll'), help='Iznos obustave', tracking=True)
    start_amount = fields.Float('Plaćeni iznos prije korištenja programa', digits=('Payroll'), help='Početni iznos npr. kredita.', tracking=True)
    end_amount = fields.Float('Ukupan iznos obustave', digits=('Payroll'), help='Završni iznos koji se koristi kod izračuna posljednjeg anuiteta.', tracking=True)
    currency_id = fields.Many2one('res.currency', 'Valuta', default=_get_currency, help='Valuta iznosa', tracking=True)
    start_date = fields.Date('Početni datum',required=True, help='Početni datum obustave ili kredita', tracking=True)
    due_date = fields.Date('Datum dospijeća', help='Datum dospijeća (npr. Kredit)', tracking=True)
    annuity_number = fields.Integer('Broj anuiteta', help='Broj anuiteta ovrhe', tracking=True)
    bank_account_id = fields.Many2one('res.partner.bank', 'Bankovni račun', help='Bankovni račun za plaćanje', required=False, ondelete='restrict', tracking=True)
    paid_amount = fields.Float("Plaćeni iznos", compute='_calculate_paid_amount', tracking=True)
    number_of_annuities_paid = fields.Integer('Broj plaćenih anuiteta', readonly=True, help='Broj plaćenih anuiteta.', compute='_calculate_number_of_paid_annuities', tracking=True)
    ref = fields.Char('Poziv na broj', size=50, help='Broj reference za plaćanje', required=True)
    model = fields.Char('Model', size=10, help='Model na broj pozivatelja', required=True, tracking=True)
    suspension_type = fields.Selection([
                        ('fixed', 'Fiksni iznos'),
                        ('alimony', 'Alimentacija'),
                        ('distraint', 'Ovrha'),
                        ('membership', 'Sindikalna članarina')
                    ], 'Vrsta obustave', required=True, default='fixed', help=_suspension_type_help, tracking=True)
    max_ratio = fields.Selection([
                        ('4', '1/4'),
                        ('2', '1/2'),
                        ('34', '3/4'),
                        ('1', '1/1'),
                    ], 'Max. iznos obustave', required=False, default='4', help=_suspension_ratio_help, tracking=True)
    sequence = fields.Integer('Sekvenca', required=True, help='Redni broj koji se koristi za sortiranje obustava po prioritetu. Manji redni broj ima veći prioritet.', tracking=True)
    company_id = fields.Many2one('res.company', 'Tvrtka', default=_get_company, help='Tvrtka')
    payment_ids = fields.One2many('hr.salary.suspension.payment', 'suspension_id', 'Povijest isplata')
    i3_active = fields.Boolean("Aktivno", default=True, tracking=True)

    membership_base = fields.Selection([('brutto', 'Bruto plaća'), ('netto', 'Neto plaća')], 'Osnovica za članarinu', tracking=True)
    membership_base_pct = fields.Float('Postotak osnovice (%)', tracking=True)
    bank_account_distribution_ids = fields.One2many('hr.salary.suspension.bank.account.distribution.line', 'suspension_id', 'Raspodjela po računima')
    even_split = fields.Boolean('Razdijeli ravnomjerno', default=True)


    @api.onchange('even_split', 'bank_account_distribution_ids')
    def update_bank_account_distribution(self):
        if self.even_split:
            for acc in self.bank_account_distribution_ids:
                acc.share = 100.0 / len(self.bank_account_distribution_ids)

    @api.depends('payment_ids')
    def _calculate_number_of_paid_annuities(self):
        for s in self:
            s.number_of_annuities_paid = len(s.payment_ids)

    @api.depends('payment_ids')
    def _calculate_paid_amount(self):
        """
        Returns sum of paid amount for suspensions.
        """
        for s in self:
            s.paid_amount = sum([payment.amount for payment in s.payment_ids])

    @api.onchange('suspension_type')
    def on_change_type(self):
        """
        Sets max_ratio based on type change. Fixed|Distraint=1/4, Alimony=1/2.
        Reset bank account distribution settings - else domain on bank account field makes no sense:
            If suspension_type == 'membership', only bank accounts from syndicates are allowed.
            If we change suspension_type and don't reset account distribution:
                => we are in conflict because a syndicate's account is entered for non-syndicate suspension type
            Same principle applies if some other suspension_type is chosen, non-syndicate bank account entered and then suspension_type changed to 'membership'.
        """
        self.bank_account_distribution_ids = []
        ratio = False
        if self.suspension_type != 'membership':
            ratio = '4'
            if self.suspension_type == 'alimony':
                ratio = '2'
            if self.suspension_type == 'distraint':
                self.currency_id = self._get_currency()
            self.membership_base = False
            self.membership_base_pct = 0
        self.max_ratio = ratio

    def get_suspension_data(self):
        """
        Return a copy of all fields except payment_ids.
        Used for versioning on hr.payslip.
        """
        susp_data = {}
        for field in self._fields:
            if field == 'payment_ids':
                continue
            elif isinstance(self._fields[field], (fields.Many2one)):
                susp_data[field] = self[field].id
            else:
                susp_data[field] = self[field]
        return susp_data

