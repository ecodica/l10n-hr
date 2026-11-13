import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .l10n_hr_business_working_hours import DAYS_OF_WEEK

TIME_RE = re.compile(r"^([0-1]\d|2[0-3]):([0-5]\d)$")


class L10nHrFiscalOperationLine(models.Model):
    """One line of a fiscal operation: either a working hours entry to register
    at FINA or an existing entry to remove.

    The line is the source of truth for the pending change. When the operation
    succeeds, register lines are converted into real
    ``l10n_hr.business.working.hours`` records and remove lines delete the
    referenced records.
    """

    _name = "l10n_hr.fiscal.operation.line"
    _description = "Fiscal operation working hours line"
    _order = "operation_id, action, sequence, id"

    sequence = fields.Integer(default=10)
    operation_id = fields.Many2one(
        comodel_name="l10n_hr.fiscal.operation",
        string="Fiscal Operation",
        required=True,
        ondelete="cascade",
    )
    action = fields.Selection(
        selection=[("register", "Register"), ("remove", "Remove")],
        string="Action",
        required=True,
    )

    # -- remove: reference to an existing working hours line ------------------
    # For register, this is optional: if set, the existing line is sent to FINA
    # without creating a duplicate; if not set, a new line is created from the
    # values below.
    working_hours_id = fields.Many2one(
        comodel_name="l10n_hr.business.working.hours",
        string="Working Hours",
        ondelete="set null",
        help="Existing working hours line to register at or remove from FINA.",
    )

    # -- register: values for a new working hours line ------------------------
    # Not DB-required: a register line that references an existing
    # working_hours_id copies the times from it, so the times are only
    # mandatory for a brand-new line (checked below).
    type = fields.Selection(
        selection=[("regular", "Regular"), ("exception", "Exception")],
        string="Type",
        required=True,
        default="regular",
    )
    description = fields.Char(string="Description")
    dow = fields.Selection(DAYS_OF_WEEK, string="Day of Week", default="1")
    valid_from = fields.Date(string="Valid from")
    valid_on = fields.Date(string="Valid on")
    time_from = fields.Char(string="Time from")
    time_to = fields.Char(string="Time to")
    split_shift = fields.Selection(
        [("1", "First shift"), ("2", "Second shift")],
        string="Split shift",
    )

    @api.model
    def _check_draft_operations(self, operations):
        operations.check_access('write')
        if any(op.state != 'draft' for op in operations):
            raise UserError(_('Executed fiscal operation lines are history and cannot be modified.'))

    @api.model_create_multi
    def create(self, vals_list):
        operations = self.env['l10n_hr.fiscal.operation'].browse([
            vals.get('operation_id') or self.env.context.get('default_operation_id')
            for vals in vals_list
            if vals.get('operation_id') or self.env.context.get('default_operation_id')
        ])
        self._check_draft_operations(operations)
        return super().create(vals_list)

    def write(self, vals):
        operations = self.operation_id
        if vals.get('operation_id'):
            operations |= self.env['l10n_hr.fiscal.operation'].browse(vals['operation_id'])
        self._check_draft_operations(operations)
        return super().write(vals)

    def unlink(self):
        self._check_draft_operations(self.operation_id)
        return super().unlink()

    @api.constrains('operation_id', 'working_hours_id')
    def _check_reference_access(self):
        self._check_draft_operations(self.operation_id)
        self.working_hours_id.check_access('read')
        for operation in self.operation_id:
            premises = operation.business_premise_id | operation.business_premise_ids
            if premises:
                operation._check_working_hours_scope(premises)

    @api.constrains("action", "working_hours_id")
    def _check_remove_has_working_hours(self):
        for line in self.filtered(lambda l: l.action == "remove"):
            if not line.working_hours_id:
                raise ValidationError(_(
                    "Remove lines must reference an existing working hours entry."
                ))

    @api.constrains("action", "type", "valid_from", "valid_on", "working_hours_id")
    def _check_register_has_data(self):
        for line in self.filtered(lambda l: l.action == "register"):
            if line.working_hours_id:
                continue
            if line.type == "regular" and not line.valid_from:
                raise ValidationError(_(
                    "Regular working hours to register must have a Valid From date."
                ))
            if line.type == "exception" and not line.valid_on:
                raise ValidationError(_(
                    "Exception working hours to register must have a Valid On date."
                ))
            if not line.time_from or not line.time_to:
                raise ValidationError(_(
                    "Working hours to register must have a Time from and a Time to."
                ))

    @api.constrains("time_from", "time_to")
    def _check_times(self):
        for line in self.filtered(lambda l: l.action != "remove"):
            for field, value in [("time_from", line.time_from), ("time_to", line.time_to)]:
                if value and not TIME_RE.match(value):
                    raise ValidationError(_(
                        "%(field)s must be in HH:MM format (24-hour), got %(value)s.",
                        field=field,
                        value=value,
                    ))
            if line.time_from and line.time_to and line.time_from >= line.time_to:
                raise ValidationError(_(
                    "End time must be after start time (%s >= %s).",
                    line.time_from,
                    line.time_to,
                ))

    def _to_working_hours_vals(self, premise_id):
        """Convert a register line into vals for ``l10n_hr.business.working.hours``."""
        self.ensure_one()
        if self.working_hours_id:
            return {
                "business_premise_id": premise_id,
                "type": self.working_hours_id.type,
                "description": self.working_hours_id.description,
                "dow": self.working_hours_id.dow,
                "valid_from": self.working_hours_id.valid_from,
                "valid_on": self.working_hours_id.valid_on,
                "time_from": self.working_hours_id.time_from,
                "time_to": self.working_hours_id.time_to,
                "split_shift": self.working_hours_id.split_shift,
            }
        return {
            "business_premise_id": premise_id,
            "type": self.type,
            "description": self.description,
            "dow": self.dow,
            "valid_from": self.valid_from,
            "valid_on": self.valid_on,
            "time_from": self.time_from,
            "time_to": self.time_to,
            "split_shift": self.split_shift,
        }
