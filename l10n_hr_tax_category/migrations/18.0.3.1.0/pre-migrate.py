from odoo.tools import sql

COLUMN = 'l10n_hr_pass_through_reason_text'


def migrate(cr, version):
    """Keep the Croatian text of the tax when its column stops being translated.

    The eRačun stated the Croatian term, while the conversion of the column keeps en_US only.
    """
    if sql.table_columns(cr, 'account_tax').get(COLUMN, {}).get('udt_name') != 'jsonb':
        return
    cr.execute(f"""
        UPDATE account_tax
           SET {COLUMN} = jsonb_build_object('en_US', {COLUMN}->>'hr_HR')
         WHERE {COLUMN}->>'hr_HR' IS NOT NULL
    """)
