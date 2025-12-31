# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """
    Pre-migration script to remove the ghost field 'l10n_hr_fiskal_on_confirm'
    from res.company before the Odoo registry tries to unlink it.
    """
    _logger.info("Starting pre-migration: Cleaning up l10n_hr_fiskal_on_confirm")

    cr.execute("""
        SELECT id FROM ir_model_fields
        WHERE name = 'l10n_hr_fiskal_on_confirm'
        AND model = 'res.company'
    """)
    field_exists = cr.fetchone()

    if field_exists:
        cr.execute("""
            DELETE FROM ir_model_data
            WHERE (name = 'field_res_company__l10n_hr_fiskal_on_confirm'
                OR name LIKE '%l10n_hr_fiskal_on_confirm%')
            AND model = 'ir.model.fields'
        """)

        cr.execute("""
            DELETE FROM ir_model_fields
            WHERE name = 'l10n_hr_fiskal_on_confirm'
            AND model = 'res.company'
        """)

        _logger.info("Successfully deleted ghost field and metadata.")
    else:
        _logger.info("Field l10n_hr_fiskal_on_confirm not found, skipping cleanup.")
