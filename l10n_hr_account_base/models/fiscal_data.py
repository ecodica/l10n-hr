from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class L10nHrBusinessPremise(models.Model):
    _name = "l10n_hr.business.premise"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Croatia business premises"
    _rec_name = 'l10n_hr_name'
    _check_company_auto = True

    l10n_hr_lock = fields.Boolean(
        string="Lock Premise?",
        tracking=1,
        help="Once the first invoice is confirmed, "
             "business premise code and invoice sequence should not be changed.")
    l10n_hr_name = fields.Char(
        string="Business Premise", 
        required=True, 
        size=128, 
        tracking=1)
    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company)
    l10n_hr_fiscal_code = fields.Char(
        string="Fiscal Code",
        required=True,
        size=20,
        tracking=1,
        help="Will be used as second part of fiscal invoice number.")
    l10n_hr_invoice_sequence_by = fields.Selection(
        selection=[
            ("N", "On PoS device level"), 
            ("P", "On business premise level")],
        string="Sequence By",
        required=True,
        default="P",
        tracking=1)
    l10n_hr_invoice_place = fields.Char(
        string="Place Of Invoicing",  # required="True",
        tracking=1,
        help="It will be used as place of invoicing for this premise, "
             " as a legally required element.")
    l10n_hr_fiscal_device_ids = fields.One2many(
        comodel_name="l10n_hr.fiscal.device",
        inverse_name="l10n_hr_business_premise_id",
        string="PoS Devices")
    l10n_hr_state = fields.Selection(
        string="State",
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("pause", "Paused"),
            ("closed", "Closed"),
        ],
        default="draft",
        tracking=1)
    l10n_hr_journal_ids = fields.One2many(
        comodel_name="account.journal",
        inverse_name="l10n_hr_business_premise_id",
        string="Journals In This Premise",
        context={"active_test": False},  # want to see inactive in tree view
        help="Used invoicing journals in this business premise.")
    l10n_hr_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Sequence",
        check_company=True,
        domain=[("code", "=", "l10n_hr.fiscal")],
        help="Is invoicing sequence is premise based, (P)"
             "this is number sequence is used as first part of "
             "invoice fiscal number.")

    _sql_constraints = [
        (
            "l10n_hr_business_premise_uniq",
            "unique (l10n_hr_fiscal_code,company_id)",
            "The code of the business premise must be unique per company!",
        )
    ]

    def _get_sequence_fiscal_code(self, pos=None):
        self.ensure_one()
        if pos is None:
            pos = "__"
        if self.l10n_hr_invoice_sequence_by == "N" and pos == "__":
            # error? or just pass it
            pass
        code = self.company_id.l10n_hr_fiscal_separator.join(
            ("", self.l10n_hr_fiscal_code, str(pos))
        )
        return code

    def _create_sequence(self, pos_code=None):
        self.ensure_one()
        sequence_code = self._get_sequence_fiscal_code(pos_code)
        current_date = fields.Date.today()
        n_years, n = 3, 0
        date_range = []
        year = current_date.year
        while n < n_years:
            date_range.append(
                (
                    0,
                    0,
                    {
                        "date_from": "%s-%s-%s" % (year + n, "01", "01"),
                        "date_to": "%s-%s-%s" % (year + n, "12", "31"),
                        "number_next": 1,
                    },
                )
            )
            n += 1
        sequence_vals = {
            "implementation": "no_gap",
            "code": "l10n_hr.fiscal",
            "name": "IRA %s - %s - (%s)"
            % (self.l10n_hr_name, self.l10n_hr_invoice_sequence_by, sequence_code),
            "prefix": False,
            "suffix": sequence_code,
            "use_date_range": True,
            "date_range_ids": date_range,
        }
        seq = self.env["ir.sequence"].create(sequence_vals)
        return seq

    def _check_sequence(self, sequence):
        if not sequence:
            self.l10n_hr_sequence_id = self._create_sequence()
            return
        if sequence.prefix or sequence.suffix:
            raise UserError(_("Fiscal sequence should not contain prefix nor suffix."))
        # TODO:
        # is it used in another premise?

    def button_activate_premise(self):
        self.ensure_one()
        if not self.l10n_hr_fiscal_device_ids:
            raise ValidationError(
                _("Business premise cannot be activated without existing PoS devices!")
            )
        if self.l10n_hr_invoice_sequence_by == "P":
            self._check_sequence(self.l10n_hr_sequence_id)
        else:  # sljed_racuna == 'N'
            self.l10n_hr_sequence_id = False
        self.l10n_hr_state = "active"
        # finally activate PoS devices waiting for premise to become active
        waiting = self.l10n_hr_fiscal_device_ids.filtered(lambda u: u.l10n_hr_state == "wait")
        waiting.l10n_hr_journal_ids.show_on_dashboard = True
        waiting.l10n_hr_state = "active"

    def button_pause_premise(self):
        self.ensure_one()
        self.l10n_hr_fiscal_device_ids.button_pause_device()
        self.l10n_hr_state = "pause"

    def button_close_premise(self):
        self.ensure_one()
        self.l10n_hr_fiscal_device_ids.button_close_device()
        if self.l10n_hr_sequence_id:
            self.l10n_hr_sequence_id.active = False
        self.l10n_hr_state = "closed"

    def unlink(self):
        for premise in self:
            if premise.l10n_hr_lock:
                raise ValidationError(
                    _(
                        "Deleting PoS device with confirmed invoices is not possible! "
                        "Try deactivating instead."
                    )
                )
        return super().unlink()


