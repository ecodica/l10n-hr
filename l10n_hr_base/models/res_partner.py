from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10_hr_company_registry_is_not_set = fields.Boolean(
        string='Company Registry Is Not Set', compute='_compute_l10_hr_company_registry_is_not_set', store=False)

    l10_hr_eu_country_vat_is_not_set = fields.Boolean(
        string='Tax ID Is Not Set', compute='_compute_l10_hr_eu_country_vat_is_not_set', store=False)

    @api.depends('company_registry', 'country_id', 'company_type')
    def _compute_l10_hr_company_registry_is_not_set(self):
        """Check if Croatian company has company registry (OIB) number set"""
        for partner in self:
           partner.l10_hr_company_registry_is_not_set = (
               partner.company_type == 'company' and
               partner.country_id.code == 'HR' and
               not partner.company_registry or
               False
            )

    @api.depends('vat', 'country_id', 'company_type')
    def _compute_l10_hr_eu_country_vat_is_not_set(self):
        """Check if Croatian company has company registry (OIB) number set"""
        eu_countries =  self.env.ref('base.europe').country_ids
        for partner in self:
           partner.l10_hr_eu_country_vat_is_not_set = (
               partner.company_type == 'company' and
               partner.country_id.code != 'HR' and
               partner.country_id in eu_countries and
               not partner.vat or
               False
            )

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
        if not self.company_registry or not self.company_registry.isdigit() or len(self.company_registry) != 11:
            return False
        return True

    @api.constrains('company_registry', 'country_id')
    def _validate_company_registry(self):
        """Croatian OIB validation"""
        for partner in self.filtered(lambda p: p.country_id.code == "HR" and p.company_registry):
            if not partner._l10n_hr_is_oib_valid():
                raise ValidationError(_("OIB %s is not valid!", partner.company_registry))

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
