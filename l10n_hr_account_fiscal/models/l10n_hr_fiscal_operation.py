import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

from markupsafe import Markup, escape

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..fiscal import fiscal
from ..helpers.fiscal_wrapper import FiscalExchange, fisc_handler
from .l10n_hr_business_working_hours import DAYS_OF_WEEK
from .l10n_hr_fiscal_v1_mixin import employee_oib, operator_errors

_logger = logging.getLogger(__name__)

DATE_FORMAT = '%d.%m.%Y'

# operation -> FINA service method
OPERATIONS = [
    ('get', 'Get Working Hours'),
    ('register', 'Register Working Hours'),
    ('remove', 'Remove Working Hours'),
]
MSG_TYPES = {
    'get': 'dohvatiRadnoVrijeme',
    'register': 'prijaviRadnoVrijeme',
    'remove': 'obrisiRadnoVrijeme',
}
# Fields of l10n_hr.business.working.hours frozen in every snapshot
SNAPSHOT_FIELDS = ('type', 'valid_from', 'valid_on', 'dow', 'split_shift',
                   'time_from', 'time_to', 'description')
# Fields identifying one shift; the remaining SNAPSHOT_FIELDS are its "value"
SNAPSHOT_KEY_FIELDS = ('type', 'valid_from', 'valid_on', 'dow', 'split_shift')


def _fina_date_format(value: date):
    return value and value.strftime(DATE_FORMAT) or None


def _fina_date_parse(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, DATE_FORMAT).date()
    except (ValueError, TypeError):
        return None