class L10nHrFiscalDevice(models.Model):
    _name = "l10n_hr.fiscal.device"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "PoS device (fiscal device) details"
    _rec_name = 'l10n_hr_name'

    l10n_hr_lock = fields.Boolean(
        string="Lock Device?",
        default=False,
        # tracking=1,
        help="After first invoice is confirmed, no more changes!")
    l10n_hr_name = fields.Char(string="PoS Name", tracking=1)
    l10n_hr_business_premise_id = fields.Many2one(
        comodel_name="l10n_hr.business.premise",
        string="Business Premise",
        help="Business premise where this device is operating.",
        ondelete="restrict")
    l10n_hr_invoice_sequence_by = fields.Selection(
        string="Sequence By", 
        store=True, 
        related="l10n_hr_business_premise_id.l10n_hr_invoice_sequence_by")
    l10n_hr_fiscal_device_code = fields.Integer(  # -> kad se šalje xml onda strict integer!
        string="Device Code",
        required=True,
        tracking=1,
        help="Only integer number values allowed, without leading zeroes.")
    l10n_hr_invoice_place = fields.Char(
        string="Place Of Invoicing",
        tracking=1,
        help="If not entered, Premise invoicing place will be used, "
             " as a legally required element.")
    l10n_hr_possible_journal_ids = fields.Many2many(
        string="Possible Journals",
        comodel_name="account.journal", 
        compute="_compute_possible_journal_ids")
    l10n_hr_journal_ids = fields.Many2many(
        comodel_name="account.journal",
        relation="l10n_hr_fiscal_device_account_journal_rel",
        column1="l10n_hr_fiscal_device_id",
        column2="l10n_hr_journal_id",
        string="Allowed Journals",
        domain="[('type', 'in', ['sale','sale_refund'])]")
    l10n_hr_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        name="Sequence",
        domain=[("code", "=", "l10n_hr.fiscal")],
        help="Should be defined with no prefix or suffix, used only for this PoS.")
    l10n_hr_state = fields.Selection(
        string="State",
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("wait", "Waiting Premise"),  # activated before the premise
            ("pause", "Paused"),
            ("close", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=1)

    _sql_constraints = [
        (
            "l10n_hr_fiscal_device_uniq",
            "unique (l10n_hr_fiscal_device_code,l10n_hr_business_premise_id)",
            "The code of the payment register must be unique per business premise!",
        )
    ]

    @api.depends(
        "l10n_hr_business_premise_id", 
        "l10n_hr_business_premise_id.l10n_hr_fiscal_device_ids", 
        "l10n_hr_business_premise_id.l10n_hr_fiscal_device_ids.l10n_hr_journal_ids"
    )
    def _compute_possible_journal_ids(self):
        for device in self:
            domain = [("l10n_hr_business_premise_id", "=", device.l10n_hr_business_premise_id.id)]
            # if pos.sljed_racuna == 'N':
            # TODO: fetch journals possible for this premise

    @api.onchange("l10n_hr_business_premise_id")
    def on_change_l10n_hr_business_premise_id(self):
        if self.l10n_hr_business_premise_id:
            self.l10n_hr_fiscal_device_code = len(self.l10n_hr_business_premise_id.l10n_hr_fiscal_device_ids)
            # self.oznaka_uredjaj += self._context.get('default_prostor_id') and 0 or 1

    # Methods
    def name_get(self):
        return [(u.id, "%s-%s" % (u.l10n_hr_business_premise_id.l10n_hr_name, u.l10n_hr_name)) for u in self]

    def unlink(self):
        if self.filtered(lambda s: s.l10n_hr_lock == True):
            raise ValidationError(
                _(
                    "Not allowed to delete PoS device with invoices related, please deactivate it instead!"
                )
            )
        return super().unlink()

    def _get_new_journal_vals(self):
        # TODO: Remove hardcoded values
        account = self.env["account.account"].search(
            [("code", "like", "750000")])
        account = account and account[0]
        journal_vals = {
            "sequence": 1,
            "type": "sale",
            "name": "%s-%s"
            % (self.l10n_hr_business_premise_id.l10n_hr_name, self.l10n_hr_name or str(self.l10n_hr_fiscal_device_code)),
            "refund_sequence": False,
            "code": "INV-%s-%s" % (self.l10n_hr_business_premise_id.l10n_hr_fiscal_code, self.l10n_hr_fiscal_device_code),
            "restrict_mode_hash_table": False,  # HEADS UP! should be true but...
            "l10n_hr_business_premise_id": self.l10n_hr_business_premise_id.id,
            "l10n_hr_fiscal_device_ids": [(4, self.id)],
            "show_on_dashboard": False,
            # TODO: correct account setup if possible!
            #  hardcoded for now based on RRIF CoA
            "default_account_id": account and account.id,
            # 'invoice_reference_model': 'hr', -> inheritable but not set here
        }
        return journal_vals

    def _create_new_journal(self):
        self.ensure_one()
        journal_vals = self._get_new_journal_vals()
        self.env["account.journal"].create(journal_vals)

    def button_activate_device(self):
        for device in self:
            if not device.l10n_hr_journal_ids:
                self._create_new_journal()
            no_good = []
            for journal in device.l10n_hr_journal_ids:
                if not journal.l10n_hr_business_premise_id:
                    journal.l10n_hr_business_premise_id = device.l10n_hr_business_premise_id
                if (
                    journal.l10n_hr_business_premise_id
                    and journal.l10n_hr_business_premise_id != device.l10n_hr_business_premise_id
                ):
                    no_good.append(
                        (
                            "Journal shared with other premise",
                            journal.display_name,
                            journal.l10n_hr_business_premise_id.display_name,
                        )
                    )
                if device.l10n_hr_invoice_sequence_by == "N":
                    if journal.l10n_hr_fiscal_device_ids.ids != [device.id]:
                        no_good.append(
                            (
                                "Journal shared with other PoS",
                                journal.display_name,
                                journal.l10n_hr_business_premise_id.display_name,
                            )
                        )

            if no_good:
                msg = "\n".join(["%s - %s (%s) !" % line for line in no_good])
                raise ValidationError(msg)

            if device.l10n_hr_invoice_sequence_by == "N":
                if not device.l10n_hr_sequence_id:
                    device.l10n_hr_sequence_id = device.l10n_hr_business_premise_id._create_sequence(
                        device.l10n_hr_fiscal_device_code)
            else:
                device.l10n_hr_sequence_id = False

            if device.l10n_hr_business_premise_id.l10n_hr_state != "active":
                device.l10n_hr_state = "wait"
            else:
                device.l10n_hr_state = "active"
                device.l10n_hr_journal_ids.write({"show_on_dashboard": True})

    def button_pause_device(self):
        for device in self:
            device.l10n_hr_journal_ids.write({"show_on_dashboard": False})
            device.l10n_hr_state = "pause"

    def button_close_device(self):
        for device in self:
            if device.l10n_hr_sequence_id:
                device.l10n_hr_sequence_id.active = False
            device.l10n_hr_journal_ids.write({"show_on_dashboard": False})
            device.l10n_hr_state = "close"
