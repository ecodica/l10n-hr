#  Copyright 2026 Ecodica d.o.o
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move
        SET l10n_hr_fiscal_time_calc = TO_TIMESTAMP(l10n_hr_fiscal_time, 'DD.MM.YYYY"T"HH24:MI:SS') AT TIME ZONE 'UTC'
        WHERE 
            l10n_hr_fiscal_time IS NOT NULL
        """,
    )
