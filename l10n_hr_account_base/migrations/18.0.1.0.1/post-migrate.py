import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """Migrate l10n_hr_payment_method to the l10n_hr_account_payment_type_id field."""

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
                    pt.code = am.l10n_hr_payment_method
                AND
                    am.l10n_hr_payment_method IS NOT NULL
                RETURNING
                    am.id
            )
        SELECT
            COUNT(*) FROM updated;
    """)

    updated_count = cr.fetchone()[0]
    _logger.info("--- MIGRATION SCRIPT COMPLETED: %s account.move records updated for field l10n_hr_account_payment_type_id ---", updated_count)

    cr.execute("""
        WITH
            updated AS (
                UPDATE
                    account_journal aj
                SET
                    l10n_hr_default_account_payment_type_id = pt.id
                FROM
                    l10n_hr_account_payment_type pt
                WHERE
                    pt.code = aj.l10n_hr_default_fiscal_payment_method
                AND
                    aj.l10n_hr_default_fiscal_payment_method IS NOT NULL
                RETURNING
                    aj.id
            )
        SELECT
            COUNT(*) FROM updated;
    """)

    updated_count = cr.fetchone()[0]
    _logger.info("--- MIGRATION SCRIPT COMPLETED: %s account.journal records updated for field l10n_hr_default_fiscal_payment_method ---", updated_count)
