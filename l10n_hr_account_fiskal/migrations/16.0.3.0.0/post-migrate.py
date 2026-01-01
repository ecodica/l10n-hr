import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """Update fiscal schema on fiscal certificate to the latest version."""

    cr.execute("""
        WITH
            updated AS (
                UPDATE
                    l10n_hr_fiskal_certificate fc
                SET
                    fiskal_schema = split_part(fiskal_schema, '_', 1) || '_v1.10'
                RETURNING
                    fc.id
            )
        SELECT
            COUNT(*) FROM updated;
    """)

    updated_count = cr.fetchone()[0]
    _logger.info("--- MIGRATION SCRIPT COMPLETED: %s l10n.hr.fiskal.certificate records updated field fiskal_schema---", updated_count)

    cr.commit()
