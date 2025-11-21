from odoo import models, fields, api, _


class BankingExportSepa(models.Model):
    '''SEPA export'''
    _name = 'banking.export.sepa'
    _rec_name = 'filename'
    _description = 'Ova klasa se koristi za modeliranje SEPA izvoza'

    _charge_bearer_sel = [
        ('SLEV', 'Following Service Level'),
        ('SHAR', 'Shared'),
        ('CRED', 'Borne by Creditor'),
        ('DEBT', 'Borne by Debtor'),
    ]

    _charge_bearer_help = "Following service level : transaction charges are to be" \
        "applied following the rules agreed in the service level and/or" \
        "scheme (SEPA Core messages must use this). Shared : " \
        "transaction charges on the creditor side are to be borne by " \
        "the creditor, transaction charges on the debtor side are to " \
        "be borne by the debtor. Borne by creditor : all transaction " \
        "charges are to be borne by the creditor. Borne by debtor : " \
        "all transaction charges are to be borne by the debtor."
    
    _batch_booking_help = "If true, the bank statement will display only one debit " \
        "line for all the wire transfers of the SEPA XML file ; " \
        "if false, the bank statement will display one debit line " \
        "per wire transfer of the SEPA XML file."

    payment_order_ids = fields.Many2many('account.payment.order', 'account_payment_order_sepa_rel', 'banking_export_sepa_id',
                                        'account_order_id', 'Nalozi za plaćanje', readonly=True)
    nb_transactions = fields.Integer('Broj transakcija', readonly=True)
    total_amount = fields.Float('Ukupni iznos', digits=('Account'), readonly=True)
    batch_booking = fields.Boolean('Način terećenja računa platitelja', readonly=True, help=_batch_booking_help)
    charge_bearer = fields.Selection(_charge_bearer_sel, 'Troškovna opcija', readonly=True, help=_charge_bearer_help)
    create_date = fields.Datetime('Datum kreiranja', readonly=True)
    sepa_file = fields.Binary('SEPA xml datoteka', readonly=True)
    filename = fields.Char('Naziv datoteke', readonly=True)
    state = fields.Selection([
        ('draft', 'Nacrt'),
        ('sent', 'Poslano'),
        ('done', 'Podmireno'),
        ], 'Stanje', readonly=True)


class Info3Sepa(models.Model):
    _name = 'info3.sepa'
    _description = 'Ova klasa se koristi za spremanje kreiranih SEPA plaćanja u modulu Obračun plaće'
    _order = 'date desc, name desc'

    name = fields.Char('Naziv', size=128)
    date = fields.Date('Date')
    lines = fields.One2many('info3.sepa.line.form','sepa_line_id','Stavke', readonly=True)
    sepa_type = fields.Char('Vrsta', size=128)
    payslip_run_ids = fields.Many2many('hr.payslip.run','info3_sepa_file_payslip_run_rel', 'sepa_file_id', 'run_id',
                                        'Obračuni plaće', readonly=True)
    filename = fields.Char('Naziv datoteke', size=256, readonly=True)
    file_id = fields.Many2one('banking.export.sepa', 'SEPA xml datoteka', readonly=True)
    file_related = fields.Binary(related='file_id.sepa_file', string="Datoteka", readonly=True)
    user_edit = fields.Boolean('Ručno uređivano', default=False)
    company_id = fields.Many2one('res.company', string='Tvrtka', readonly=True, copy=False,
                                    default=lambda self: self.env['res.company']._company_default_get())

class Info3SepaLineForm(models.Model):
    _name = 'info3.sepa.line.form'
    _description = 'Stavka plaćanja SEPA datoteke'

    sepa_line_id = fields.Many2one('info3.sepa', 'Sepa id')
    nazbanprim = fields.Char('Banka primatelja', size=50)
    nazivprim = fields.Char('Naziv primatelja', size=128)
    primatelj = fields.Char('Primatelj', size=128)
    opis = fields.Char('Opis', size=140)
    ispl = fields.Float('Iznos')
    modelplat = fields.Char('modelplat', size=26, help='Ref u SEPA xml datoteci')
    modelprim = fields.Char('modelprim', size=26, help='EndToEndId u SEPA xml datoteci')
    ibanprim = fields.Char('IBAN primatelja', size=35)
    sum = fields.Float('sum')
    protbanprim = fields.Char('Zaštićeni račun primatelja', size=34)
    protiban = fields.Char('IBAN zaštićenog računa', size=34)
    oib = fields.Char('OIB primatelja', size=34)
    bic = fields.Char('BIC', size=34)

class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    date_done = fields.Date(string='Done Date', readonly=True)
