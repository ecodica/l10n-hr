from odoo import fields, models, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import format_date

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('wait', 'Waiting For Payment'),
    ('ready', 'Ready For Processing'),
    ('done', 'Done'),
    ('cancel', 'Cancelled')
]
READONLY_STATES = {'done': [('readonly', True)], 'cancel': [('readonly', True)]}


class JOPPDAccountMoveEntry(models.Model):
    _name = 'l10n.hr.joppd.account.move.entry'
    _description = "JOPPD General Ledger Entry"

    name = fields.Char('Name', size=64, required=1)
    amount = fields.Float('Amount', digits=dp.get_precision('Account'))
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=1, readonly=1,
        ondelete='cascade', index=1,
        default=lambda self: self.env['res.company']._company_default_get(self._name))
    state = fields.Selection(
        string='State',
        selection=STATE_SELECTION,
        readonly=1, required=1,
        default=STATE_SELECTION[0][0],
        index=1)
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Account Move',
        required=1, readonly=1,
        ondelete='cascade', index=1)
    move_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Journal Item',
        required=1, readonly=1,
        ondelete='cascade', index=1)
    date = fields.Date(string='Date', required=1, index=1)
    date_payment = fields.Date(string='Payment Date', index=1)
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=1, readonly=0, states=READONLY_STATES,
        ondelete='restrict')
    nontaxable_receipt_id = fields.Many2one(
        comodel_name='l10n.hr.joppd.code.register.nontaxable.receipt',
        string='Non-Taxable Receipt',
        required=1, readonly=0, states=READONLY_STATES,
        ondelete='restrict', domain=[('type', '=', 'normal')])
    payment_method_id = fields.Many2one(
        comodel_name='l10n.hr.joppd.code.register.payment.method',
        string='Payment Method',
        required=1, readonly=0, states=READONLY_STATES,
        ondelete='restrict', domain=[('type', '=', 'normal')])

    def unlink(self):
        for entry in self:
            if entry.state == 'done':
                raise UserError(_('Entry %s/%s is in state "Done" and can not be deleted!')
                                % (entry.name, format_date(self.env, entry.date)))
        self.mapped('move_id').write({'joppd_posted': False})
        return super().unlink()
