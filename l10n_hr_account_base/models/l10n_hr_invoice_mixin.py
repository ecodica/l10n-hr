import logging
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
# from odoo.addons.l10n_hr_base.models.res_company import FISKAL_DATETIME_FORMAT, RACUN_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class l10nHrInvoiceMixin(models.AbstractModel):
    """Contains minimum set of fields for ALL Croatian invoices
      - used for invoices to foreign customers and domestical out of VAT sistem
    """
    _name = "l10n.hr.invoice.mixin"
    _description = "Croatia Invoice mixin"

    # invoice number [SEQ]
    l10n_hr_fiscal_device_id = fields.Many2one(
        comodel_name="l10n_hr.fiscal.device",
        string="Fiscal Device",
        help="Device that registers invoice.")

    l10n_hr_fiscal_user_id = fields.Many2one(
        comodel_name="res.partner",
        string="Fiscal User",
        domain=lambda self: self._get_l10n_hr_fiskal_user_id_domain(),
        ondelete='restrict',
        copy=False,
        help="User who sent the fiscalization message to FINA."
        " Can be different from responsible person on invoice.",
    )

    def l10n_hr_gen_fiscal_number(self):
        self.ensure_one()  # one at a time only!
        premise = self.l10n_hr_fiscal_device_id.l10n_hr_business_premise_id
        device = self.l10n_hr_fiscal_device_id
        if not premise or not device:
            return False
        sequence = (premise.l10n_hr_invoice_sequence_by == "P" and premise.l10n_hr_sequence_id
                    or device.l10n_hr_sequence_id)
        number = sequence._next(sequence_date=self.date)
        if number.endswith("__"):
            number = number.replace("__", str(device.l10n_hr_fiscal_device_code))
        return number




class l10nHrFiskInvoiceMixin(models.AbstractModel):
    """ Contains common set of fields/methods for Croatian F1.0 (B2C), and F2.0 invoice (B2B,B2C)

    """
    _name = "l10n.hr.fisk.invoice.mixin"
    _inherit = "l10n.hr.invoice.mixin"
    _description = "Croatia Fiscal Invoice mixin"


class l10nHrFisk10InvoiceMixin(models.AbstractModel):
    """
      Set of fields/methods for Croatian F1.0 B2C invoice.
      Fiscalization in final consumption docs : https://porezna.gov.hr/fiskalizacija/gotovinski-racuni

    """
    _name = "l10n.hr.fisk.10.invoice.mixin"
    _inherit = "l10n.hr.fisk.invoice.mixin"
    _description = "Croatia Fiscal B2C Invoice mixin"

    l10n_hr_zki = fields.Char(string="ZKI", readonly=True, copy=False)
    l10n_hr_jir = fields.Char(string="JIR", readonly=True, copy=False)

    # Issue time format dd.mm.ggggThh:mm:ss

class l10nHrFisk20InvoiceMixin(models.AbstractModel):
    """Set of fields/methods for Croatian F2.0 B2B and B2G invoice

    """
    _name = "l10n.hr.fisk.20.invoice.mixin"
    _inherit = "l10n.hr.fisk.invoice.mixin"
    _description = "Croatia Fiscal B2B Invoice mixin"
