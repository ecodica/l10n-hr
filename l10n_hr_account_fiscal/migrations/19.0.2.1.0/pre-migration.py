#  Copyright 2025 Ecodica d.o.o
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # l10n_hr.working.hours.schedule changed from TransientModel to Model.
    # Drop the old transient tables so Odoo can recreate them as persistent tables
    # with the correct foreign keys and indexes.
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM l10n_hr_working_hours_schedule_line;
        DELETE FROM l10n_hr_working_hours_schedule;
        DROP TABLE IF EXISTS l10n_hr_working_hours_schedule_line CASCADE;
        DROP TABLE IF EXISTS l10n_hr_working_hours_schedule CASCADE;
        """,
    )
