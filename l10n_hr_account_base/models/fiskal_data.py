from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class FiskalProstor(models.Model):
    _name = "l10n.hr.fiskal.prostor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Croatia business premisses"

    lock = fields.Boolean(
        tracking=1,
        help="Once the first invoice is confirmed, "
        "business premise code and invoice sequence should not be changed",
    )
    name = fields.Char(required=True, size=128, tracking=1)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required="True",
        default=lambda self: self.env.company,
    )
    oznaka_prostor = fields.Char(
        string="Fiscal Code",
        required="True",
        size=20,
        tracking=1,
        help="Will be used as second part of fiscal invoice number",
    )
    sljed_racuna = fields.Selection(
        selection=[("N", "On PoS device level"), ("P", "On business premise level")],
        string="Sequence by",
        required="True",
        default="P",
        tracking=1,
    )
    mjesto_izdavanja = fields.Char(
        string="Place of invoicing",  # required="True",
        tracking=1,
        help="It will be used as place of invoicing for this premise, "
        " as a legaly required element",
    )
    uredjaj_ids = fields.One2many(
        comodel_name="l10n.hr.fiskal.uredjaj",
        inverse_name="prostor_id",
        string="PoS devices",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("pause", "Paused"),
            ("closed", "Closed"),
        ],
        default="draft",
        tracking=1,
    )
    journal_ids = fields.One2many(
        comodel_name="account.journal",
        inverse_name="l10n_hr_prostor_id",
        string="Journals in this premisse",
        context={"active_test": False},  # want to see inactive in tree view
        help="Used invoicing journals in this business premisse",
    )
    sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        name="Sequence",
        check_company=True,
        domain=[("code", "=", "l10n_hr.fiscal")],
        help="Is invoicing sequence is premisse based, (P)"
        "this is number sequence is used as first part of "
        "invoice fiscal number",
    )

    _sql_constraints = [
        (
            "fiskal_prostor_uniq",
            "unique (oznaka_prostor,company_id)",
            "The code of the business premise must be unique per company !",
        )
    ]

    def _get_sequence_fiskal_code(self, pos=None):
        self.ensure_one()
        if pos is None:
            pos = "__"
        if self.sljed_racuna == "N" and pos == "__":
            # error? or just pass it
            pass
        code = self.company_id.l10n_hr_fiskal_separator.join(
            ("", self.oznaka_prostor, str(pos))
        )
        return code

    def _create_sequence(self, pos_code=None):
        self.ensure_one()
        sequence_code = self._get_sequence_fiskal_code(pos_code)
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
            % (self.name, self.sljed_racuna, sequence_code),
            "prefix": False,
            "suffix": sequence_code,
            "use_date_range": True,
            "date_range_ids": date_range,
        }
        seq = self.env["ir.sequence"].create(sequence_vals)
        return seq

    def _check_sequence(self, sequence):
        if not sequence:
            self.sequence_id = self._create_sequence()
            return
        if sequence.prefix or sequence.suffix:
            raise UserError(_("Fiscal sequence should not contain prefix nor suffix"))
        # TODO:
        # is it used in another premisse?

    def button_activate_premisse(self):
        self.ensure_one()
        if not self.uredjaj_ids:
            raise ValidationError(
                _("Business premisse cannot be activated without existing PoS devices!")
            )
        if self.sljed_racuna == "P":
            self._check_sequence(self.sequence_id)
        else:  # sljed_racuna == 'N'
            self.sequence_id = False
        self.state = "active"
        # finaly activate PoS devices waiting for premisse to become active
        waiting = self.uredjaj_ids.filtered(lambda u: u.state == "wait")
        waiting.journal_ids.show_on_dashboard = True
        waiting.state = "active"

    def button_pause_premisse(self):
        self.ensure_one()
        self.uredjaj_ids.button_pause()
        self.state = "pause"

    def button_close_premisse(self):
        self.ensure_one()
        self.uredjaj_ids.button_close_device()
        if self.sequence_id:
            self.sequence_id.active = False
        self.state = "closed"

    @api.model
    def unlink(self):
        for ured in self:
            if ured.lock:
                raise ValidationError(
                    _(
                        "Deleting PoS device with confirmed invoices is not possible! "
                        "Try deactivating instead."
                    )
                )
        return super().unlink()


