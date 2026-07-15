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

    _l10n_hr_business_premise_uniq = models.Constraint(
        'unique (l10n_hr_fiscal_code,company_id)',
        "The code of the business premise must be unique per company!",
    )

    def _get_sequence_fiscal_code(self, pos=None):
        self.ensure_one()
        if pos is None:
            pos = "__"
        if self.l10n_hr_invoice_sequence_by == "N" and pos == "__":
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
        # if sequence.prefix or sequence.suffix:
        #     raise UserError(_("Fiscal sequence should not contain prefix nor suffix."))
        # TODO: is it used in another premise?

    def button_activate_premise(self):
        self.ensure_one()
        if not self.l10n_hr_fiscal_device_ids:
            raise ValidationError(
                _("Business premise cannot be activated without existing PoS devices!")
            )
        if self.l10n_hr_invoice_sequence_by == "P":
            self._check_sequence(self.l10n_hr_sequence_id)
        else:
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
