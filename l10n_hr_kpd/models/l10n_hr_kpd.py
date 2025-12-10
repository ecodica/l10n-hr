from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv.expression import NEGATIVE_TERM_OPERATORS
import re

CODE_PATTERNS = {
    '1': r"[A-Z]",
    '2': r"^\d{2}$",
    '3': r"^\d{2}\.\d$",
    '4': r"^\d{2}\.\d{2}$",
    '5': r"^\d{2}\.\d{2}\.\d$",
    '6': r"^\d{2}\.\d{2}\.\d{2}$"
}


class L10nHrKpd(models.Model):
    _name = 'l10n.hr.kpd'
    _description = 'Defines KPD classification.'
    _order = 'code ASC'
    _inherit = ['mail.thread']

    code = fields.Char(string="Code", required=True, copy=False)
    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date")
    level = fields.Char(string="Level", readonly=True, required=True)
    name = fields.Char(string="Name", required=True, translate=True)
    type = fields.Selection(
        string="Type",
        selection=[
            ('1', 'Section'),
            ('2', 'Division'),
            ('3', 'Group'),
            ('4', 'Class'),
            ('5', 'Category'),
            ('6', 'Subcategory')
        ], compute="_compute_type", store=True)
    parent_id = fields.Many2one(comodel_name='l10n.hr.kpd', string="Parent")

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'The KPD code has to be unique!')
    ]

    @api.depends('level')
    def _compute_type(self):
        for kpd in self:
            kpd.type = kpd.level

    @staticmethod
    def _is_code_valid(code, level):
        """
            Check if KPD code is in proper format depending on record type.
        """
        valid_pattern = CODE_PATTERNS.get(level)
        return bool(re.fullmatch(valid_pattern, code))

    @api.constrains('code')
    def _check_subcategory_code(self):
        for kpd in self:
            if not self._is_code_valid(code=kpd.code, level=kpd.level):
                raise UserError(
                    _("The KPD code is not properly formatted!")
                )

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for kpd in self:
            kpd.display_name = '%s - %s' % (kpd.code, kpd.name)

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = ["|", ("code", operator, name), ("name", operator, name)]
            if operator in NEGATIVE_TERM_OPERATORS:
                domain = ["&", "!"] + domain[1:]
        kpds = self.search(domain + args, limit=limit)
        return [(kpd.id, kpd.display_name) for kpd in kpds.sudo()]
