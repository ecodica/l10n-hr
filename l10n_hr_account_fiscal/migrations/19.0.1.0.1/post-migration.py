#  Copyright 2026 Ecodica d.o.o
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Schemas v1.6, v1.7 and v1.8 have been removed in favor of v1.9 / v1.10.
    # Remap any company still pointing at a removed schema to the closest
    # remaining one (v1.9) so fiscalization keeps working without manual fixup.
    openupgrade.logged_query(
        env.cr,
        """
            UPDATE res_company
               SET l10n_hr_fiscal_schema = 'PROD_v1.9'
             WHERE l10n_hr_fiscal_schema IN ('PROD_v1.6', 'PROD_v1.7', 'PROD_v1.8')
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
            UPDATE res_company
               SET l10n_hr_fiscal_schema = 'EDUC_v1.9'
             WHERE l10n_hr_fiscal_schema IN ('EDUC_v1.6', 'EDUC_v1.7', 'EDUC_v1.8')
        """,
    )
