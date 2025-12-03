# Copyright 2025 Ecodica - Danijel Bosnar
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade
from psycopg2 import sql
from odoo.tools.sql import column_exists


def convert_partner_l10n_hr_journals_to_company_dependent(
        env,
        origin_field_name,
        destination_field_name,
):
    """For each row in a given table, the value of a given field is
    set in another 'company dependant' field of the same table.
    Useful in cases when from one version to another one, some field in a
    model becomes a 'company dependent' field.

    This method must be executed in post-migration scripts after
    the field is created, or in pre-migration if you have previously
    executed add_fields openupgradelib method.

    :param origin_field_name: Name of the field from which the values
      will be obtained.
    :param destination_field_name: Name of the 'company dependent'
      field where the values obtained from origin_field_name will be set.

    """
    openupgrade.logger.debug(
        "Converting {} in res_partner to company_dependent field {}.".format(
            origin_field_name, destination_field_name
        )
    )
    # if origin_field_name == destination_field_name:
    #     openupgrade.do_raise("A field can't be converted without changing its name.")
    cr = env.cr
    openupgrade.logged_query(
        cr,
        sql.SQL(
            """
        WITH company_base AS (
            SELECT rc.id as rc_id
            , aj.id as aj_id
                --company_id AS cid
            FROM res_company rc
            JOIN account_journal aj ON aj.company_id = rc.id
        )

        -- 
        UPDATE res_partner p
        SET {value_field_name} = jsonb_build_object(
                company_base.rc_id::text,
                p.{origin_field_name}
            )
        FROM company_base
        WHERE p.{origin_field_name} = company_base.aj_id
          AND p.{origin_field_name} IS NOT NULL;
        """
        ).format(
            value_field_name=sql.Identifier(destination_field_name),
            origin_field_name=sql.Identifier(origin_field_name),
        ),
    )
    # alter table, not sure if this is really necessary or not
    openupgrade.logged_query(
        cr,
        sql.SQL(
            """
        ALTER TABLE res_partner
            ALTER COLUMN {value_field_name} TYPE jsonb
            USING {value_field_name}::jsonb;
        """
        ).format(
            value_field_name=sql.Identifier(destination_field_name),
        ),
    )


@openupgrade.migrate()
def migrate(env, version):
    """Set the *_journal_id value in the res_partner to multi company."""
    if column_exists(env.cr, "res_partner", "l10n_hr_sale_journal_id"):
        convert_partner_l10n_hr_journals_to_company_dependent(
            env, "old_l10n_hr_sale_journal_id", "l10n_hr_sale_journal_id"
        )
    if column_exists(env.cr, "res_partner", "l10n_hr_purchase_journal_id"):
        convert_partner_l10n_hr_journals_to_company_dependent(
            env, "old_l10n_hr_purchase_journal_id", "l10n_hr_purchase_journal_id"
        )
