from odoo import fields, models, api


class L10nHrJOPPDb(models.Model):
    _inherit = 'l10n.hr.joppd.b'

    joppd_move_entry_id = fields.Many2one('l10n.hr.joppd.account.move.entry', 'JOPPD Move Entry')