class FiskalUredjaj(models.Model):
    _name = "l10n.hr.fiskal.uredjaj"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "PoS device details"

    lock = fields.Boolean(
        default=False,
        tracking=1,
        help="After first invoice is confirmed, no more changes!",
    )
    name = fields.Char(string="PoS name", tracking=1)
    prostor_id = fields.Many2one(
        comodel_name="l10n.hr.fiskal.prostor",
        string="Business Premisse",
        help="Business premisee where this device is operating",
        ondelete="restrict",
    )
    sljed_racuna = fields.Selection(
        string="Sequence by", store=True, related="prostor_id.sljed_racuna"
    )
    oznaka_uredjaj = fields.Integer(  # -> kad se šalje xml onda strict integer!
        string="Device code",
        required="True",
        tracking=1,
        help="Only integer number values allowed, without leading zeroes.",
    )
    mjesto_izdavanja = fields.Char(
        string="Place of invoicing",
        tracking=1,
        help="If not entered, Premisse invicing place will be used, "
        " as a legaly required element",
    )
    possible_journal_ids = fields.Many2many(
        comodel_name="account.journal", compute="_compute_possible_journal_ids"
    )
    journal_ids = fields.Many2many(
        comodel_name="account.journal",
        relation="l10n_hr_fiskal_uredjaj_account_journal_rel",
        column1="uredjaj_id",
        column2="journal_id",
        string="Allowed journals",
        domain="[('type', 'in', ['sale','sale_refund'])]",
    )
    sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        name="Sequence",
        domain=[("code", "=", "l10n_hr.fiscal")],
        help="Shoud be defined with no prefix or suffix, used only for this PoS",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("wait", "Waiting Premisse"),  # activated before the premisse
            ("pause", "Paused"),
            ("close", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=1,
    )

    _sql_constraints = [
        (
            "fiskal_uredjaj_uniq",
            "unique (oznaka_uredjaj,prostor_id)",
            "The code of the payment register must be unique per business premise !",
        )
    ]

    @api.depends(
        "prostor_id", "prostor_id.uredjaj_ids", "prostor_id.uredjaj_ids.journal_ids"
    )
    def _compute_possible_journal_ids(self):
        for pos in self:
            domain = [("l10n_hr_prostor_id", "=", pos.prostor_id.id)]
            # if pos.sljed_racuna == 'N':
            # TODO: fetch journals possible for this premise

    @api.onchange("prostor_id")
    def on_change_prostor_id(self):
        if self.prostor_id:
            self.oznaka_uredjaj = len(self.prostor_id.uredjaj_ids)
            # self.oznaka_uredjaj += self._context.get('default_prostor_id') and 0 or 1

    # Methods
    def name_get(self):
        return [(u.id, "%s-%s" % (u.prostor_id.name, u.name)) for u in self]

    @api.model
    def unlink(self):
        if self.filtered(lambda s: s.lock == True):
            raise ValidationError(
                _(
                    "Not allowed to delete PoS device with invoices related, please deactivate it instead!"
                )
            )
        return super(FiskalUredjaj, self).unlink()

    def _get_new_journal_vals(self):
        account = self.env["account.account"].search([("code", "like", "750000")])
        account = account and account[0]
        journal_vals = {
            "sequence": 1,
            "type": "sale",
            "name": "%s-%s"
            % (self.prostor_id.name, self.name or str(self.oznaka_uredjaj)),
            "refund_sequence": False,
            "code": "INV-%s-%s" % (self.prostor_id.oznaka_prostor, self.oznaka_uredjaj),
            "restrict_mode_hash_table": False,  # HEADS UP! should be true but...
            "l10n_hr_prostor_id": self.prostor_id.id,
            "l10n_hr_fiskal_uredjaj_ids": [(4, self.id)],
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
        for pos in self:
            if not pos.journal_ids:
                self._create_new_journal()
            no_good = []
            for jrnl in pos.journal_ids:
                if not jrnl.l10n_hr_prostor_id:
                    jrnl.l10n_hr_prostor_id = pos.prostor_id

                if (
                    jrnl.l10n_hr_prostor_id
                    and jrnl.l10n_hr_prostor_id != pos.prostor_id
                ):
                    no_good.append(
                        (
                            "Journal shared with other premisse",
                            jrnl.display_name,
                            jrnl.l10n_hr_prostor_id.display_name,
                        )
                    )
                if pos.sljed_racuna == "N":
                    if jrnl.l10n_hr_fiskal_uredjaj_ids.ids != [pos.id]:
                        no_good.append(
                            (
                                "Journal shared with other PoS",
                                jrnl.display_name,
                                jrnl.l10n_hr_prostor_id.display_name,
                            )
                        )

            if no_good:
                msg = "\n".join(["%s - %s (%s) !" % line for line in no_good])
                raise ValidationError(msg)

            if pos.sljed_racuna == "N":
                if not pos.sequence_id:
                    pos.sequence_id = pos.prostor_id._create_sequence(
                        pos.oznaka_uredjaj
                    )
            else:
                pos.sequence_id = False

            if pos.prostor_id.state != "active":
                pos.state = "wait"
            else:
                pos.state = "active"
                pos.journal_ids.write({"show_on_dashboard": True})

    def button_pause_device(self):
        for pos in self:
            pos.journal_ids.write({"show_on_dashboard": False})
            pos.state = "pause"

    def button_close_device(self):
        for pos in self:
            if pos.sequence_id:
                pos.sequence_id.active = False
            pos.journal_ids.write({"show_on_dashboard": False})
            pos.state = "close"
