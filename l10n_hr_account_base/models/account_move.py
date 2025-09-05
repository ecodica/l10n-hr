from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_hr_date_document = fields.Date(
        string="Document Date",
        copy=False,
        help="Date when the document was actually created. "
             "Leave blank for current date.")
    l10n_hr_invoice_time = fields.Char(
        string="Time Of Invoicing",
        copy=False,
        help="Croatia Fiscal datetime value as string, should respect format: hh:mm")
    l10n_hr_invoice_time_extformat = fields.Char(
        string="Time Of Invoicing Extended",
        copy=False,
        help="Croatia Fiscal datetime value as string in fiscal format i.e. extended with seconds, "
             "should respect format: hh:mm:ss. It will serve where seconds are needed e.g."
             "IssueTime for eRacun will be extracted from it."
    )
    l10n_hr_fiscal_number = fields.Char(
        string="Fiscal Number",
        copy=False,
        readonly=True,
        help="Required fiscal number, generated according to "
             "regulations regardless of journal number.")
    # i za ulazne račune se ovdje moze upisati
    l10n_hr_payment_method = fields.Selection(
        selection=[("T", "Bank transfer")],
        string="Croatia - Payment Method",
        default="T",
        help="According to Fiscalization Law and regulative "
             "there are 5 possible options: T, G, K, C, O\n"
             "T - Transaction bank account, is applicable without fiscalization\n"
             " and for other options needed please install fiscalization extension module.")
    l10n_hr_fiscal_device_id = fields.Many2one(
        comodel_name="l10n_hr.fiscal.device",
        string="Fiscal Device",
        help="Device that registers fiscal payment.")
    l10n_hr_fiscal_user_id = fields.Many2one(
        comodel_name="res.partner",
        string="Fiscal User",
        domain=lambda self: self._get_l10n_hr_fiscal_user_id_domain(),
        ondelete='restrict',
        default=lambda self: self.env.user.partner_id.id,
        copy=False,
        help="User who sent the fiscalisation message to FINA."
             " Can be different from responsible person on invoice.",
    )
    l10n_hr_allowed_fiscal_device_ids = fields.Many2many(
        comodel_name="l10n_hr.fiscal.device",
        compute="_compute_l10n_hr_allowed_fiscal_device_ids",
        string="Allowed Fiscal Devices")
    l10n_hr_fiscal_device_visible = fields.Boolean(
        string="Fiscal Device Visible?",
        help="Technical field to show device selection"
             " only if there is something to select"
             " like 2 or more devices for this journal.")
    l10n_hr_show_required_fisk_fields_on_header = fields.Boolean(
        string="Show Required Fiscal Fields on Header?",
        related='company_id.l10n_hr_show_required_fisk_fields_on_header')
    l10n_hr_is_ref_required = fields.Boolean(
        string="Is Ref Required?",
        compute="_compute_l10n_hr_is_ref_required")

    def _get_l10n_hr_fiscal_user_id_domain(self):
        """"Build domain to filter only internal partners."""
        internal_users = self.env.ref('base.group_user')
        domain = [('user_ids', 'in', internal_users.users.ids)]
        return domain

    @api.constrains('l10n_hr_fiscal_number', 'company_id', 'date')
    def _check_l10n_hr_fiscal_number(self):
        for move in self:
            if move.company_id.account_fiscal_country_id.code != "HR" or \
                    move.move_type not in ('out_invoice', 'out_refund'):
                continue
            if not move.l10n_hr_fiscal_number and move.state == 'draft':
                continue
            fiscal_year_dates = move.company_id.compute_fiscalyear_dates(move.date)
            if not fiscal_year_dates.get('date_from') or \
                    not fiscal_year_dates.get('date_to'):
                raise ValidationError(
                    _("Fiscal year %s for company %s has not been properly defined.") % (
                        move.date.year, move.company_id.name)
                )
            existing_move = self.env['account.move'].search([
                ('id', '!=', move.id),
                ('l10n_hr_fiscal_number', '=', move.l10n_hr_fiscal_number),

                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('company_id', '=', move.company_id.id),
                ('date', '>=', fiscal_year_dates.get('date_from')),
                ('date', '<=', fiscal_year_dates.get('date_to')),
            ], limit=1)
            if existing_move:
                raise ValidationError(
                    _("Invoice with fiscal number %s has already been created.") % (move.l10n_hr_fiscal_number)
                )

    @api.depends('move_type', 'company_id')
    def _compute_l10n_hr_is_ref_required(self):
        for move in self:
            move.l10n_hr_is_ref_required = (
                    move.company_id.account_fiscal_country_id.code == "HR"
                    and move.move_type == 'in_invoice'
                    and move.company_id.country_id.code == 'HR'
            )

    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        # TODO: Check if needed in next versions
        res = super()._compute_tax_totals()
        """ Storno hack for Croatia,
            We print Storno invoices with negative amounts,
            So this sets the boolean which triggers for minus sign in lines footer related amounts in
            Tax totals widget
        """
        for move in self:
            if not move.tax_totals:
                continue
            move.tax_totals['l10n_hr_is_storno'] = (
                    move.company_id.account_fiscal_country_id.code == "HR"
                    and move.move_type == "out_refund"
            )

    @api.depends(
        "journal_id",
        "journal_id.l10n_hr_business_premise_id",
        "journal_id.l10n_hr_business_premise_id.l10n_hr_state",
        "journal_id.l10n_hr_fiscal_device_ids",
        "journal_id.l10n_hr_fiscal_device_ids.l10n_hr_state",
    )
    def _compute_l10n_hr_allowed_fiscal_device_ids(self):
        for move in self:
            move.l10n_hr_allowed_fiscal_device_ids = False
            if move.company_id.account_fiscal_country_id.code != "HR":
                continue
            vals = []
            if move.journal_id.l10n_hr_business_premise_id.l10n_hr_state == "active":
                vals = [
                    (4, fd.id)
                    for fd in move.journal_id.l10n_hr_fiscal_device_ids
                    if fd.l10n_hr_state == "active"
                ]

            move.l10n_hr_allowed_fiscal_device_ids = vals
            move.l10n_hr_fiscal_device_visible = len(vals) > 1
            # NOTE: automatically set l10n_hr_fiscal_device_id if only one active records exists
            if len(vals) == 1:
                move.l10n_hr_fiscal_device_id = vals and vals[0][1]

    def l10n_hr_gen_fiscal_number(self):
        self.ensure_one()  # one at a time only!
        premise = self.l10n_hr_fiscal_device_id.l10n_hr_business_premise_id
        device = self.l10n_hr_fiscal_device_id
        if not premise or not device:
            return False
        sequence = (
                premise.l10n_hr_invoice_sequence_by == "P" and premise.l10n_hr_sequence_id or device.l10n_hr_sequence_id
        )
        number = sequence._next(sequence_date=self.date)
        if number.endswith("__"):
            number = number.replace("__", str(device.l10n_hr_fiscal_device_code))
        return number

    def _l10n_hr_post_check(self):
        """
            Inherit for all other controls needed adding a line for each
            missing or wrong entry data for out invoices / refunds needed.
            Better that raising error for each error.
            :return:
        """
        self.ensure_one()
        res = []
        if not self.l10n_hr_fiscal_device_id:
            res.append(_("No active PoS devices found for this journal."))
        if self.l10n_hr_fiscal_device_id.l10n_hr_state != "active":
            res.append(_("PoS device selected is not active."))
        return res

    def _l10n_hr_post_out_invoice(self):
        self.ensure_one()
        l10n_hr_errors = self._l10n_hr_post_check()
        if l10n_hr_errors:
            msg = _("Invoice posting not possible:\n") + "\n".join(l10n_hr_errors)
            raise ValidationError(msg)
        # set date fields
        if not self.l10n_hr_date_document:
            self.l10n_hr_date_document = fields.Date.context_today(self)
        if not self.delivery_date:
            self.delivery_date = fields.Date.context_today(self)
        if not self.date:
            self.date = fields.Date.context_today(self)
        if not self.l10n_hr_invoice_time:
            datum = self.company_id.get_l10n_hr_time_formatted()
            self.l10n_hr_invoice_time = datum["datum_racun"]
            self.l10n_hr_invoice_time_extformat = datum["datum_vrijeme"]
        # set fiscal number
        if not self.invoice_user_id:
            self.invoice_user_id = self.env.user
        if not self.l10n_hr_fiscal_number:
            self.l10n_hr_fiscal_number = self.l10n_hr_gen_fiscal_number()
        # now and set lock on journals,
        # after first posting journal is locked for changes
        if not self.l10n_hr_fiscal_device_id.l10n_hr_lock:
            self.l10n_hr_fiscal_device_id.sudo().write({'l10n_hr_lock': True})
            # self.l10n_hr_fiscal_device_id.lock = True
            if not self.l10n_hr_fiscal_device_id.l10n_hr_business_premise_id.l10n_hr_lock:
                self.l10n_hr_fiscal_device_id.l10n_hr_business_premise_id.sudo().write({'l10n_hr_lock': True})

    @api.depends('country_code', 'move_type')
    def _compute_show_delivery_date(self):
        super()._compute_show_delivery_date()
        for move in self:
            if move.country_code == 'HR':
                move.show_delivery_date = move.is_sale_document()

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        for move in posted:
            if move.company_id.account_fiscal_country_id.code != "HR":
                continue  # only for croatia
            if not move.is_invoice(include_receipts=False):
                continue  # only invoices
            if move.move_type in ("out_invoice", "out_refund"):
                move._l10n_hr_post_out_invoice()
        return posted

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
            Extend to set default sale or purchase journal from partner.
        """
        res = super()._onchange_partner_id()
        if self.company_id.account_fiscal_country_id.code != "HR":
            return res
        if self.partner_id.l10n_hr_sale_journal_id and self.is_sale_document(include_receipts=True):
            self.journal_id = self.partner_id.l10n_hr_sale_journal_id
        elif self.partner_id.l10n_hr_purchase_journal_id and self.is_purchase_document(include_receipts=True):
            self.journal_id = self.partner_id.l10n_hr_purchase_journal_id
        return res

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        res = super()._onchange_journal_id()
        if self.company_id.account_fiscal_country_id.code != "HR":
            return res
        if self.journal_id.l10n_hr_default_fiscal_payment_method:
            self.l10n_hr_payment_method = self.journal_id.l10n_hr_default_fiscal_payment_method
        return res
