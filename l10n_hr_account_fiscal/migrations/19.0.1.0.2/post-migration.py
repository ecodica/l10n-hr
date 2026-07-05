#  Copyright 2026 Ecodica d.o.o
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Set default schema to PROD_v1.10 for companies that have no schema set
    openupgrade.logged_query(
        env.cr,
        """
            UPDATE res_company
               SET l10n_hr_fiscal_schema = 'PROD_v1.10'
             WHERE l10n_hr_fiscal_schema IS NULL
                OR l10n_hr_fiscal_schema = ''
        """,
    )
