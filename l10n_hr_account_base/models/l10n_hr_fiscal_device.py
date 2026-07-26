from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class L10nHrFiscalDevice(models.Model):
    _name = "l10n_hr.fiscal.device"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "PoS device (fiscal device) details"
    _rec_name = 'l10n_hr_name'

    l10n_hr_lock = fields.Boolean(
        string="Lock Device?",
        default=False,
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
    l10n_hr_fiscal_device_code = fields.Integer(  # -> strict integer in xml documents!
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

    _l10n_hr_fiscal_device_uniq = models.Constraint(
        'unique (l10n_hr_fiscal_device_code,l10n_hr_business_premise_id)',
        "The code of the payment register must be unique per business premise!",
    )

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
        account = self.env["account.account"].search([("code", "like", "750000")])
        journal_vals = {
            "sequence": 1,
            "type": "sale",
            "name": "%s-%s"
                    % (self.l10n_hr_business_premise_id.l10n_hr_name,
                       self.l10n_hr_name or str(self.l10n_hr_fiscal_device_code)),
            "refund_sequence": False,
            "code": "INV-%s-%s" % (
                self.l10n_hr_business_premise_id.l10n_hr_fiscal_code, self.l10n_hr_fiscal_device_code),
            "restrict_mode_hash_table": False,
            "l10n_hr_business_premise_id": self.l10n_hr_business_premise_id.id,
            "l10n_hr_fiscal_device_ids": [(4, self.id)],
            "show_on_dashboard": False,
            "default_account_id": account and account[0].id,
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
