from odoo.tools import SQL, sql

PARTNER_JOURNAL_FIELDS = ('l10n_hr_sale_journal_id', 'l10n_hr_purchase_journal_id')


def migrate(cr, version):
    """File the journal each partner had under the company that owns that journal."""
    for name in PARTNER_JOURNAL_FIELDS:
        old_name = f'old_{name}'
        if not sql.column_exists(cr, 'res_partner', old_name):
            continue
        cr.execute(SQL(
            """
            UPDATE res_partner p
               SET %(new)s = jsonb_build_object(j.company_id::text, j.id)
              FROM account_journal j
             WHERE j.id = p.%(old)s
            """,
            new=SQL.identifier(name),
            old=SQL.identifier(old_name),
        ))
        cr.execute(SQL("ALTER TABLE res_partner DROP COLUMN %s", SQL.identifier(old_name)))
