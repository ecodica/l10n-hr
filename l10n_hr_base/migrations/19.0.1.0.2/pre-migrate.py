from odoo.tools import sql

# Columns of fields added to res.partner after databases were already in
# use. Created here, before the registry loads, when a database never got
# an upgrade of l10n_hr_base since: the ORM creates them as well during the
# schema sync of this upgrade, but a registry hook used to do it on every
# server start with an ALTER TABLE that locked res_partner (lock timeout,
# registry unusable under load). No DDL runs outside an upgrade any more.
COLUMNS = (
    ('l10n_hr_personal_oib', 'varchar'),
    ('l10n_hr_business_unit_code', 'varchar'),
)


def migrate(cr, version):
    for name, column_type in COLUMNS:
        if not sql.column_exists(cr, 'res_partner', name):
            sql.create_column(cr, 'res_partner', name, column_type)
