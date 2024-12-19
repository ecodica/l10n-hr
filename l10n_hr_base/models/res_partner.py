from odoo import api, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.depends("vat", "country_id")
    def _compute_company_registry(self):
        # OVERRIDE
        # If a croatian company has a VAT number then it"s company registry (OIB)
        # is it"s VAT Number (without country code).
        # borrowed from l10n_be
        res = super()._compute_company_registry()
        for partner in self.filtered(lambda p: p.country_id.code == "HR" and p.vat):
            vat_country, vat_number = self._split_vat(partner.vat)
            if vat_country == "hr" and self.simple_vat_check(vat_country, vat_number):
                partner.company_registry = vat_number
        return res

    def _l10n_hr_is_oib_valid(self):
        res = {}
        if not self.company_registry or not self.company_registry.isdigit() or len(self.company_registry) != 11:
            return False
        return True

    @api.constrains('company_registry', 'country_id')
    def _validate_company_registry(self):
        """Croatian OIB validation"""
        for partner in self.filtered(lambda p: p.country_id.code == "HR" and p.company_registry):
            if not self._l10n_hr_is_oib_valid():
                raise ValidationError(_("OIB %s is not valid!", self.company_registry))

    @api.model
    def _commercial_fields(self):
        """Extend to skip writing OIB and VAT on contacts when company is updated."""
        # TODO: add this as optional
        commercial_fields = super()._commercial_fields()
        if self.type == 'contact' and 'company_registry' in commercial_fields:
            commercial_fields.remove("company_registry")
        if self.type == 'contact' and 'vat' in commercial_fields:
            commercial_fields.remove("vat")
        return commercial_fields
