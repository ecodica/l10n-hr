import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Store the full pass-through exemption reason on existing taxes.

    The eRačun used to build "#<category code>#<text>" from the text of the tax, the default of
    its category or the tax name, all read in Croatian. It now writes the text of the tax as it
    stands, so that text has to hold the full reason.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    lang = env['res.lang']._get_code('hr_HR') or None
    tax_ids = env['account.tax'].with_context(active_test=False, lang=lang).search([
        ('l10n_hr_tax_category_id', '!=', False),
    ]).filtered(lambda tax: tax.l10n_hr_exemption_reason_mode == 'pass_through')
    for tax in tax_ids:
        category_id = tax.l10n_hr_tax_category_id
        prefix = '#{}#'.format(category_id.code)
        text = tax.l10n_hr_pass_through_reason_text or ''
        if not text.startswith(prefix):
            tax.l10n_hr_pass_through_reason_text = prefix + (
                text or category_id.pass_through_reason_text or tax.name)
            _logger.info("Pass-through exemption reason of tax %s (id %s) set to %s",
                         tax.name, tax.id, tax.l10n_hr_pass_through_reason_text)
