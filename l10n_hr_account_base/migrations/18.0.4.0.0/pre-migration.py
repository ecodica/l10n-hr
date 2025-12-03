# Copyright 2025 Ecodica - Danijel Bosnar
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo.tools.sql import column_exists

column_renames_sale = {
    "res_partner": [("l10n_hr_sale_journal_id", "old_l10n_hr_sale_journal_id")],
}
column_renames_purchase = {
    "res_partner": [("l10n_hr_purchase_journal_id", "old_l10n_hr_purchase_journal_id")],
}

@openupgrade.migrate()
def migrate(env, version):
    """Rename columns to keep old values"""
    if column_exists(env.cr, "res_partner", "l10n_hr_sale_journal_id"):
        openupgrade.rename_columns(env.cr, column_renames_sale)
    if column_exists(env.cr, "res_partner", "l10n_hr_purchase_journal_id"):
        openupgrade.rename_columns(env.cr, column_renames_purchase)
