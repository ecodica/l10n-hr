#  Copyright 2025 Ecodica d.o.o
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    field_spec = [
        (
            "account.move",
            "account_move",
            "l10n_hr_invoice_time",
            "l10n_hr_fiscal_time",
        ),
        # Odoo 16 named this field differently; cover the 16 -> 18 jump too.
        # rename_fields is idempotent, so whichever old column actually exists
        # in the DB wins and the other rename is skipped.
        (
            "account.move",
            "account_move",
            "l10n_hr_vrijeme_izdavanja",
            "l10n_hr_fiscal_time",
        ),
    ]
    openupgrade.rename_fields(env, field_spec)
