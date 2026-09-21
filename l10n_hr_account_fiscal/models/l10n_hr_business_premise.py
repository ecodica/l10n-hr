from datetime import date

from odoo import _, api, fields, models

from .l10n_hr_fiscal_operation import SNAPSHOT_FIELDS


class L10nHrBusinessPremise(models.Model):
    _inherit = "l10n_hr.business.premise"

    l10n_hr_fiscal_log_ids = fields.One2many(
        comodel_name="l10n_hr.fiscal.log",
        inverse_name="business_premise_id",
        string="Fiscal message logs",
        help="Log of all messages sent and received for FINA",
        readonly=True,
    )
    regular_working_hours_ids = fields.One2many(
        comodel_name='l10n_hr.business.working.hours',
        inverse_name='business_premise_id',
        string='Regular Working Hours',
        domain=[('type', '=', 'regular')],
    )
    exception_working_hours_ids = fields.One2many(
        comodel_name='l10n_hr.business.working.hours',
        inverse_name='business_premise_id',
        string='Exception Working Hours',
        domain=[('type', '=', 'exception')],
    )
    regular_working_hours_valid_from = fields.Date('Regular Working Hours Valid From')
    regular_working_hours_valid_to = fields.Date('Regular Working Hours Valid To')
    regular_working_hours_note = fields.Text('Regular Working Hours Note')
    fiscal_operation_ids = fields.One2many(
        comodel_name='l10n_hr.fiscal.operation',
        inverse_name='business_premise_id',
        string='Fiscal Operations',
        readonly=True,
    )
    fiscal_operation_count = fields.Integer(compute='_compute_fiscal_operation_count')
    last_fiscal_operation_id = fields.Many2one(
        comodel_name='l10n_hr.fiscal.operation',
        string='Last Fiscal Operation',
        compute='_compute_fiscal_operation_count',
    )

    @api.depends('fiscal_operation_ids.state')
    def _compute_fiscal_operation_count(self):
        for premise in self:
            # fiscal_operation_ids is ordered id DESC, so the first executed one is the latest
            executed = premise.fiscal_operation_ids.filtered(lambda op: op.state != 'draft')
            premise.fiscal_operation_count = len(executed)
            premise.last_fiscal_operation_id = executed[:1]

    # ------------------------------------------------------------------------
    # Working hours helpers used by l10n_hr.fiscal.operation
    # ------------------------------------------------------------------------
    def _get_all_working_hours(self):
        return self.regular_working_hours_ids + self.exception_working_hours_ids

    def get_working_hours_for_date(self, day):
        """Return the working hours effective on ``day`` for this premise.

        Resolution rules (single source of truth for the schedule master model):

        * an exception registered for that exact date wins over everything else;
        * otherwise the regular shifts for that day of week whose ``valid_from`` is
          the most recent one still in effect (``valid_from <= day``) apply;
        * an empty recordset means the premise is closed that day.
        """
        self.ensure_one()
        if isinstance(day, str):
            day = fields.Date.to_date(day)
        exceptions = self.exception_working_hours_ids.filtered(lambda line: line.valid_on == day)
        if exceptions:
            return exceptions.sorted(lambda line: (line.split_shift or '', line.time_from or ''))
        dow = str(day.isoweekday())
        regular = self.regular_working_hours_ids.filtered(
            lambda line: line.dow == dow and (not line.valid_from or line.valid_from <= day))
        valid_dates = [line.valid_from for line in regular if line.valid_from]
        latest = max(valid_dates) if valid_dates else False
        regular = regular.filtered(lambda line: (line.valid_from or False) == latest)
        return regular.sorted(lambda line: (line.split_shift or '', line.time_from or ''))

    def _get_working_hours_snapshot(self):
        """JSON-serializable frozen copy of the current working hours."""
        self.ensure_one()
        snapshot = []
        for line in self._get_all_working_hours():
            vals = {}
            for field_name in SNAPSHOT_FIELDS:
                value = line[field_name]
                vals[field_name] = fields.Date.to_string(value) if isinstance(value, date) else (value or None)
            snapshot.append(vals)
        return snapshot

    def _replace_working_hours(self, vals_list):
        """Replace local working hours with the ones received from FINA."""
        self.ensure_one()
        self._get_all_working_hours().unlink()
        if vals_list:
            self.env['l10n_hr.business.working.hours'].create(
                [dict(vals, business_premise_id=self.id) for vals in vals_list])

    # ------------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------------
    def button_l10n_hr_test_fiscal_echo(self):
        self.company_id.button_l10n_hr_test_fiscal_echo(self)

    def _run_fiscal_operation(self, operation):
        """Create and immediately execute a fiscal operation for every premise."""
        operations = self.env['l10n_hr.fiscal.operation'].create(
            [{'business_premise_id': premise.id, 'operation': operation} for premise in self])
        for op in operations:
            op._execute()
        return operations

    def action_get_working_hours(self):
        return self._run_fiscal_operation('get')._action_result()

    def action_register_working_hours(self):
        return self._run_fiscal_operation('register')._action_result()

    def action_remove_working_hours(self):
        return self._run_fiscal_operation('remove')._action_result()

    def action_new_fiscal_operation(self):
        """Open a draft operation covering the selected premise(s): the user picks
        get/register/remove and executes it. Several premises are fanned out into
        one operation each."""
        context = {}
        if len(self) == 1:
            context['default_business_premise_id'] = self.id
            context['default_business_premise_ids'] = self.ids
        else:
            context['default_business_premise_ids'] = self.ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Working Hours Fiscalization'),
            'res_model': 'l10n_hr.fiscal.operation',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def action_open_fiscal_operations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fiscal Operations'),
            'res_model': 'l10n_hr.fiscal.operation',
            'view_mode': 'list,form',
            'domain': [('business_premise_id', '=', self.id), ('state', '!=', 'draft')],
            'context': {'default_business_premise_id': self.id},
        }
