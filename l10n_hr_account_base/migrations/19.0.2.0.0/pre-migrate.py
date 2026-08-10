#  Copyright 2026 Ecodica d.o.o
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    field_spec = [
        (
            "res.company",
            "res_company",
            "l10n_hr_show_required_fisk_fields_on_header",
            "l10n_hr_show_required_fiscal_fields_on_header",
        ),
        (
            "account.move",
            "account_move",
            "l10n_hr_show_required_fisk_fields_on_header",
            "l10n_hr_show_required_fiscal_fields_on_header",
        ),
    ]
    openupgrade.rename_fields(env, field_spec)
