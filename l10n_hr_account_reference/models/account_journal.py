from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Most used payment reference models for out invoices. Add more if needed...
L10N_HR_MODELS = {
    'hr00': ('HR00', 'HR00 - P1-P2-P3  No Control'),
    'hr01': ('HR01', 'HR01 - P1-P2-P3  [k(P1,P2,P3)]'),
    'hr02': ('HR02', 'HR02 - P1-P2-P3  [k(P2), k(P3)]'),
    'hr03': ('HR03', 'HR03 - P1-P2-P3  [k(P1), k(P2), k(P3)]'),
    'hr04': ('HR04', 'HR04 - P1-P2-P3  [k(P1), P2, k(P3)]'),
    'hr06': ('HR06', 'HR06 - P1-P2-P3  [k(P2,P3)]'),
    'hr99': ('HR99', 'HR99 - No Control'),
    'hr': ('HR', 'No Control'),
}


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.constrains("invoice_reference_model", "invoice_reference_type")
    def _l10n_hr_constrain_pnb_model(self):
        for record in self:
            if record.country_code != 'HR':
                return
            if (
                record.invoice_reference_type == "hr"
                and record.invoice_reference_model not in list(zip(*list(L10N_HR_MODELS.values())))[0]
            ) or (
                record.invoice_reference_type != "hr"
                and record.invoice_reference_model in list(zip(*list(L10N_HR_MODELS.values())))[0]
            ):
                raise ValidationError(
                    _(
                        "Both Communication standard and Communication type,"
                        " should be Croatia or not Croatia, mix is not possible!"
                    )
                )

    def _get_P1_P4_selection(self):
        return [
            ("move_id", "Invoice Database ID"),  # solid unique reference part!
            ("partner_code", "Partner Code (or ID if empty)"),
            ("partner_id", "Partner ID"),
            ("invoice_no", "Invoice Number (1.st segment)"),
            ("delivery_ym", "Delivery Year And Month (YYYYMM)"),
            ("invoice_ym", "Invoice Year And Month (YYYYMM)"),
            ("null", "Nothing"),
        ]

    _P1_P4_selection = lambda self: self._get_P1_P4_selection()

    invoice_reference_model = fields.Selection(
        selection_add=list(L10N_HR_MODELS.values()),
        ondelete={item[1][0]: "set default" for item in L10N_HR_MODELS.items()})
    invoice_reference_type = fields.Selection(
        selection_add=[("hr", "HR Model Types")],
        ondelete={"hr": "set default"})
    
    # FIELDS
    property_l10n_hr_P1_ar = fields.Selection(
        selection=_P1_P4_selection,
        company_dependent=True,
        string="P1",
        help="1. ref number field.",
    )
    property_l10n_hr_P2_ar = fields.Selection(
        selection=_P1_P4_selection,
        company_dependent=True,
        string="P2",
        help="2. ref number field.",
    )
    property_l10n_hr_P3_ar = fields.Selection(
        selection=_P1_P4_selection,
        company_dependent=True,
        string="P3",
        help="3. ref number field.",
    )
    property_l10n_hr_P4_ar = fields.Selection(
        selection=_P1_P4_selection,
        company_dependent=True,
        string="P4",
        help="4. ref number field.",
    )

    @api.onchange("invoice_reference_type")
    def onchange_invoice_reference_type(self):
        if self.invoice_reference_type == "hr":
            if self.invoice_reference_model not in list(zip(*list(L10N_HR_MODELS.values())))[0]:
                self.invoice_reference_model = "HR01"

    @api.onchange("invoice_reference_model")
    def onchange_invoice_reference_model(self):
        if (
            self.invoice_reference_model in list(zip(*list(L10N_HR_MODELS.values())))[0]
            and self.invoice_reference_type != "hr"
        ):
            self.invoice_reference_type = "hr"
