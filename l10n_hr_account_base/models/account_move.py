from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.sql import drop_index, index_exists



class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def get_default_l10n_hr_account_payment_type(self):
        """ Try to return 'Bank Transfer' as default payment type """
        return self.env.ref('l10n_hr_account_base.l10n_hr_account_payment_type_T', raise_if_not_found=False)

    l10n_hr_date_document = fields.Date(
        string="Document Date",
        copy=False,
        help="Date when the document was actually created. "
        "Leave blank for current date",
    )
    l10n_hr_date_delivery = (
        # TODO in 17.0 delivery_date already exits, check if we need custom field
        # for now, we changed label so that we don't get warnings of duplicate fields in logs
        fields.Date(  # to avoid possible name conflict in delivery module!
            string="Date Of Delivery",
            copy=False,
            help="Date of delivery of goods or service. "
            "Leave blank for current date",
        )
    )
    l10n_hr_vrijeme_izdavanja = fields.Datetime(
        # DB: used to be char, changed to Datetime!
        string="Time Of Invoicing",
        copy=False,
        help="Croatia Fiskal datetime",
    )
    l10n_hr_fiskalni_broj = fields.Char(
        string="Fiskal Number",
        copy=False,
        readonly=True,
        help="Required fiscal number, generated according to "
        "regulations regardless of journal number",
    )
    l10n_hr_fiskal_user_id = fields.Many2one(
        comodel_name="res.partner",
        string="Fiscal User",
        domain=lambda self: self._get_l10n_hr_fiskal_user_id_domain(),
        default=lambda self: self.env.user.partner_id.id,
        ondelete='restrict',
        copy=False,
        help="User who sent the fiscalisation message to FINA."
        " Can be different from responsible person on invoice.",
    )
    l10n_hr_account_payment_type_id = fields.Many2one(
        comodel_name='l10n_hr.account.payment.type',
        string="Croatia Payment Means",
        ondelete="restrict",
        default=lambda self: self.get_default_l10n_hr_account_payment_type()
    )
    l10n_hr_fiskal_uredjaj_id = fields.Many2one(
        comodel_name="l10n.hr.fiskal.uredjaj",
        string="Fiskal Device",
        help="Device on which is fiscal payment registred",
    )
    l10n_hr_allowed_fiskal_uredjaj_ids = fields.Many2many(
        comodel_name="l10n.hr.fiskal.uredjaj",
        compute="_compute_allowed_fiskal_device",
        string="Alowed Fiskal Device",
    )
    l10n_hr_fiskal_uredjaj_visible = fields.Boolean(
        help="Technical field to show device selection"
        " only if there is something to select"
        " like 2 or more devices for this journal",
    )
    l10n_hr_show_required_fisk_fields_on_header = fields.Boolean(
        related='company_id.l10n_hr_show_required_fisk_fields_on_header')
    l10n_hr_is_ref_required = fields.Boolean(
        compute="_compute_l10n_hr_is_ref_required"
    )
    l10n_hr_allowed_payment_type_ids = fields.Many2many(
            'l10n_hr.account.payment.type',
            compute='_compute_l10n_hr_allowed_payment_types'
        )

    _sql_constraints = [(
        'unique_name', "", "Another entry with the same name already exists.",
    ), (
        'unique_name_l10n_hr', "", "Another entry with the same name already exists.",
    )]

    @api.depends('l10n_hr_fiskal_uredjaj_id')
    def _compute_l10n_hr_allowed_payment_types(self):
        """
        Compute allowed payment types if set on fiskal uredjaj and
        reset payment type only if the device has a restricted list and current is not in it
        """
        all_payment_types = self.env['l10n_hr.account.payment.type'].search([('active', '=', True)])

        for move in self:
            # 1. Update the allowed types
            fiskal_uredjaj = move.l10n_hr_fiskal_uredjaj_id
            allowed = fiskal_uredjaj.allowed_payment_type_ids if fiskal_uredjaj and fiskal_uredjaj.allowed_payment_type_ids else all_payment_types
            move.l10n_hr_allowed_payment_type_ids = allowed

            # 2. Reset the selected payment type if it's no longer valid
            if move.l10n_hr_account_payment_type_id and move.l10n_hr_account_payment_type_id not in allowed:
                move.l10n_hr_account_payment_type_id = False

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
        "journal_id.l10n_hr_prostor_id",
        "journal_id.l10n_hr_prostor_id.state",
        "journal_id.l10n_hr_fiskal_uredjaj_ids",
        "journal_id.l10n_hr_fiskal_uredjaj_ids.state",
    )
    def _compute_allowed_fiskal_device(self):
        for move in self:
            vals = []
            if move.journal_id.l10n_hr_prostor_id.state == "active":
                vals = [
                    (4, fd.id)
                    for fd in move.journal_id.l10n_hr_fiskal_uredjaj_ids
                    if fd.state == "active"
                ]

            move.l10n_hr_allowed_fiskal_uredjaj_ids = vals
            move.l10n_hr_fiskal_uredjaj_visible = len(vals) > 1
            # NOTE: automatically set l10n_hr_fiskal_uredjaj_id if only one active records exists
            if len(vals) == 1:
                move.l10n_hr_fiskal_uredjaj_id = vals and vals[0][1]

    def _get_l10n_hr_fiskal_user_id_domain(self):
        """"Build domain to filter only internal partners."""
        internal_users = self.env.ref('base.group_user')
        domain = [('user_ids', 'in', internal_users.users.ids)]
        return domain

    def _must_check_constrains_date_sequence(self):
        """Extend to skip check if l10n_hr_fiskal_uredjaj_id is set."""
        # NOTE: fiskal number are specific and they don't have date reference in them so we can skip that check
        if self.l10n_hr_fiskal_uredjaj_id:
            return False
        return super()._must_check_constrains_date_sequence()

    def _gen_fiskal_number(self):
        self.ensure_one()  # one at a time only!
        prostor = self.l10n_hr_fiskal_uredjaj_id.prostor_id
        uredjaj = self.l10n_hr_fiskal_uredjaj_id
        if not prostor or not uredjaj:
            return False
        sequence = (
            prostor.sljed_racuna == "P" and prostor.sequence_id or uredjaj.sequence_id
        )
        broj = sequence._next(sequence_date=self.date)
        if broj.endswith("__"):
            broj = broj.replace("__", str(uredjaj.oznaka_uredjaj))
        return broj

    def _l10n_hr_post_check(self):
        """
        Inherit for all other controls needed adding a line for each
        missing or wrong entry data for out invoices / refunds needed
        Better that raising error for each error
        :return:
        """
        self.ensure_one()
        res = []
        if not self.l10n_hr_fiskal_uredjaj_id:
            res.append(_("No active PoS devices found for this journal"))
        if self.l10n_hr_fiskal_uredjaj_id.state != "active":
            res.append(_("PoS device selected is not active"))
        if not self.l10n_hr_account_payment_type_id:
            res.append(_("Payment method not selected"))
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
        if not self.l10n_hr_vrijeme_izdavanja:  # depend na l10n_hr_base?
            # DEV NOTE: mozda i ostaviti datetime field? za sad.. char
            datum = self.company_id.get_l10n_hr_datetime()
            self.l10n_hr_vrijeme_izdavanja = datum["server_datetime"]
        # set fiskal number
        if not self.invoice_user_id:
            self.invoice_user_id = self.env.user
        if not self.l10n_hr_fiskalni_broj:
            self.l10n_hr_fiskalni_broj = self._gen_fiskal_number()
        # now and set lock on journals,
        # after first posting journal is locked for changes
        if not self.l10n_hr_fiskal_uredjaj_id.lock:
            self.l10n_hr_fiskal_uredjaj_id.sudo().write({'lock': True})
            #self.l10n_hr_fiskal_uredjaj_id.lock = True
            if not self.l10n_hr_fiskal_uredjaj_id.prostor_id.lock:
                self.l10n_hr_fiskal_uredjaj_id.prostor_id.sudo().write({'lock': True})

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
        """Extend to set default sale or purchase journal from partner."""
        res = super()._onchange_partner_id()
        if self.partner_id.sale_journal_id and self.is_sale_document(include_receipts=True):
            self.journal_id = self.partner_id.sale_journal_id
        elif self.partner_id.purchase_journal_id and self.is_purchase_document(include_receipts=True):
            self.journal_id = self.partner_id.purchase_journal_id
        return res

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        res = super()._onchange_journal_id()
        if self.journal_id.l10n_hr_default_account_payment_type_id:
            self.l10n_hr_account_payment_type_id = self.journal_id.l10n_hr_default_account_payment_type_id
        return res
