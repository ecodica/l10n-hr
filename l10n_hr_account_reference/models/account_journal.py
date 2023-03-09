from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

REF_CROATIA = ["00", "01", "02", "03", "06"]


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.constrains("invoice_reference_model", "invoice_reference_type")
    def _l10n_constrain_pnb_model(self):
        for record in self:
            if (
                record.invoice_reference_type == "hr"
                and record.invoice_reference_model not in REF_CROATIA
            ) or (
                record.invoice_reference_type != "hr"
                and record.invoice_reference_model in REF_CROATIA
            ):
                raise ValidationError(
                    _(
                        "Both Communication standard and Communication type,"
                        " should be Croatia or not Croatia, mix is not possible!"
                    )
                )

    def _get_P1_P4_selection(self):
        return [
            ("move_id", "Invoice database id"),  # solid unique reference part!
            ("partner_code", "Partner code (or ID if empty)"),
            ("partner_id", "Partner ID"),
            ("invoice_no", "Invoice Number (1.st segment)"),
            ("delivery_ym", "Delivery year and month (YYYYMM)"),
            ("invoice_ym", "Invoice year and month (YYYYMM)"),
            ("null", "Nothing"),
        ]

    _P1_P4_selection = lambda self: self._get_P1_P4_selection()

    invoice_reference_model = fields.Selection(
        selection_add=[
            ("00", "HR00 - P1-P2-P3  No controll"),
            ("01", "HR01 - P1-P2-P3  [k(P1,P2,P3)]"),
            ("02", "HR02 - P1-P2-P3  [k(P2), k(P3)]"),
            ("03", "HR03 - P1-P2-P3  [k(P1), k(P2), k(P3)]"),
            ("06", "HR06 - P1-P2-P3  [k(P2,P3)]"),
            # ('99', 'HR99 - No controll') - no usage in generating
        ],
        ondelete={
            "00": "set default",
            "01": "set default",
            "02": "set default",
            "03": "set default",
            "06": "set default",
            "99": "set default",
        },
    )
    invoice_reference_type = fields.Selection(
        selection_add=[("hr", "HR model types")],
        ondelete={"hr": "set default"},
    )
    # FIELDS

    property_l10n_hr_P1_pnbr = fields.Selection(
        selection=_P1_P4_selection,
        company_dependent=True,
        string="P1",
        help="1. ref number field.",
    )
    property_l10n_hr_P2_pnbr = fields.Selection(
        selection=_P1_P4_selection,
        company_dependent=True,
        string="P2",
        help="2. ref number field.",
    )
    property_l10n_hr_P3_pnbr = fields.Selection(
        selection=_P1_P4_selection,
        company_dependent=True,
        string="P3",
        help="3. ref number field.",
    )
    property_l10n_hr_P4_pnbr = fields.Selection(
        selection=_P1_P4_selection,
        company_dependent=True,
        string="P4",
        help="4. ref number field.",
    )

    @api.onchange("invoice_reference_type")
    def onchange_invoice_reference_type(self):
        if self.invoice_reference_type == "hr":
            if self.invoice_reference_model not in REF_CROATIA:
                self.invoice_reference_model = "01"

    @api.onchange("invoice_reference_model")
    def onchange_invoice_reference_model(self):
        if (
            self.invoice_reference_model in REF_CROATIA
            and self.invoice_reference_type != "hr"
        ):
            self.invoice_reference_type = "hr"
