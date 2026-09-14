import logging
from datetime import date, datetime

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..fiscal import fiscal
from ..helpers.fiscal_wrapper import fisc_handler
from .l10n_hr_business_working_hours import DAYS_OF_WEEK

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
                   ('error', 'Error')],
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
    to_register_count = fields.Integer(compute='_compute_pending_counts')
    to_remove_count = fields.Integer(compute='_compute_pending_counts')

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

    @api.depends('business_premise_id.regular_working_hours_ids.to_register',
                 'business_premise_id.regular_working_hours_ids.to_remove',
                 'business_premise_id.exception_working_hours_ids.to_register',
                 'business_premise_id.exception_working_hours_ids.to_remove')
    def _compute_pending_counts(self):
        for op in self:
            hours = op.business_premise_id._get_all_working_hours()
            op.to_register_count = len(hours.filtered('to_register'))
            op.to_remove_count = len(hours.filtered('to_remove'))

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
    def write(self, vals):
        if not self.env.context.get('l10n_hr_fiscal_operation_execute'):
            executed = self.filtered(lambda op: op.state != 'draft')
            if executed:
                raise UserError(_('Executed fiscal operations are history and cannot be modified.'))
        return super().write(vals)

    def unlink(self):
        if any(op.state != 'draft' for op in self):
            raise UserError(_('Executed fiscal operations are history and cannot be deleted.'))
        return super().unlink()

    def _write_execution(self, vals):
        """Write bypassing the immutability guard - for the execution flow only."""
        return self.with_context(l10n_hr_fiscal_operation_execute=True).write(vals)

    # ------------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------------
    def action_execute(self):
        generated = self.env['l10n_hr.fiscal.operation']
        for op in self:
            if op.state == 'draft' and not op.business_premise_id and op.business_premise_ids:
                generated |= op._fan_out()
            else:
                op._execute()
                generated |= op
        return generated._action_result()

    def _fan_out(self):
        """A draft launcher spawns one executed operation per selected premise.

        The launcher itself carries no history and is discarded once its children
        have been created and executed.
        """
        self.ensure_one()
        premises = self.business_premise_ids
        if not premises:
            raise UserError(_('Select at least one business premise.'))
        children = self.create([
            {'business_premise_id': premise.id, 'operation': self.operation}
            for premise in premises])
        for child in children:
            child._execute()
        self.unlink()
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
        if self.operation == 'register' and not self.to_register_count:
            raise UserError(_('There are no working hours flagged to be registered!'))
        if self.operation == 'remove' and not self.to_remove_count:
            raise UserError(_('There are no working hours flagged to be removed!'))

    def _execute(self):
        """Run the API call and freeze before/after state.

        Communication errors are caught and stored on the record instead of raised, so
        the operation (and its fiscal log) survive as history even when FINA rejects it.
        """
        self._check_executable()
        premise = self.business_premise_id
        before = premise._get_working_hours_snapshot()
        vals = {
            'execution_date': fields.Datetime.now(),
            'user_id': self.env.user.id,
            'snapshot_before': before,
            'error_msg': False,
        }
        handler = getattr(self, '_call_%s' % self.operation)
        try:
            handler()
            vals['state'] = 'done'
        except UserError as error:
            vals.update(state='error', error_msg=str(error))
        # The log was created with this operation as origin (res_model/res_id): no guessing.
        # Even when nothing was raised, silent error logging on the company
        # may have swallowed a FINA error - the log is the authority.
        log = self._find_fiscal_log()
        vals['fiscal_log_id'] = log.id
        if vals['state'] == 'done' and log and log.error_msg and log.error_msg != 'OK':
            vals.update(state='error', error_msg=log.error_msg)
        after = premise._get_working_hours_snapshot()
        diff = self._compute_diff(before, after)
        vals.update({
            'snapshot_after': after,
            'diff': diff,
            'added_count': sum(1 for line in diff if line['status'] == 'added'),
            'removed_count': sum(1 for line in diff if line['status'] == 'removed'),
            'changed_count': sum(1 for line in diff if line['status'] == 'changed'),
        })
        self._write_execution(vals)
        return self.state == 'done'

    def _find_fiscal_log(self):
        self.ensure_one()
        return self.env['l10n_hr.fiscal.log'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
        ], order='id DESC', limit=1)

    # ------------------------------------------------------------------------
    # FINA API calls (fisc_handler builds the client, sends, logs and dispatches
    # the successful response to _handle_fisc_response)
    # ------------------------------------------------------------------------
    def _new_fiscal_client(self):
        return fiscal.Fiscalization(self.company_id.get_fiscal_data())

    @fisc_handler(msg_type='dohvatiRadnoVrijeme')
    def _call_get(self):
        fisk = self._new_fiscal_client()
        return dict(
            Zaglavlje=fisk.create_request_header(),
            Oib=self.company_id.company_registry,
            OznPosPr=self.business_premise_id.l10n_hr_fiscal_code,
            OibOper=self.env.user.company_registry,
            VrstaRadnogVremena='SVE',
        )

    @fisc_handler(msg_type='prijaviRadnoVrijeme')
    def _call_register(self):
        fisk = self._new_fiscal_client()
        return dict(
            Zaglavlje=fisk.create_request_header(),
            PoslovniProstor=self._prepare_register_payload(fisk),
            OibOper=self.env.user.company_registry,
        )

    @fisc_handler(msg_type='obrisiRadnoVrijeme')
    def _call_remove(self):
        fisk = self._new_fiscal_client()
        return dict(
            Zaglavlje=fisk.create_request_header(),
            PoslovniProstor=self._prepare_remove_payload(fisk),
            OibOper=self.env.user.company_registry,
        )

    def _handle_fisc_response(self, response, msg_type):
        """Apply a *successful* FINA response to the business premise."""
        self.ensure_one()
        premise = self.business_premise_id
        if msg_type == 'dohvatiRadnoVrijeme':
            premise._replace_working_hours(self._parse_get_response(response))
        elif msg_type == 'prijaviRadnoVrijeme':
            # registered - unflag, prevent double registration
            premise._get_all_working_hours().filtered('to_register').write({'to_register': False})
        elif msg_type == 'obrisiRadnoVrijeme':
            premise._get_all_working_hours().filtered('to_remove').unlink()

    # -- request payloads ----------------------------------------------------
    def _prepare_register_payload(self, fisk):
        tf = fisk.type_factory
        premise = self.business_premise_id
        regulars = premise.regular_working_hours_ids.filtered('to_register')
        exceptions = premise.exception_working_hours_ids.filtered('to_register')

        redovno = []
        for valid_from, group in regulars.grouped('valid_from').items():
            # descriptions ought to be identical within one DatumOd group
            desc = ', '.join(sorted({d for d in group.mapped('description') if d}))
            regular = tf.RedovnoType(DatumOd=_fina_date_format(valid_from), Napomena=desc or None)
            # zeep does not always pre-initialize these lists
            regular.Jednokratno = regular.Jednokratno or []
            regular.Dvokratno = regular.Dvokratno or []
            for line in group:
                if line.split_shift:
                    regular.Dvokratno.append(tf.DvokratnoType(
                        DanUTjednu=line.dow, RadnoVrijemeOd=line.time_from, RadnoVrijemeDo=line.time_to))
                else:
                    regular.Jednokratno.append(tf.JednokratnoType(
                        DanUTjednu=line.dow, RadnoVrijemeOd=line.time_from, RadnoVrijemeDo=line.time_to))
            redovno.append(regular)

        iznimke = []
        for valid_on, group in exceptions.grouped('valid_on').items():
            exception = tf.IznimkeType(Datum=_fina_date_format(valid_on))
            exception.Jednokratno = exception.Jednokratno or []
            exception.Dvokratno = exception.Dvokratno or []
            for line in group:
                if line.split_shift:
                    exception.Dvokratno.append(tf.DvokratnoIznimkeType(
                        DioDvokratnog=line.split_shift, RadnoVrijemeOd=line.time_from, RadnoVrijemeDo=line.time_to))
                else:
                    exception.Jednokratno.append(tf.JednokratnoIznimkeType(
                        RadnoVrijemeOd=line.time_from, RadnoVrijemeDo=line.time_to))
            iznimke.append(exception)

        return tf.PoslovniProstorType(
            Oib=self.company_id.company_registry,
            OznPosPr=premise.l10n_hr_fiscal_code,
            RadnoVrijeme=tf.RadnoVrijemeType(Redovno=redovno, Iznimke=iznimke),
        )

    def _prepare_remove_payload(self, fisk):
        tf = fisk.type_factory
        premise = self.business_premise_id
        regulars = premise.regular_working_hours_ids.filtered('to_remove')
        exceptions = premise.exception_working_hours_ids.filtered('to_remove')
        redovno = [dict(DatumOd=_fina_date_format(d))
                   for d in sorted(set(regulars.mapped('valid_from'))) if d]
        iznimke = [dict(Datum=_fina_date_format(d))
                   for d in sorted(set(exceptions.mapped('valid_on'))) if d]
        return tf.PoslovniProstorType(
            Oib=self.company_id.company_registry,
            OznPosPr=premise.l10n_hr_fiscal_code,
            BrisanjeRadnogVremena=tf.RadnoVrijemeBrisanjeType(Redovno=redovno, Iznimke=iznimke),
        )

    # -- response parsing ----------------------------------------------------
    def _parse_get_response(self, response):
        """Parse DohvatiRadnoVrijemeOdgovor into working hours create vals (without premise)."""
        radno_vrijeme = getattr(getattr(response, 'PoslovniProstor', None), 'RadnoVrijeme', None)
        if not radno_vrijeme:
            return []
        vals_list = []
        for regular in _as_list(getattr(radno_vrijeme, 'Redovno', None)):
            vals_list.extend(self._parse_regular(regular))
        for exception in _as_list(getattr(radno_vrijeme, 'Iznimke', None)):
            vals_list.extend(self._parse_exception(exception))
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
