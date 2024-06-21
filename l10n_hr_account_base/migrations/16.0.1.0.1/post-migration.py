# Copyright 2024 Ecodica - Goran Bogic
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.property'].migrate_classical_field_to_property('res_partner', 'purchase_journal_id', 'purchase_journal_id',
                                                           drop_old_column=True)
    env['ir.property'].migrate_classical_field_to_property('res_partner', 'sale_journal_id', 'sale_journal_id',
                                                           drop_old_column=True)
