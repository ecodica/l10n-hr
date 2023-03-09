from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

TYPE_SELECTION = [('view', 'View'), ('normal', 'Normal')]


class L10nHrJOPPDCodeRegister(models.AbstractModel):
    _name = "l10n.hr.joppd.code.register"
    _description = "JOPPD Code Register"
    _auto = False
    _parent_store = True
    _parent_order = "code"
    _parent_path_store = False

    parent_path = fields.Char(string='Parent Path', index=True)
    # TODO: review necessity
    # company_id = fields.Many2one('res.company', 'Company', required=1, index=1,
    #                              default=lambda self: self.env['res.company']._company_default_get(self._name))
    name = fields.Char('Description', size=1024, required=1, index=1)
    code = fields.Char('Code', size=10, index=1)
    type = fields.Selection(TYPE_SELECTION, 'Type', required=1, default='normal')
    parent_id = fields.Many2one(comodel_name=_name,
                                string='Parent', index=1, ondelete='restrict', domain=[('type', '=', 'view')])
    child_ids = fields.One2many(comodel_name=_name, inverse_name="parent_id", string='Children', readonly=1)
    active = fields.Boolean('Active', index=1, default=True)

    @api.model
    def _setup_fields(self):
        super()._setup_fields()
        if self._name != 'l10n.hr.joppd.register.code':
            for field in self._fields.values():
                if field.type in ('many2one', 'one2many') and field.comodel_name == 'l10n.hr.joppd.code.register':
                    field.comodel_name = self._name

    def name_get(self):
        return [
            (record.id, '[%s] %s' % (record.code, record.name[:128]))
            for record in self
        ]

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(
                _('Error! You cannot create recursive records.'))

    @api.constrains('code')
    def _check_duplicate_code(self):
        duplicate_code_records = self.search([('code', '=', self.code),
                                              ('id', '!=', self.id),
                                              ('type', '!=', 'view')])

        if duplicate_code_records:
            raise ValidationError(_('Error! You cannot create records with duplicate code.'))