def _as_list(value):
    """Normalize a zeep response attribute to a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class L10nHrFiscalOperation(models.Model):
    """One record = one working hours message exchanged with the Porezna uprava (FINA) API
    for a business premise.

    The record is the single source of truth for the whole exchange:

    * it owns the API call (``get`` / ``register`` / ``remove``),
    * it is the origin of the ``l10n_hr.fiscal.log`` holding the raw XML request/response,
    * it freezes the premise working hours *before* and *after* the call,
    * it computes and stores the resulting diff (added / removed / changed shifts).

    Once executed, the record is immutable and cannot be deleted - it is history.
    """
    _name = "l10n_hr.fiscal.operation"
    _description = "Business premise fiscal operation (FINA working hours)"
    _order = 'id DESC'
    _rec_name = 'name'

    name = fields.Char(string='Reference', compute='_compute_name')
    business_premise_id = fields.Many2one(
        comodel_name='l10n_hr.business.premise',
        string='Business Premise',
        readonly=True,
        ondelete='restrict',
        index=True,
        help="The single premise this operation acts on. Empty only for a draft "
             "launcher that fans out one operation per premise in 'Business Premises'.",
    )
    business_premise_ids = fields.Many2many(
        comodel_name='l10n_hr.business.premise',
        string='Business Premises',
        help="Select several premises on a draft: executing it fans out and creates "
             "one executed operation per premise.",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='business_premise_id.company_id',
        store=True,
    )
    operation = fields.Selection(
        selection=OPERATIONS,
        string='Operation',
        required=True,
        default='get',
        help="get - fetch working hours registered at FINA (dohvatiRadnoVrijeme); "
             "local working hours are replaced with the received data\n"
             "register - register working hours flagged 'To Register' at FINA (prijaviRadnoVrijeme)\n"
             "remove - remove working hours flagged 'To Remove' at FINA (obrisiRadnoVrijeme)")
    msg_type = fields.Char(string='FINA Method', compute='_compute_msg_type')
    state = fields.Selection(
        selection=[('draft', 'Draft'),
                   ('done', 'Done'),
                   ('error', 'Error'),
                   ('uncertain', 'Needs Reconciliation')],
        string='Status',
        required=True,
        readonly=True,
        default='draft',
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Executed By',
        readonly=True,
    )
    execution_date = fields.Datetime(string='Executed On', readonly=True)

    reconciliation_of_id = fields.Many2one(
        'l10n_hr.fiscal.operation', string='Reconciliation Of', readonly=True, ondelete='restrict',
        help='A fresh GET to establish the current FINA state; not a retry of the original request.',
    )
    reconciliation_ids = fields.One2many(
        'l10n_hr.fiscal.operation', 'reconciliation_of_id', string='Reconciliation Attempts', readonly=True,
    )
    is_reconciled = fields.Boolean(compute='_compute_is_reconciled')

    @api.depends('reconciliation_ids.state')
    def _compute_is_reconciled(self):
        for op in self:
            op.is_reconciled = any(attempt.state == 'done' for attempt in op.reconciliation_ids)

    # -- communication -------------------------------------------------------
    fiscal_log_id = fields.Many2one(
        comodel_name='l10n_hr.fiscal.log',
        string='Fiscal Log',
        readonly=True,
        help="Raw XML request/response exchanged with FINA for this operation.",
    )
    request_msg = fields.Text(string='Sent Message', related='fiscal_log_id.content')
    response_msg = fields.Text(string='Reply', related='fiscal_log_id.reply_msg')
    error_msg = fields.Text(string='Error', readonly=True)

    # -- pending work (draft) ------------------------------------------------
    line_ids = fields.One2many(
        comodel_name='l10n_hr.fiscal.operation.line',
        inverse_name='operation_id',
        string='Working Hours Changes',
    )
    register_line_ids = fields.One2many(
        comodel_name='l10n_hr.fiscal.operation.line',
        inverse_name='operation_id',
        string='Working Hours to Register',
        domain=[('action', '=', 'register')],
    )
    remove_line_ids = fields.One2many(
        comodel_name='l10n_hr.fiscal.operation.line',
        inverse_name='operation_id',
        string='Working Hours to Remove',
        domain=[('action', '=', 'remove')],
    )
    remove_all = fields.Boolean('Remove All?')
    register_count = fields.Integer(compute='_compute_change_counts')
    remove_count = fields.Integer(compute='_compute_change_counts')

    # -- history -------------------------------------------------------------
    snapshot_before = fields.Json(string='Working Hours Before', readonly=True)
    snapshot_after = fields.Json(string='Working Hours After', readonly=True)
    diff = fields.Json(string='Diff', readonly=True)
    added_count = fields.Integer(string='Added', readonly=True)
    removed_count = fields.Integer(string='Removed', readonly=True)
    changed_count = fields.Integer(string='Changed', readonly=True)
    has_changes = fields.Boolean(compute='_compute_has_changes')
    snapshot_before_html = fields.Html(compute='_compute_snapshot_html', sanitize=False)
    snapshot_after_html = fields.Html(compute='_compute_snapshot_html', sanitize=False)
    diff_html = fields.Html(compute='_compute_diff_html', sanitize=False)

    # -- persistent schedule snapshots ---------------------------------------
    schedule_before_id = fields.Many2one(
        comodel_name='l10n_hr.working.hours.schedule',
        string='Schedule Before',
        readonly=True,
    )
    schedule_after_id = fields.Many2one(
        comodel_name='l10n_hr.working.hours.schedule',
        string='Schedule After',
        readonly=True,
    )

    # ------------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------------
    @api.depends('business_premise_id', 'operation', 'execution_date')
    def _compute_name(self):
        labels = dict(self._fields['operation']._description_selection(self.env))
        for op in self:
            parts = [op.business_premise_id.display_name or '', labels.get(op.operation, '')]
            if op.execution_date:
                parts.append(fields.Datetime.to_string(op.execution_date))
            op.name = ' / '.join(p for p in parts if p)

    @api.depends('operation')
    def _compute_msg_type(self):
        for op in self:
            op.msg_type = MSG_TYPES.get(op.operation)

    @api.depends('line_ids.action')
    def _compute_change_counts(self):
        for op in self:
            op.register_count = len(op.line_ids.filtered(lambda l: l.action == 'register'))
            op.remove_count = len(op.line_ids.filtered(lambda l: l.action == 'remove'))

    @api.depends('added_count', 'removed_count', 'changed_count')
    def _compute_has_changes(self):
        for op in self:
            op.has_changes = bool(op.added_count or op.removed_count or op.changed_count)

    @api.depends('snapshot_before', 'snapshot_after')
    def _compute_snapshot_html(self):
        for op in self:
            op.snapshot_before_html = op._render_snapshot(op.snapshot_before)
            op.snapshot_after_html = op._render_snapshot(op.snapshot_after)

    @api.depends('diff')
    def _compute_diff_html(self):
        for op in self:
            op.diff_html = op._render_diff(op.diff)

    # ------------------------------------------------------------------------
    # History integrity
    # ------------------------------------------------------------------------
    @api.model
    def _execution_fields(self):
        return {
            'execution_date', 'user_id', 'fiscal_log_id', 'error_msg',
            'snapshot_before', 'snapshot_after', 'diff',
            'added_count', 'removed_count', 'changed_count',
            'schedule_before_id', 'schedule_after_id', 'reconciliation_of_id', 'reconciliation_ids',
        }

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(list(self._execution_fields() | {'state'}))
        for vals in vals_list:
            effective = {**defaults, **vals}
            if effective.get('state', 'draft') != 'draft' or self._execution_fields().intersection(effective):
                raise UserError(_('Fiscal execution results can only be recorded by executing an operation.'))
        return super().create(vals_list)

    def write(self, vals):
        if any(op.state != 'draft' for op in self):
            raise UserError(_('Executed fiscal operations are history and cannot be modified.'))
        if ('state' in vals and vals['state'] != 'draft') or self._execution_fields().intersection(vals):
            raise UserError(_('Fiscal execution results can only be recorded by executing an operation.'))
        return super().write(vals)

    @api.constrains('business_premise_id', 'business_premise_ids')
    def _check_premise_access(self):
        for op in self:
            premises = op.business_premise_id | op.business_premise_ids
            premises.check_access('read')
            if op.business_premise_id and op.business_premise_ids - op.business_premise_id:
                raise UserError(_('Choose a single business premise or a batch, not both.'))
            if not self.env.su and premises.company_id - self.env.companies:
                raise AccessError(_('Fiscal operations must use premises of the enabled companies.'))

    def unlink(self):
        if any(op.state != 'draft' for op in self):
            raise UserError(_('Executed fiscal operations are history and cannot be deleted.'))
        return super().unlink()

    def _write_execution(self, vals):
        """Write bypassing the immutability guard - for the execution flow only."""
        return super().write(vals)

    # ------------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------------
    def _check_execution_access(self):
        if not self.env.su and not self.env.user.has_group('l10n_hr_account_fiscal.group_fiscal_manager'):
            raise AccessError(_('Only fiscal managers can execute working hours operations.'))
        self.check_access('write')
        self._check_premise_access()

    def action_execute(self):
        self._check_execution_access()
        generated = self.env['l10n_hr.fiscal.operation']
        launchers = self.env['l10n_hr.fiscal.operation']
        for op in self:
            if op.state == 'draft' and not op.business_premise_id and op.business_premise_ids:
                generated |= op._fan_out()
                launchers |= op
            else:
                generated |= op
        if len(generated.filtered('business_premise_id')) != len(generated.business_premise_id):
            raise UserError(_('Execute only one operation per business premise at a time.'))
        # This includes public multi-record calls, not just a single launcher.
        prepared = [(op, op._prepare_execution()) for op in generated]
        for op, values in prepared:
            op._execute(prepared=values)
        launchers.unlink()
        return generated._action_result()

    def _fan_out(self):
        """Expand a launcher into drafts; action_execute owns batch execution.

        The launcher is discarded only after the entire input set has been
        prepared and its children executed.
        """
        self.ensure_one()
        premises = self.business_premise_ids
        if not premises:
            raise UserError(_('Select at least one business premise.'))
        lines = self.line_ids.filtered(lambda line: line.action == self.operation)
        if self.operation == 'remove' and self.remove_all:
            # Remove All replaces manual selections, just as on a single premise.
            lines = self.env['l10n_hr.fiscal.operation.line']
        else:
            self._check_working_hours_scope(premises)
        children = self.create([
            {
                'business_premise_id': premise.id,
                'business_premise_ids': [Command.clear()],
                'operation': self.operation,
                'remove_all': self.remove_all,
                'line_ids': [
                    Command.create(line.copy_data({'operation_id': False})[0])
                    for line in lines
                    if not line.working_hours_id or line.working_hours_id.business_premise_id == premise
                ],
            }
            for premise in premises])
        # Validate every premise before the first external side effect. Inline
        # register lines are shared; references always stay with their own premise.
        for child in children:
            child._prepare_remove_all_lines()
            child._check_executable()
        return children

    def _action_result(self):
        """Open the single executed operation, or the list when several were run."""
        if len(self) == 1:
            return self.action_open()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fiscal Operations'),
            'res_model': self._name,
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.ids)],
        }

    def action_open(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fiscal Operation'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _check_executable(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft fiscal operations can be executed.'))
        if not self.business_premise_id:
            raise UserError(_('A fiscal operation needs a business premise.'))
        if self.operation == 'register' and not self.register_count:
            raise UserError(_('There are no working hours selected to be registered!'))
        if self.operation == 'remove' and not self.remove_count and not self.remove_all:
            raise UserError(_('There are no working hours selected to be removed!'))
        self._check_working_hours_scope(self.business_premise_id)
        if self.operation in ('register', 'remove'):
            unresolved = self.search([
                ('business_premise_id', '=', self.business_premise_id.id),
                ('state', '=', 'uncertain'),
                ('reconciliation_of_id', '=', False),
            ]).filtered(lambda operation: not operation.is_reconciled)
            if unresolved:
                raise UserError(_(
                    'Reconcile the uncertain working hours operations for %(premise)s before sending more changes.',
                    premise=self.business_premise_id.display_name,
                ))
        if self.operation == 'register':
            self.line_ids.filtered(lambda line: line.action == 'register')._check_register_has_data()
        if self.operation == 'remove':
            if self.line_ids.filtered(lambda line: line.action == 'remove' and not line.working_hours_id):
                raise UserError(_('Selected working hours no longer exist. Select existing entries to remove.'))
            self._check_complete_remove_dates()

    def _check_working_hours_scope(self, premises):
        """Never send or delete a referenced shift under another premise's code."""
        self.ensure_one()
        referenced = self.line_ids.working_hours_id
        if referenced.business_premise_id - premises:
            raise UserError(_(
                'Selected working hours must belong to the selected business premise(s).'
            ))

    def _check_complete_remove_dates(self):
        """FINA identifies a removal by date, not by weekday or individual shift."""
        self.ensure_one()
        selected = self.line_ids.filtered(lambda line: line.action == 'remove').working_hours_id
        regular_dates = set(selected.filtered(lambda hours: hours.type == 'regular').mapped('valid_from'))
        exception_dates = set(selected.filtered(lambda hours: hours.type == 'exception').mapped('valid_on'))
        if False in regular_dates or False in exception_dates:
            raise UserError(_('Working hours to remove must have a valid date.'))
        affected = self.business_premise_id._get_all_working_hours().filtered(
            lambda hours: (hours.type == 'regular' and hours.valid_from in regular_dates)
            or (hours.type == 'exception' and hours.valid_on in exception_dates)
        )
        if affected - selected:
            raise UserError(_(
                'FINA removes all working hours for each selected date. '
                'Select every entry for those dates in %(premise)s before removing them.',
                premise=self.business_premise_id.display_name,
            ))

    def _create_schedule_snapshot(self):
        """Create a persistent schedule snapshot for the premise and return it."""
        self.ensure_one()
        # Use a fixed 30-day window around today so the snapshot is useful without
        # being huge. The operation itself records the exact date of the change.
        today = fields.Date.context_today(self)
        # Only this private execution path may create/rebuild audit snapshots.
        schedule = self.env['l10n_hr.working.hours.schedule'].sudo().create({
            'date_from': today,
            'date_to': today + timedelta(days=30),
            'business_premise_ids': [(6, 0, self.business_premise_id.ids)],
            'company_id': self.company_id.id,
            'fiscal_operation_id': self.id,
        })
        schedule.action_compute()
        return schedule

    def _prepare_remove_all_lines(self):
        """Auto-populate remove lines when the operation should delete every working
        hour of the selected business premise.
        """
        self.ensure_one()
        if self.operation != 'remove' or not self.remove_all or self.state != 'draft':
            return
        self.line_ids.unlink()
        working_hours = self.business_premise_id._get_all_working_hours()
        if not working_hours:
            return
        self.env['l10n_hr.fiscal.operation.line'].create([
            {
                'operation_id': self.id,
                'action': 'remove',
                'working_hours_id': wh.id,
                'type': wh.type,
                'description': wh.description,
                'dow': wh.dow,
                'valid_from': wh.valid_from,
                'valid_on': wh.valid_on,
                'time_from': wh.time_from,
                'time_to': wh.time_to,
                'split_shift': wh.split_shift,
            }
            for wh in working_hours
        ])

    def _prepare_execution(self):
        """All local preparation happens before dispatch (for every batch child)."""
        self.ensure_one()
        self._check_execution_access()
        self.lock_for_update(allow_referencing=True)
        if self.business_premise_id:
            self.business_premise_id._lock_fiscal_execution()
        self._prepare_remove_all_lines()
        self._check_executable()
        # Keep the values in history even if a later get/remove deletes the source.
        for line in self.line_ids.filtered('working_hours_id'):
            values = line._to_working_hours_vals(self.business_premise_id.id)
            values.pop('business_premise_id')
            line.write(values)
        before = self.business_premise_id._get_working_hours_snapshot()
        schedule_before = self._create_schedule_snapshot()
        return {
            'execution_date': fields.Datetime.now(),
            'user_id': self.env.user.id,
            'snapshot_before': before,
            'snapshot_after': before,
            'schedule_before_id': schedule_before.id,
            'schedule_after_id': schedule_before.id,
            'diff': [], 'added_count': 0, 'removed_count': 0, 'changed_count': 0,
            'error_msg': False,
        }

    def _execute(self, prepared=None):
        """Retain the exchange; roll back only local application on failure.

        Savepoints do not make the external service and this transaction atomic.
        Recorded operational failures return normally so a batch can continue.
        """
        self.ensure_one()
        self._check_execution_access()
        vals = dict(prepared) if prepared is not None else self._prepare_execution()
        if self.operation == 'remove' and self.remove_all and not self.line_ids:
            self._write_execution({**vals, 'state': 'done'})
            return True

        try:
            # The wrapper sends and logs, but does not change local working hours.
            exchange = getattr(self, '_call_%s' % self.operation)()
        except Exception as error:
            _logger.exception('Unexpected fiscal exchange failure for operation %s', self.id)
            exchange = FiscalExchange('uncertain', error=str(error))
        vals['fiscal_log_id'] = exchange.log.id if exchange.log else False
        if exchange.status == 'success':
            try:
                # The log is outside this savepoint and survives an apply/DB error.
                with self.env.cr.savepoint():
                    self._handle_fisc_response(exchange.response, self.msg_type)
                    after = self.business_premise_id._get_working_hours_snapshot()
                    diff = self._compute_diff(vals['snapshot_before'], after)
                    self._write_execution({
                        **vals, 'state': 'done', 'snapshot_after': after,
                        'schedule_after_id': self._create_schedule_snapshot().id,
                        'diff': diff,
                        'added_count': sum(line['status'] == 'added' for line in diff),
                        'removed_count': sum(line['status'] == 'removed' for line in diff),
                        'changed_count': sum(line['status'] == 'changed' for line in diff),
                    })
                return True
            except Exception as error:
                _logger.exception('Local application failed after FINA replied to operation %s', self.id)
                exchange = FiscalExchange('uncertain', log=exchange.log, error=str(error))
                # A verified success was received, but local completion failed.
                vals['state'] = 'uncertain'
        else:
            vals['state'] = (
                'uncertain' if exchange.status == 'uncertain' and self.operation != 'get' else 'error'
            )
        vals['error_msg'] = exchange.error or _('The fiscal exchange did not complete.')
        if vals['state'] == 'uncertain':
            vals['error_msg'] += '\n' + _(
                'Do not resend this change. Fetch the current working hours from FINA to reconcile the premise.'
            )
        # Do not rebuild the snapshot that just failed. The savepoint restored the
        # before-state, which is also the unchanged local after-state.
        self._write_execution(vals)
        return False

    def action_reconcile(self):
        """Establish current FINA state through a new GET; never retry a change."""
        self.ensure_one()
        self._check_execution_access()
        self.lock_for_update(allow_referencing=True)
        if self.state != 'uncertain':
            raise UserError(_('Only an uncertain fiscal operation needs reconciliation.'))
        if self.reconciliation_of_id:
            return self.reconciliation_of_id.action_reconcile()
        completed = self.reconciliation_ids.filtered(lambda attempt: attempt.state == 'done')
        if completed:
            return completed[:1].action_open()
        recovery = self.create({
            'business_premise_id': self.business_premise_id.id,
            'business_premise_ids': [Command.clear()],
            'operation': 'get',
        })
        recovery._write_execution({'reconciliation_of_id': self.id})
        recovery._execute()
        return recovery.action_open()

    def _find_fiscal_log(self):
        self.ensure_one()
        return self.env['l10n_hr.fiscal.log'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
        ], order='id DESC', limit=1)

    # ------------------------------------------------------------------------
    # FINA API calls (fisc_handler sends and logs; _execute owns local application)
    # ------------------------------------------------------------------------
    def _new_fiscal_client(self):
        return fiscal.Fiscalization(self.company_id.get_fiscal_data())

    def _l10n_hr_operator_oib(self):
        """Return ``OibOper``: the OIB of the sending user's employee, or refuse to send."""
        self.ensure_one()
        operator = self.env.user.with_company(self.company_id).employee_id
        errors = operator_errors(operator, self.env.user, self.company_id)
        if errors:
            raise UserError("\n".join(errors))
        return employee_oib(operator)

    @fisc_handler(msg_type='dohvatiRadnoVrijeme', handle_response=False)
    def _call_get(self):
        fisk = self._new_fiscal_client()
        return dict(
            Zaglavlje=fisk.create_request_header(),
            Oib=self.company_id.company_registry,
            OznPosPr=self.business_premise_id.l10n_hr_fiscal_code,
            OibOper=self._l10n_hr_operator_oib(),
            VrstaRadnogVremena='SVE',
        )

    @fisc_handler(msg_type='prijaviRadnoVrijeme', handle_response=False)
    def _call_register(self):
        fisk = self._new_fiscal_client()
        return dict(
            Zaglavlje=fisk.create_request_header(),
            PoslovniProstor=self._prepare_register_payload(fisk),
            OibOper=self._l10n_hr_operator_oib(),
        )

    @fisc_handler(msg_type='obrisiRadnoVrijeme', handle_response=False)
    def _call_remove(self):
        fisk = self._new_fiscal_client()
        return dict(
            Zaglavlje=fisk.create_request_header(),
            PoslovniProstor=self._prepare_remove_payload(fisk),
            OibOper=self._l10n_hr_operator_oib(),
        )

    def _handle_fisc_response(self, response, msg_type):
        """Apply a *successful* FINA response to the business premise."""
        self.ensure_one()
        premise = self.business_premise_id
        if msg_type == 'dohvatiRadnoVrijeme':
            premise._replace_working_hours(self._parse_get_response(response))
        elif msg_type == 'prijaviRadnoVrijeme':
            # Create real working hours records for register lines that do not
            # already reference an existing record.
            for line in self.line_ids.filtered(
                    lambda l: l.action == 'register' and not l.working_hours_id
            ):
                self.env['l10n_hr.business.working.hours'].create(
                    line._to_working_hours_vals(premise.id)
                )
        elif msg_type == 'obrisiRadnoVrijeme':
            # Delete the working hours records referenced by remove lines.
            self.line_ids.filtered(lambda l: l.action == 'remove').mapped('working_hours_id').unlink()

    # -- request payloads ----------------------------------------------------
    def _prepare_register_payload(self, fisk):
        tf = fisk.type_factory
        premise = self.business_premise_id
        register_lines = self.line_ids.filtered(lambda l: l.action == 'register')

        def _effective_values(line):
            """Return the values to send, whether inline or from a referenced record."""
            if line.working_hours_id:
                wh = line.working_hours_id
                return {
                    'type': wh.type,
                    'valid_from': wh.valid_from,
                    'valid_on': wh.valid_on,
                    'description': wh.description,
                    'dow': wh.dow,
                    'time_from': wh.time_from,
                    'time_to': wh.time_to,
                    'split_shift': wh.split_shift,
                }
            return {
                'type': line.type,
                'valid_from': line.valid_from,
                'valid_on': line.valid_on,
                'description': line.description,
                'dow': line.dow,
                'time_from': line.time_from,
                'time_to': line.time_to,
                'split_shift': line.split_shift,
            }

        regulars = [_effective_values(line) for line in register_lines if _effective_values(line)['type'] == 'regular']
        exceptions = [_effective_values(line) for line in register_lines if
                      _effective_values(line)['type'] == 'exception']

        redovno = []
        regular_groups = defaultdict(list)
        for values in regulars:
            regular_groups[values['valid_from']].append(values)
        for valid_from, group in sorted(regular_groups.items()):
            desc = ', '.join(sorted({d for d in [v['description'] for v in group] if d}))
            regular = tf.RedovnoType(DatumOd=_fina_date_format(valid_from), Napomena=desc or None)
            # zeep does not always pre-initialize these lists
            regular.Jednokratno = regular.Jednokratno or []
            regular.Dvokratno = regular.Dvokratno or []
            for values in group:
                if values['split_shift']:
                    regular.Dvokratno.append(tf.DvokratnoType(
                        DanUTjednu=values['dow'], RadnoVrijemeOd=values['time_from'], RadnoVrijemeDo=values['time_to']))
                else:
                    regular.Jednokratno.append(tf.JednokratnoType(
                        DanUTjednu=values['dow'], RadnoVrijemeOd=values['time_from'], RadnoVrijemeDo=values['time_to']))
            redovno.append(regular)

        iznimke = []
        exception_groups = defaultdict(list)
        for values in exceptions:
            exception_groups[values['valid_on']].append(values)
        for valid_on, group in sorted(exception_groups.items()):
            exception = tf.IznimkeType(Datum=_fina_date_format(valid_on))
            exception.Jednokratno = exception.Jednokratno or []
            exception.Dvokratno = exception.Dvokratno or []
            for values in group:
                if values['split_shift']:
                    exception.Dvokratno.append(tf.DvokratnoIznimkeType(
                        DioDvokratnog=values['split_shift'], RadnoVrijemeOd=values['time_from'],
                        RadnoVrijemeDo=values['time_to']))
                else:
                    exception.Jednokratno.append(tf.JednokratnoIznimkeType(
                        RadnoVrijemeOd=values['time_from'], RadnoVrijemeDo=values['time_to']))
            iznimke.append(exception)

        return tf.PoslovniProstorType(
            Oib=self.company_id.company_registry,
            OznPosPr=premise.l10n_hr_fiscal_code,
            RadnoVrijeme=tf.RadnoVrijemeType(Redovno=redovno, Iznimke=iznimke),
        )

    def _prepare_remove_payload(self, fisk):
        tf = fisk.type_factory
        remove_lines = self.line_ids.filtered(lambda l: l.action == 'remove')
        regulars = remove_lines.filtered(lambda l: l.working_hours_id.type == 'regular')
        exceptions = remove_lines.filtered(lambda l: l.working_hours_id.type == 'exception')
        redovno = [dict(DatumOd=_fina_date_format(d))
                   for d in sorted(set(regulars.mapped('working_hours_id.valid_from'))) if d]
        iznimke = [dict(Datum=_fina_date_format(d))
                   for d in sorted(set(exceptions.mapped('working_hours_id.valid_on'))) if d]
        return tf.PoslovniProstorType(
            Oib=self.company_id.company_registry,
            OznPosPr=self.business_premise_id.l10n_hr_fiscal_code,
            BrisanjeRadnogVremena=tf.RadnoVrijemeBrisanjeType(Redovno=redovno, Iznimke=iznimke),
        )

    # -- response parsing ----------------------------------------------------
    def _parse_get_response(self, response):
        """Parse DohvatiRadnoVrijemeOdgovor into working hours create vals (without premise)."""
        if response is None or not hasattr(response, 'PoslovniProstor'):
            raise UserError(_('The working hours response is incomplete; local hours were not replaced.'))
        premise = response.PoslovniProstor
        # The 1.10 response schema allows an absent PoslovniProstor for no hours.
        if premise is None:
            return []
        code = getattr(premise, 'OznPosPr', None)
        if code and code != self.business_premise_id.l10n_hr_fiscal_code:
            raise UserError(_('The working hours response belongs to another business premise.'))
        oib = getattr(premise, 'Oib', None)
        if oib and oib != self.company_id.company_registry:
            raise UserError(_('The working hours response belongs to another company.'))
        radno_vrijeme = getattr(premise, 'RadnoVrijeme', None)
        if (radno_vrijeme is None or not hasattr(radno_vrijeme, 'Redovno')
                or not hasattr(radno_vrijeme, 'Iznimke')):
            raise UserError(_('The working hours response is incomplete; local hours were not replaced.'))
        vals_list = []
        for regular in _as_list(getattr(radno_vrijeme, 'Redovno', None)):
            if getattr(regular, 'PoDogovoru', None) or getattr(regular, 'ParniNeparni', None):
                raise UserError(_('The received working hours variant is not supported; local hours were not replaced.'))
            parsed = self._parse_regular(regular)
            if not parsed or any(not values['valid_from'] for values in parsed):
                raise UserError(_('The received regular working hours are incomplete or have an invalid date.'))
            vals_list.extend(parsed)
        for exception in _as_list(getattr(radno_vrijeme, 'Iznimke', None)):
            parsed = self._parse_exception(exception)
            if not parsed or any(not values['valid_on'] for values in parsed):
                raise UserError(_('The received exception working hours are incomplete or have an invalid date.'))
            vals_list.extend(parsed)
        return vals_list

    @staticmethod
    def _parse_regular(regular):
        base = {
            'type': 'regular',
            'valid_from': _fina_date_parse(getattr(regular, 'DatumOd', None)),
            'description': getattr(regular, 'Napomena', None),
        }
        vals_list = []
        for shift in _as_list(getattr(regular, 'Jednokratno', None)):
            vals_list.append(dict(base, dow=getattr(shift, 'DanUTjednu', None),
                                  time_from=getattr(shift, 'RadnoVrijemeOd', None),
                                  time_to=getattr(shift, 'RadnoVrijemeDo', None),
                                  split_shift=False))
        for shift in _as_list(getattr(regular, 'Dvokratno', None)):
            vals_list.append(dict(base, dow=getattr(shift, 'DanUTjednu', None),
                                  time_from=getattr(shift, 'RadnoVrijemeOd', None),
                                  time_to=getattr(shift, 'RadnoVrijemeDo', None),
                                  split_shift=getattr(shift, 'DioDvokratnog', None)))
        for unsupported in ('PoDogovoru', 'ParniNeparni'):
            if getattr(regular, unsupported, None):
                _logger.warning("Regular working hours '%s' received from FINA are not supported.", unsupported)
        return vals_list

    @staticmethod
    def _parse_exception(exception):
        valid_on = _fina_date_parse(getattr(exception, 'Datum', None))
        base = {
            'type': 'exception',
            'valid_on': valid_on,
            'dow': valid_on and str(valid_on.isoweekday()) or None,
        }
        vals_list = []
        for shift in _as_list(getattr(exception, 'Jednokratno', None)):
            vals_list.append(dict(base, time_from=getattr(shift, 'RadnoVrijemeOd', None),
                                  time_to=getattr(shift, 'RadnoVrijemeDo', None),
                                  split_shift=False))
        for shift in _as_list(getattr(exception, 'Dvokratno', None)):
            vals_list.append(dict(base, time_from=getattr(shift, 'RadnoVrijemeOd', None),
                                  time_to=getattr(shift, 'RadnoVrijemeDo', None),
                                  split_shift=getattr(shift, 'DioDvokratnog', None)))
        return vals_list

    # ------------------------------------------------------------------------
    # Snapshots & diff
    # ------------------------------------------------------------------------
    @staticmethod
    def _snapshot_key(line):
        return tuple(line.get(f) or '' for f in SNAPSHOT_KEY_FIELDS)

    @staticmethod
    def _snapshot_value(line):
        return {f: line.get(f) or '' for f in SNAPSHOT_FIELDS if f not in SNAPSHOT_KEY_FIELDS}

    @api.model
    def _compute_diff(self, before, after):
        """Diff two snapshots (lists of dicts) into a list of
        ``{'status': added|removed|changed, 'key': {...}, 'before': {...}|None, 'after': {...}|None}``.

        A shift is identified by ``SNAPSHOT_KEY_FIELDS``; identical keys with different
        times/description are reported as *changed*. Unchanged shifts are not listed.
        """

        def index(snapshot):
            grouped = {}
            for line in snapshot or []:
                grouped.setdefault(self._snapshot_key(line), []).append(self._snapshot_value(line))
            return grouped

        before_idx, after_idx = index(before), index(after)
        diff = []
        for key in sorted(set(before_idx) | set(after_idx)):
            key_vals = dict(zip(SNAPSHOT_KEY_FIELDS, key))
            olds = list(before_idx.get(key, []))
            news = list(after_idx.get(key, []))
            # drop identical pairs
            for value in list(olds):
                if value in news:
                    olds.remove(value)
                    news.remove(value)
            while olds and news:
                diff.append({'status': 'changed', 'key': key_vals, 'before': olds.pop(0), 'after': news.pop(0)})
            diff.extend({'status': 'removed', 'key': key_vals, 'before': old, 'after': None} for old in olds)
            diff.extend({'status': 'added', 'key': key_vals, 'before': None, 'after': new} for new in news)
        return diff

    # -- rendering -----------------------------------------------------------
    _STATUS_STYLE = {
        'added': ('table-success', '+'),
        'removed': ('table-danger', '−'),
        'changed': ('table-warning', '~'),
    }

    def _describe_key(self, key):
        """Human readable columns for a snapshot key: type, date, day, shift."""
        types = dict(self.env['l10n_hr.business.working.hours']._fields['type']._description_selection(self.env))
        days = dict(DAYS_OF_WEEK)
        shifts = dict(
            self.env['l10n_hr.business.working.hours']._fields['split_shift']._description_selection(self.env))
        return (
            types.get(key.get('type'), key.get('type') or ''),
            key.get('valid_from') or key.get('valid_on') or '',
            days.get(key.get('dow'), key.get('dow') or ''),
            shifts.get(key.get('split_shift'), key.get('split_shift') or ''),
        )

    @staticmethod
    def _describe_value(value):
        if not value:
            return ''
        text = '%s - %s' % (value.get('time_from') or '', value.get('time_to') or '')
        if value.get('description'):
            text += ' (%s)' % value['description']
        return text

    def _render_table(self, headers, rows):
        if not rows:
            return Markup('<p class="text-muted fst-italic">%s</p>') % _('Nothing to show.')
        head = Markup('').join(Markup('<th>%s</th>') % h for h in headers)
        body = Markup('').join(rows)
        return Markup('<table class="table table-sm table-striped o_l10n_hr_fiscal_snapshot">'
                      '<thead><tr>%s</tr></thead><tbody>%s</tbody></table>') % (head, body)

    def _render_snapshot(self, snapshot):
        headers = (_('Type'), _('Date'), _('Day'), _('Shift'), _('From'), _('To'), _('Description'))
        rows = []
        for line in sorted(snapshot or [], key=self._snapshot_key):
            cells = self._describe_key(line) + (line.get('time_from') or '', line.get('time_to') or '',
                                                line.get('description') or '')
            rows.append(Markup('<tr>%s</tr>') % Markup('').join(Markup('<td>%s</td>') % escape(c) for c in cells))
        return self._render_table(headers, rows)

    def _render_diff(self, diff):
        headers = ('', _('Type'), _('Date'), _('Day'), _('Shift'), _('Before'), _('After'))
        rows = []
        for line in diff or []:
            css, sign = self._STATUS_STYLE.get(line['status'], ('', ''))
            cells = (sign,) + self._describe_key(line['key']) + (
                self._describe_value(line.get('before')), self._describe_value(line.get('after')))
            rows.append(Markup('<tr class="%s">%s</tr>') % (
                css, Markup('').join(Markup('<td>%s</td>') % escape(c) for c in cells)))
        if not rows and self.state != 'draft':
            return Markup('<p class="text-muted fst-italic">%s</p>') % _('No changes on the business premise.')
        return self._render_table(headers, rows)
