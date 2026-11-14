import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# BT-118 codes whose exemption reason is a single VATEX code
SINGLE_VATEX_XMLIDS = {
    'AE': 'l10n_hr_vatex_tax_exempt.tax_exempt_VATEX_EU_AE',
    'K': 'l10n_hr_vatex_tax_exempt.tax_exempt_VATEX_EU_IC',
    'G': 'l10n_hr_vatex_tax_exempt.tax_exempt_VATEX_EU_G',
}


def migrate(cr, version):
    """Align the VATEX reason of existing taxes with l10n.hr.tax.category.exemption_reason_mode."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    account_tax = env['account.tax'].with_context(active_test=False)

    # BR-AE-10, BR-IC-10, BR-G-10: these sale taxes need a reason and only one fits
    for untdid_5305_code, xmlid in SINGLE_VATEX_XMLIDS.items():
        vatex_id = env.ref(xmlid, raise_if_not_found=False)
        tax_ids = vatex_id and account_tax.search([
            ('type_tax_use', '=', 'sale'),
            ('l10n_hr_tax_category_id.untdid_5305_code', '=', untdid_5305_code),
            ('l10n_hr_vatex_tax_exempt_id', '=', False),
        ])
        if tax_ids:
            tax_ids.l10n_hr_vatex_tax_exempt_id = vatex_id
            _logger.info("VATEX %s set on taxes %s", vatex_id.code, tax_ids.ids)

    tax_ids = account_tax.search([('l10n_hr_vatex_tax_exempt_id', '!=', False)])
    # a pass-through charge states a generated reason, its VATEX was never written
    pass_through_tax_ids = tax_ids.filtered(
        lambda tax: tax.l10n_hr_exemption_reason_mode == 'pass_through')
    if pass_through_tax_ids:
        pass_through_tax_ids.l10n_hr_vatex_tax_exempt_id = False
        _logger.info("VATEX removed from pass-through taxes %s", pass_through_tax_ids.ids)
    # kept on purpose: a reason on a standard or zero rated tax hints at a wrong tax category,
    # which only the user can settle
    for tax in tax_ids.filtered(lambda tax: tax.l10n_hr_exemption_reason_mode == 'none'):
        _logger.warning(
            "Tax %s (id %s, company %s) has VATEX %s but its tax category %s states no exemption "
            "reason: check the tax category and remove the reason.",
            tax.name, tax.id, tax.company_id.name, tax.l10n_hr_vatex_tax_exempt_id.code,
            tax.l10n_hr_tax_category_id.code)
