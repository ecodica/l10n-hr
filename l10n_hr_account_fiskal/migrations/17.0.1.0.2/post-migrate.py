import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """Based on existing l10n_hr_nacin_placanja field, set newly added l10n_hr_default_account_payment_type_id column value on account journal"""

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
                    pt.code = aj.l10n_hr_default_nacin_placanja
                AND 
                    aj.l10n_hr_default_nacin_placanja IS NOT NULL
                RETURNING
                    aj.id
            )
        SELECT 
            COUNT(*) FROM updated;
    """)
    
    updated_count = cr.fetchone()[0]
    _logger.info("--- MIGRATION SCRIPT COMPLETED: %s account.journal records updated field l10n_hr_default_account_payment_type_id---", updated_count)

    cr.commit()
