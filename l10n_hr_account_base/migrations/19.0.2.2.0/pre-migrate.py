from odoo.tools import sql

PARTNER_JOURNAL_FIELDS = ('l10n_hr_sale_journal_id', 'l10n_hr_purchase_journal_id')


def migrate(cr, version):
    """Set the one journal per partner aside: the fields become company dependent (jsonb)."""
    columns = sql.table_columns(cr, 'res_partner')
    for name in PARTNER_JOURNAL_FIELDS:
        # a database that comes from 18 already holds the jsonb column
        if columns.get(name, {}).get('udt_name') == 'int4':
            sql.rename_column(cr, 'res_partner', name, f'old_{name}')
