from odoo import api, fields, models
from odoo.exceptions import UserError

PAYMENT_METHODS = [
    ("G", "Cash"),
    ("K", "Credit or debit cards"),
    ("T", "Bank transfer"),
    ("O", "Other payment means"),
]


class L10nHrChangeFiscalData(models.TransientModel):
    """Change the customer of a fiscalized document with FINA.

    Works on any document carrying ``l10n_hr.fiscal.v1.mixin``. The payment method is
    reported as the document has it: the back office changes only the customer. The
    document changes only once FINA confirms; until midnight of the issue day a refused
    change can be tried again.
    """
    _name = "l10n_hr.change.fiscal.data"
    _description = 'Change Fiscal Data Wizard'

    res_model = fields.Char(string="Document Model", required=True, readonly=True)
    res_id = fields.Many2oneReference(string="Document ID", model_field="res_model", required=True, readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    current_partner_id = fields.Many2one("res.partner", string="Current Customer", readonly=True)
    current_payment_method = fields.Selection(selection=PAYMENT_METHODS, readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', check_company=True)
    recipient_oib = fields.Char(
        string="Recipient OIB",
        compute="_compute_change_preview",
        help="OIB reported to the tax authority: only a company's, so the receipt "
             "becomes R1. Empty for a private person.",
    )
    warning = fields.Text(compute="_compute_change_preview")

    @api.model
    def default_get(self, fields):
        """Start from the document the wizard was opened on."""
        res = super().default_get(fields)
        active_model, active_id = self.env.context.get('active_model'), self.env.context.get('active_id')
        if not active_model or not active_id:
            return res
        current_move = self.env[active_model].browse(active_id)
        res.update(dict(res_model=active_model,
                        res_id=active_id,
                        company_id=current_move.company_id.id,
                        current_partner_id=current_move.partner_id.id,
                        current_payment_method=current_move.l10n_hr_payment_method,
                        partner_id=current_move.partner_id.id))
        return res

    def _get_document(self):
        """Return the fiscalized document, checking the user may read it."""
        self.ensure_one()
        # any model carrying l10n_hr.fiscal.v1.mixin
        if self.res_model not in self.env or not hasattr(self.env[self.res_model], "_l10n_hr_change_fiscal_data"):
            raise UserError(self.env._("%(model)s is not a fiscal document.", model=self.res_model))
        document = self.env[self.res_model].browse(self.res_id).exists()
        document.check_access("read")
        return document

    @api.depends("res_model", "res_id", "partner_id")
    def _compute_change_preview(self):
        """Show the OIB that will be reported and what the change leaves as it is."""
        for wizard in self:
            document = wizard._get_document() if wizard.res_model and wizard.res_id else None
            if not document:
                wizard.recipient_oib = False
                wizard.warning = False
                continue
            wizard.recipient_oib = document._l10n_hr_recipient_oib(wizard.partner_id) or False
            warnings = document._l10n_hr_fiscal_change_warnings(wizard.partner_id, document.l10n_hr_payment_method)
            wizard.warning = "\n".join(warnings) or False

    def change(self):
        """Send the change to FINA; the document changes only when FINA confirms it."""
        self.ensure_one()
        document = self._get_document()
        failure = document._l10n_hr_change_fiscal_data(self.partner_id, document.l10n_hr_payment_method)
        if failure:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("The tax authority did not confirm the change"),
                    "message": self.env._("%(document)s was not changed, you can try again until midnight. "
                                          "Reason: %(reason)s",
                                          document=document.display_name, reason=failure),
                    "type": "danger",
                    "sticky": True,
                },
            }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Fiscal data changed"),
                "message": self.env._("The tax authority confirmed the change of %(document)s.",
                                      document=document.display_name),
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }
