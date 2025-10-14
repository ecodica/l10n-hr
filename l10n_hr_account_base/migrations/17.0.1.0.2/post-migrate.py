import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """Based on existing l10n_hr_nacin_placanja field, set newly added l10n_hr_account_payment_type_id column value on account moves"""

    cr.execute("""
        WITH
            updated AS (
                UPDATE
                    account_move am
                SET
                    l10n_hr_account_payment_type_id = pt.id
                FROM
                    l10n_hr_account_payment_type pt
                WHERE
                    pt.code = am.l10n_hr_nacin_placanja
                AND
                    am.l10n_hr_nacin_placanja IS NOT NULL
                RETURNING
                    am.id
            )
        SELECT
            COUNT(*) FROM updated;
    """)

    updated_count = cr.fetchone()[0]
    _logger.info("--- MIGRATION SCRIPT COMPLETED: %s account.move records updated for field l10n_hr_account_payment_type_id ---", updated_count)
