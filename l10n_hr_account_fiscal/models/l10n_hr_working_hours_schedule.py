from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .l10n_hr_business_working_hours import DAYS_OF_WEEK

MAX_SCHEDULE_DAYS = 366


class L10nHrWorkingHoursSchedule(models.Model):
    """Persistent snapshot of the effective working hours schedule for one or
    more business premises over a date range.

    Each record is a point-in-time snapshot. Snapshots created from a fiscal
    operation are linked to it so the history of working hours changes can be
    reviewed and audited.
    """

    _name = "l10n_hr.working.hours.schedule"
    _description = "L10n HR working hours schedule snapshot"
    _order = "compute_date DESC, id DESC"
    _check_company_auto = True

    name = fields.Char(string="Reference", compute="_compute_name")
    compute_date = fields.Datetime(
        string="Computed On",
        default=lambda self: fields.Datetime.now(),
        required=True,
        readonly=True,
    )
    date_from = fields.Date(string="From", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="To", required=True, default=fields.Date.context_today)
    business_premise_ids = fields.Many2many(
        comodel_name="l10n_hr.business.premise",
        string="Business Premises",
        check_company=True,
        help="Leave empty to cover every business premise of the current company.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
    )
    fiscal_operation_id = fields.Many2one(
        comodel_name="l10n_hr.fiscal.operation",
        string="Fiscal Operation",
        readonly=True,
        check_company=True,
        index=True,
        help="The operation that produced this snapshot (empty for manual computations).",
    )
    line_ids = fields.One2many(
        comodel_name="l10n_hr.working.hours.schedule.line",
        inverse_name="schedule_id",
        string="Schedule",
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        default_operation = self.default_get(['fiscal_operation_id']).get('fiscal_operation_id')
        if not self.env.su and any(vals.get('fiscal_operation_id', default_operation) for vals in vals_list):
            raise UserError(_('Fiscal audit snapshots can only be created by an operation.'))
        return super().create(vals_list)

    def _check_snapshot_editable(self):
        self.check_access('write')
        if not self.env.su and self.fiscal_operation_id:
            raise UserError(_('Fiscal audit snapshots are history and cannot be modified.'))

    def write(self, vals):
        self._check_snapshot_editable()
        if not self.env.su and vals.get('fiscal_operation_id'):
            raise UserError(_('Fiscal audit snapshots can only be created by an operation.'))
        return super().write(vals)

    def unlink(self):
        self._check_snapshot_editable()
        return super().unlink()

    @api.constrains('company_id', 'business_premise_ids')
    def _check_premise_access(self):
        self.business_premise_ids.check_access('read')

    @api.depends("compute_date", "date_from", "date_to")
    def _compute_name(self):
        for schedule in self:
            schedule.name = "{} / {} - {}".format(
                fields.Datetime.to_string(schedule.compute_date) or "",
                schedule.date_from or "",
                schedule.date_to or "",
            )

    @api.onchange("date_from")
    def _onchange_date_from(self):
        if self.date_from and (not self.date_to or self.date_to < self.date_from):
            self.date_to = self.date_from

    def _premises(self):
        self.ensure_one()
        if self.business_premise_ids:
            return self.business_premise_ids
        return self.env["l10n_hr.business.premise"].search(
            [("company_id", "=", self.company_id.id)]
        )

    def action_compute(self):
        """(Re)build the schedule lines for the selected range and premises."""
        self.ensure_one()
        self._check_snapshot_editable()
        if self.date_to < self.date_from:
            raise UserError(_("The end date cannot be before the start date."))
        if (self.date_to - self.date_from).days > MAX_SCHEDULE_DAYS:
            raise UserError(_("The schedule range is limited to one year at a time."))
        self.line_ids.unlink()
        self.env["l10n_hr.working.hours.schedule.line"].create(self._collect_lines())
        return True

    def _collect_lines(self):
        self.ensure_one()
        vals_list = []
        for premise in self._premises():
            day = self.date_from
            while day <= self.date_to:
                hours = premise.get_working_hours_for_date(day)
                if hours:
                    for line in hours:
                        vals_list.append({
                            "schedule_id": self.id,
                            "business_premise_id": premise.id,
                            "date": day,
                            "shift_type": line.type,
                            "split_shift": line.split_shift,
                            "time_from": line.time_from,
                            "time_to": line.time_to,
                            "source_id": line.id,
                        })
                else:
                    vals_list.append({
                        "schedule_id": self.id,
                        "business_premise_id": premise.id,
                        "date": day,
                        "closed": True,
                    })
                day += timedelta(days=1)
        return vals_list

    def action_open(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Working Hours Schedule"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }


class L10nHrWorkingHoursScheduleLine(models.Model):
    _name = "l10n_hr.working.hours.schedule.line"
    _description = "L10n HR working hours schedule line"
    _order = "business_premise_id, date, split_shift, time_from"

    schedule_id = fields.Many2one(
        comodel_name="l10n_hr.working.hours.schedule",
        string="Schedule",
        required=True,
        ondelete="cascade",
    )
    business_premise_id = fields.Many2one(
        comodel_name="l10n_hr.business.premise",
        string="Business Premise",
        required=True,
    )
    date = fields.Date(string="Date", required=True)
    dow = fields.Selection(DAYS_OF_WEEK, string="Day of Week", compute="_compute_dow", store=True)
    shift_type = fields.Selection(
        selection=[("regular", "Regular"), ("exception", "Exception")],
        string="Type",
    )
    split_shift = fields.Selection(
        selection=[("1", "First shift"), ("2", "Second shift")],
        string="Shift",
    )
    time_from = fields.Char(string="From")
    time_to = fields.Char(string="To")
    closed = fields.Boolean(string="Closed")
    source_id = fields.Many2one(
        comodel_name="l10n_hr.business.working.hours",
        string="Working Hours",
    )

    @api.model_create_multi
    def create(self, vals_list):
        schedules = self.env['l10n_hr.working.hours.schedule'].browse([
            vals.get('schedule_id') or self.env.context.get('default_schedule_id')
            for vals in vals_list
            if vals.get('schedule_id') or self.env.context.get('default_schedule_id')
        ])
        schedules._check_snapshot_editable()
        return super().create(vals_list)

    def write(self, vals):
        schedules = self.schedule_id
        if vals.get('schedule_id'):
            schedules |= self.env['l10n_hr.working.hours.schedule'].browse(vals['schedule_id'])
        schedules._check_snapshot_editable()
        return super().write(vals)

    def unlink(self):
        self.schedule_id._check_snapshot_editable()
        return super().unlink()

    @api.constrains('schedule_id', 'business_premise_id', 'source_id')
    def _check_premise_company(self):
        for line in self:
            line.business_premise_id.check_access('read')
            line.source_id.check_access('read')
            if line.business_premise_id.company_id != line.schedule_id.company_id:
                raise UserError(_('Schedule entries must belong to the schedule company.'))
            if line.source_id and line.source_id.business_premise_id != line.business_premise_id:
                raise UserError(_('Schedule entries must reference working hours of their own premise.'))

    @api.depends("date")
    def _compute_dow(self):
        for line in self:
            line.dow = line.date and str(line.date.isoweekday()) or False
