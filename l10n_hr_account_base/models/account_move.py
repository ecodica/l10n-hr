from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.sql import drop_index, index_exists



class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_hr_date_document = fields.Date(
        string="Document Date",
        copy=False,
        help="Date when the document was actually created. "
             "Leave blank for current date.")
    l10n_hr_date_delivery = (
        # TODO in 17.0 delivery_date already exits, check if we need custom field
        # for now, we changed label so that we don't get warnings of duplicate fields in logs
        fields.Date(  # to avoid possible name conflict in delivery module!
            string="Date Of Delivery",
            copy=False,
            help="Date of delivery of goods or service. "
                 "Leave blank for current date"))
    l10n_hr_invoice_time = fields.Char(
        # DB: namjerno kao char da izbjegnem timezone problem!
        string="Time Of Invoicing",
        copy=False,
        help="Croatia Fiscal datetime value as string, should respect format: ")
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
             "there is 5 possible options: T, G, K, C, O\n"
             "T - Transaction bank account, is applicable without fiscalization\n"
             " and for other options needed please install fiscalization extension module.")
    l10n_hr_fiscal_device_id = fields.Many2one(
        comodel_name="l10n.hr.fiscal.device",
        string="Fiscal Device",
        help="Device that registers fiscal payment.")
    l10n_hr_allowed_fiscal_device_ids = fields.Many2many(
        comodel_name="l10n.hr.fiscal.device",
        compute="_compute_l10n_hr_allowed_fiscal_device_ids",
        string="Allowed Fiscal Devices")
    l10n_hr_fiscal_device_visible = fields.Boolean(
        string="Fiscal Device Visible?",
        help="Technical field to show device selection"
             " only if there is something to select"
             " like 2 or more devices for this journal.")
    l10n_hr_show_required_fisk_fields_on_header = fields.Boolean(
        string="Show Required Fisk Fields on Header?",
        related='company_id.l10n_hr_show_required_fisk_fields_on_header')
    l10n_hr_is_ref_required = fields.Boolean(
        string="Is Ref Required?",
        compute="_compute_l10n_hr_is_ref_required")

    _sql_constraints = [
        (
            'unique_name', "", "Another entry with the same name already exists.",
        ), 
        (
            'unique_name_l10n_hr', "", "Another entry with the same name already exists.",
        )
    ]

    def _auto_init(self):
        super()._auto_init()
        # NOTE: in Croatia, sequences for outgoing invoices are reset each year and there can be
        # invoices with same number in database. Only constraint is that outgoing invoice must be
        # unique inside fiscal year. This override will force custom constraint for outgoing invoices
        # but we will keep Odoo's constraints for all other move types
        if not index_exists(self.env.cr, "account_move_unique_name_l10n_hr"):
            drop_index(self.env.cr, "account_move_unique_name", self._table)
            self.env.cr.execute("""CREATE UNIQUE INDEX account_move_unique_name
                ON account_move(name, journal_id)
                WHERE (state = 'posted' AND name != '/' AND move_type NOT IN ('out_invoice', 'out_refund'));
                CREATE UNIQUE INDEX account_move_unique_name_l10n_hr
                ON account_move(name, company_id, extract(year from date))
                WHERE (state = 'posted' AND name != '/' AND move_type IN ('out_invoice', 'out_refund'));
            """)

    @api.depends('move_type', 'company_id')
    def _compute_l10n_hr_is_ref_required(self):
        for move in self:
            if move.company_id.account_fiscal_country_id.code != "HR":
                continue
            move.l10n_hr_is_ref_required = move.move_type == 'in_invoice' and move.company_id.country_id.code == 'HR'

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
        res = super()._compute_tax_totals()
        """ Storno hack for Croatia,
        We print Storno invoices with negative amounts,
        So this sets the minus sign in formatted text values
        Second part of this hack is in qweb view, adding the same
        for quantity and amount  fields.
        """

        def add_minus(s):
            return "- " + s
        for move in self:
            if move.company_id.account_fiscal_country_id.code != "HR":
                continue
            if (
                move.move_type == "out_refund"
                and self.company_id.account_fiscal_country_id.code == "HR"
            ):
                totals = move.tax_totals
                totals["formatted_amount_total"] = add_minus(
                    totals["formatted_amount_total"]
                )
                totals["formatted_amount_untaxed"] = add_minus(
                    totals["formatted_amount_untaxed"]
                )
                for st in totals["subtotals"]:
                    st["formatted_amount"] = add_minus(st["formatted_amount"])
                for sg in totals["groups_by_subtotal"].keys():
                    cgt = totals["groups_by_subtotal"][sg]
                    for group in cgt:
                        group["formatted_tax_group_amount"] = add_minus(
                            group["formatted_tax_group_amount"]
                        )
                        group["formatted_tax_group_base_amount"] = add_minus(
                            group["formatted_tax_group_base_amount"]
                        )
                move.tax_totals = totals
            # return res

    @api.depends(
        "journal_id",
        "journal_id.l10n_hr_business_premise_id",
        "journal_id.l10n_hr_business_premise_id.l10n_hr_state",
        "journal_id.l10n_hr_fiscal_device_ids",
        "journal_id.l10n_hr_fiscal_device_ids.l10n_hr_state",
    )
    def _compute_l10n_hr_allowed_fiscal_device_ids(self):
        for move in self:
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

    def _gen_fiscal_number(self):
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
        if not self.l10n_hr_date_delivery:
            self.l10n_hr_date_delivery = fields.Date.context_today(self)
        if not self.date:
            self.date = fields.Date.context_today(self)
        if not self.l10n_hr_invoice_time:  # depend na l10n_hr_base?
            # DEV NOTE: mozda i ostaviti datetime field? za sad.. char
            datum = self.company_id.get_l10n_hr_time_formatted()
            self.l10n_hr_invoice_time = datum["datum_racun"]
        # set fiskal number
        if not self.invoice_user_id:
            self.invoice_user_id = self.env.user
        if not self.l10n_hr_fiscal_number:
            self.l10n_hr_fiscal_number = self._gen_fiscal_number()
        # now and set lock on journals,
        # after first posting journal is locked for changes
        if not self.l10n_hr_fiscal_device_id.l10n_hr_lock:
            self.l10n_hr_fiscal_device_id.sudo().write({'l10n_hr_lock': True})
            #self.l10n_hr_fiscal_device_id.lock = True
            if not self.l10n_hr_fiscal_device_id.l10n_hr_business_premise_id.l10n_hr_lock:
                self.l10n_hr_fiscal_device_id.l10n_hr_business_premise_id.sudo().write({'l10n_hr_lock': True})

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
