
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from dateutil.relativedelta import relativedelta
PARTNER_VAT_TYPES = [
            ("vat", "1"),
            ("vat_id", "2"),
            ("other", "3"),
        ]


class OpzStatLine(models.Model):
    _name = "opz.stat.line"
    _description = "OPZ STAT report lines"
    _order = "invoice_date, due_date, amount"

    opz_id = fields.Many2one("opz.stat", "OPZ STAT", required=1, ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Partner", required=1)
    account_id = fields.Many2one("account.account", string="Account", required=1)
    partner_name = fields.Char("Partner Name", required=1)
    partner_vat_type = fields.Selection(PARTNER_VAT_TYPES, string="VAT Type", required=True, index=True,
                                        default=PARTNER_VAT_TYPES[0][0])
    partner_vat_number = fields.Char("VAT Number", required=1)
    invoice_id = fields.Many2one(
        "account.move",
        "Invoice",
        copy=True,
        domain="[('partner_id', '=', partner_id), ('line_ids.account_id.account_type', '=', 'asset_receivable')]",
    )
    invoice_number = fields.Char("Invoice Number", required=1)
    invoice_date = fields.Date("Invoice Date", required=1)
    due_date = fields.Date("Due Date", required=1)
    amount = fields.Float("Amount", required=1, default=0.0, digits='Account')
    amount_tax = fields.Float("Amount Tax", required=1, default=0.0, digits='Account')
    amount_total = fields.Float("Amount with Tax", required=1, default=0.0, digits='Account')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=1)
    paid = fields.Float("Paid Amount", required=1, default=0.0, digits='Account')
    unpaid = fields.Float("Unpaid Amount", required=1, default=0.0, digits='Account')
    overdue_days = fields.Integer("Overdue Days", required=1, default=0)

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        if self.partner_id:
            self.partner_name = self.partner_id.name
            if self.partner_vat_type == "vat":
                self.partner_vat_number = self.partner_id.vat and self.partner_id.vat[2:]
            else:
                self.partner_vat_number = self.partner_id.vat
        else:
            self.partner_name = False
            self.partner_vat_number = False

    @api.onchange("invoice_id")
    def onchange_invoice_id(self):
        if self.invoice_id:
            overdue = (
                (
                    self.opz_id.date_to + relativedelta(months=1)
                )
                + relativedelta(day=1, months=+1, days=-1)
            ) - self.invoice_id.invoice_date_due
            self.invoice_number = self.invoice_id.name
            self.invoice_date = self.invoice_id.invoice_date
            self.due_date = self.invoice_id.invoice_date_due
            self.amount = self.invoice_id.amount_untaxed
            self.amount_tax = self.invoice_id.amount_tax
            self.amount_total = self.invoice_id.amount_total
            self.overdue_days = overdue.days
            # TODO residual must be computed
            self.paid = self.invoice_id.amount_total - self.invoice_id.amount_residual
            self.unpaid = self.invoice_id.amount_residual

    @api.onchange("due_date")
    def onchange_due_date(self):
        if self.due_date:
            overdue = (
                self.opz_id.date_to + relativedelta(months=1) + relativedelta(day=1, months=+1, days=-1)
            ) - self.due_date
            self.overdue_days = overdue.days
        else:
            self.overdue_days = False

    @api.onchange('amount', 'amount_tax')
    def onchange_amount(self):
        self.amount_total = self.amount + self.amount_tax
        self.unpaid = self.amount_total - self.paid