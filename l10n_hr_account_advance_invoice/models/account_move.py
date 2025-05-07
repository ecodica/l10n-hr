from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    advance_invoice = fields.Boolean("Advance invoice", help="Indicates if invoice is for advance payment.")
    is_advance_reconciled = fields.Boolean("Advance reconciled", compute="_compute_is_advance_reconciled", help='Advance is reconciled if invoice amount is equal total amount on storno lines of posted invoices where it was used as advance invoice.', store=True)
    advance_line_ids = fields.One2many("account.move.advance.line", "invoice_id", "Advances")
    advance_account_id = fields.Many2one(comodel_name="account.account", string="Advance account move line account")

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            advance_ids = self.search([
                ('id', 'not in', self.ids), 
                ('partner_id', '=', self.partner_id.id),
                ('advance_invoice', '=', True),
                ('state', 'not in', ['draft', 'cancel']),
                ('is_advance_reconciled', '=', False),
            ])
            unclosed_advance_string = ''
            for adv in advance_ids:
                unclosed_advance_string += '{0}\n'.format(adv.name)
            if unclosed_advance_string:
                return {
                    'warning': {
                        'title': _("Warning!"),
                        'message': _("This partner has unclosed advances!") + "\n" + unclosed_advance_string,
                    }
                }
        return

    def button_draft(self):
        #unlink storno_move_id if advance payment
        res = super().button_draft()

        for line in self.advance_line_ids:
            storno_move = line.storno_move_id
            if storno_move:
                storno_move.button_draft()
                res_unlink = storno_move.unlink()
                if res_unlink:
                    line.storno_move_id = False
            #check if advance reconciled
            line.advance_invoice_id._compute_is_advance_reconciled()
        return res

    def _create_advance_refund_invoice(self):
        for move in self:
            if move.advance_invoice or not move.advance_line_ids:
                continue
            #raise warning if advance amount is larger than invoice amount
            advance_amount = sum([line.amount for line in move.advance_line_ids])
            if advance_amount > move.amount_total:
                raise ValidationError(_("Advance payment amount ({0}) is higher than the invoice amount ({1}). Reduce the amount in the 'Advance' tab on the invoice.").format(advance_amount, move.amount_total))
            storno_name = move.company_id.storno_advance_account_move_name_prefix
            counter = 1
            for line in move.advance_line_ids:
                name = "{0} {1} {2}".format(move.name, storno_name, counter) if len(move.advance_line_ids) > 1 else "{0} {1}".format(move.name, storno_name)
                counter += 1
                new_account_move = {
                    'partner_id': move.partner_id.id,
                    'partner_shipping_id': move.partner_shipping_id.id,
                    'l10n_hr_nacin_placanja': move.l10n_hr_nacin_placanja,
                    'invoice_date': move.invoice_date,
                    'date': move.invoice_date,
                    'invoice_date_due': move.invoice_date_due,
                    'reference_type': move.reference_type,
                    'payment_reference': move.payment_reference,
                    'l10n_hr_date_delivery': move.l10n_hr_date_delivery,
                    'state': 'draft',
                    'name': name,
                    'journal_id': move.journal_id.id,
                    'currency_id': move.currency_id.id,
                    'move_type': 'entry',
                    'auto_post': move.auto_post,
                    'l10n_hr_fiskalni_broj': name,
                    'l10n_hr_fiskal_uredjaj_id': move.l10n_hr_fiskal_uredjaj_id.id,
                    'ref': line.advance_invoice_id.name
                }
                res_create_storno_move = move.env['account.move'].create(new_account_move)

                #create account move lines
                if res_create_storno_move:
                    advance_journal_lines = line.advance_invoice_id.line_ids
                    payment_term_line = move.line_ids.filtered(lambda line: line.display_type == "payment_term")
                    lines_to_create = []
                    for adv_journal_line in advance_journal_lines:
                        amount_percentage = line.amount / adv_journal_line.move_id.amount_total
                        amount_credit = 0
                        amount_debit = 0
                        account_id = adv_journal_line.account_id.id
                        if adv_journal_line.display_type == "tax":
                            amount_credit = adv_journal_line.credit * (-1) * amount_percentage
                            amount_debit = 0
                        elif adv_journal_line.display_type == "product":
                            amount_credit = adv_journal_line.credit * (-1) * amount_percentage
                            amount_debit = 0
                        elif adv_journal_line.display_type == "payment_term":
                            amount_credit = 0
                            amount_debit = line.amount * (-1)
                            account_id = payment_term_line.account_id.id
                        lines_to_create.append({
                            'move_id': res_create_storno_move.id,
                            'account_id': account_id,
                            'name': adv_journal_line.name,
                            'debit': amount_debit,
                            'credit': amount_credit,
                            'tax_ids': adv_journal_line.tax_ids,
                        })

                    res_create_lines = move.env['account.move.line'].create(lines_to_create)

                    #post move manually because it cant be directly set when creating
                    res_create_storno_move.action_post()

                    #write storno move id to current move
                    line.storno_move_id = res_create_storno_move.id

                    #when reconciling, dont create exchange difference account move
                    move = move.with_context(no_exchange_difference=True) #dont create exchange rate difference account move

                    #reconcile
                    reconciliation_plan = (payment_term_line + res_create_lines.filtered(lambda line: line.account_id == payment_term_line.account_id))
                    res_reconcile = move.env['account.move.line']._reconcile_plan({reconciliation_plan})

                    #reconcile product line (usually account 2259)
                    advance_invoice_product_line = line.advance_invoice_id.line_ids.filtered(lambda line: line.display_type == "product")
                    storno_invoice_product_line = res_create_lines.filtered(lambda line: line.account_id.code == advance_invoice_product_line.account_id.code)
                    reconciliation_plan_product = (storno_invoice_product_line + advance_invoice_product_line)
                    res_reconcile_product = move.env['account.move.line']._reconcile_plan({reconciliation_plan_product})

                    #check if advance reconciled
                    line.advance_invoice_id._compute_is_advance_reconciled()


    def action_post(self):
        #override post if current invoice has advance lines
        res = super().action_post()
        self._create_advance_refund_invoice()
        return res

    def _compute_is_advance_reconciled(self):
        """Flag if advance invoice (IN or OUT) has been fully reconciled."""
        advance_line_obj = self.env['account.move.advance.line']
        res = dict()
        totals = dict()
        advance_line_domain = [
            ('advance_invoice_id', 'in', self.ids), #tu je bilo ids umjesto self.id
            ('invoice_id.state', 'not in', ['draft', 'cancel'])
        ]
        for advance_line in advance_line_obj.search(advance_line_domain):
            key = advance_line.advance_invoice_id.id
            if key not in totals:
                totals[key] = 0
            totals[key] += advance_line.amount
        for invoice in self:
            if invoice.advance_invoice and invoice.id in totals and totals[invoice.id] == invoice.amount_total:
                invoice.is_advance_reconciled = True
            else:
                invoice.is_advance_reconciled = False


class AccountMoveAdvanceLine(models.Model):
    _name = 'account.move.advance.line'
    _description = 'Account move advance lines'

    invoice_id = fields.Many2one(
        string='Related invoice',
        comodel_name='account.move',
        ondelete='restrict',
    )
    advance_invoice_id = fields.Many2one(
        string='Advance move',
        comodel_name='account.move',
        ondelete='restrict',
        help='Advance invoice related to this invoice. Will be used for reconciliation.'
    )
    advance_move_line_id = fields.Many2one(
        string='Advance move line',
        comodel_name='account.move.line',
        help='Advance move line related to this invoice. Will be used for reconciliation.'
    )
    amount = fields.Float(digits='Account')
    amount_untaxed = fields.Float('Amount untaxed', digits='Account')
    tax_amount = fields.Float('Tax amount', digits='Account')
    storno_move_id = fields.Many2one(
        string='Deduction account move',
        comodel_name='account.move',
    )

    def get_advance_paid_amount(self, field_name, value, invoice_type, context=None):
        """
        Return total advance already deducted from selected invoice / account move line.
        """
        #TODO: return dict to handle case with multiple invoices
        advance_paid = {'total': 0, 'untaxed': 0, 'tax': 0}
        advance_line_ids = self.search([('id', 'not in', self.ids), (field_name, '=', value)]) #možda filtrirati one koji nisu u nacrtu
        for line in advance_line_ids:
            advance_paid['total'] += line.amount
            advance_paid['untaxed'] += line.amount_untaxed
            advance_paid['tax'] += line.tax_amount
        return advance_paid

    @api.onchange('amount', 'advance_invoice_id')
    def onchange_advance_amount(self):
        "Update untaxed amount in case total amount from invoice is changed. Account move line and storno invoice amounts are not updated."
        vals = {}
        if self.advance_invoice_id:
            amount_untaxed = self.amount * self.advance_invoice_id.amount_untaxed / self.advance_invoice_id.amount_total
            vals.update({
                'amount_untaxed': amount_untaxed,
                'tax_amount': self.amount - amount_untaxed,
            })
        return {'value': vals}

    @api.onchange('advance_invoice_id')
    def onchange_advance_invoice(self):
        """
        * Ako je odabran račun za avans:
            - provjerava se koliki iznos je već odbijen s tog računa
            - preostali iznos se zapisuje u amount
            - amount_untaxed se ažurira proporcionalno amountu (ovisno o porezu definiranom na računu)
        * Ako je odabran račun za storno:
            - znamo koje stavke treba zatvoriti
            - ako je uključena opcija za storniranje avansa bez kreiranja računa, na Zatvori stavke će se račun kreirati u pozadini
        * Funkcija se poziva i nakon što se ažurira svaki od gornjih slučajeva, pitanje je da li u tom slučaju treba išta vratiti?
            - ulazni parametri su naziv_polja i False
            - meni se čini da ne treba ništa ažurirati
            - problem je ipak ako se izbrišu sva tri odabira, onda bi trebalo postaviti iznose na 0
        """
        vals = {}
        invoice_obj = self.pool.get('account.invoice')
        advance_paid = self.get_advance_paid_amount('advance_invoice_id', self.advance_invoice_id.id, self.advance_invoice_id.move_type)
        if self.advance_invoice_id:
            vals.update({
                'advance_invoice_id': self.advance_invoice_id,
                'amount': self.advance_invoice_id.amount_total - advance_paid['total'],
                'amount_untaxed': self.advance_invoice_id.amount_untaxed - advance_paid['untaxed'],
                'tax_amount': self.advance_invoice_id.amount_tax - advance_paid['tax'],
                'storno_move_id': False,
            })
        else:
            vals.update({ 'amount': 0.0, 'amount_untaxed': 0.0, 'tax_amount': 0.0 })
        return {'value': vals}


