#  Copyright 2025 Ecodica d.o.o
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    field_spec = [
        (
            "account.move",
            "account_move",
            "l10n_hr_fiskal_user_id",
            "l10n_hr_fiscal_user_id",
        ),
    ]
    openupgrade.rename_fields(env, field_spec)
