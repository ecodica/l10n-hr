import json
import datetime
from dateutil import relativedelta
from datetime import date
from lxml import etree
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from . import internship_calculator


class Contract(models.Model):
    _inherit = 'hr.contract'

    contract_no = fields.Char(string="Contract Number", tracking=True)
    sequence_generated = fields.Boolean(related='company_id.is_contract_sequence', readonly=True)

    job_description = fields.Text(tracking=True)
    area = fields.Many2one("hr.contract.area.type", string="Contract Area", required=True)
    area_type = fields.Many2one(
        "hr.contract.subarea.type", string="Contract Area Type", required=True, domain="[('area_type_id', '=', area)]")
    attach_data = fields.Binary(string='Attachment file')
    attach_filename = fields.Char(string='Attachment filename', size=128)

    termination_reason = fields.Many2one("hr.contract.interruption.reason.type", string="Contract Termination Reason")
    trial_date_start = fields.Date('Start of Trial Period', help="Start date of trial period.")
    internship_date_start = fields.Date('Start of Internship')
    internship_date_end = fields.Date('End of Internship')

    contract_type = fields.Selection([
        ('contract', 'Contract'),
        ('annex', 'Annex')
    ], 'Contract type', required=True, default='contract', copy=True, tracking=True)
    parent_id = fields.Many2one('hr.contract', 'Parent contract')
    child_ids = fields.One2many('hr.contract', 'parent_id', 'Annexes')

    employee_id = fields.Many2one(required=True)
    date_end_with_annexes = fields.Date('End date including annexes', compute='_get_end_date_with_annexes', store=True,
                                            help='Contract end date is max end date including all annexes.')

    internship_type = fields.Selection([
            ('0', '0 - None'),
            ('1', '1 - 12/14'),
            ('2', '2 - 12/15'),
            ('3', '3 - 12/16'),
            ('4', '4 - 12/18'),
        ], string='Internship With Increased Duration', required=True, default='0')

    old_state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('pending', 'To Renew'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], default='draft')

    notice_period = fields.Integer('Notice period', default=0, tracking=True)
    notice_date = fields.Date('Date of giving the notice', tracking=True)
    used_annual_leave_days = fields.Float('Used days of annual leave')
    annual_leave_days_used = fields.Float('Annual leave days used')
    annual_leave_days_to_pay = fields.Float('Annual leave days to pay')

    hr_config_hr_contract_wage_visible = fields.Boolean(related='company_id.hr_config_hr_contract_wage_visible', readonly=True)
    structure_type_id = fields.Many2one(string="Structure Type", help="Used for automatically setting 'Working Schedule' field. Each structure can be edited so it is connected to different working schedules.")

    @api.onchange('notice_period', 'notice_date')
    def _onchange_notice_data(self):
        if self.notice_period and self.notice_date:
            self.termination_date = self.notice_date + datetime.timedelta(days=self.notice_period)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """
        Duplicating a contract creates a new one with date_start:
            1. one day after date_end (with annexes) if latest contract has end date
            2. today if latest contract has no end date and is running
            3. one day after date_start if latest contract has no end date and hasn't started yet
        Duplication is always possible and warnings only appear after editing.
        """
        default = default or {}
        emp_id = self.employee_id.id
        domain = ['|', ('active', '=', True), ('active', '=', False), ('employee_id','=',emp_id)]
        contract_ids = self.search(domain, order = 'date_start desc')
        contract = contract_ids[0]
        latest_contract_start_date = contract.date_start
        latest_contract_end_date = contract.date_end_with_annexes
        if not latest_contract_end_date:
            if latest_contract_start_date >= date.today():
                date_start = latest_contract_start_date + relativedelta.relativedelta(days=+1)
            else:
                date_start = date.today()
        else:
            date_start = latest_contract_end_date + relativedelta.relativedelta(days=+1)
        default.update({
            'date_start': date_start,
            'date_end': False,
        })
        return super().copy(default)

    @api.depends('date_end','child_ids')
    def _get_end_date_with_annexes(self):
        for con in self:
            date_list = [con.date_end] + [ann.date_end for ann in con.child_ids]
            con.date_end_with_annexes = False if False in date_list else max(date_list)

    @api.constrains('date_start', 'date_end_with_annexes')
    def _check_dates_for_employee_contracts(self):
        for contract in self:
            if contract.contract_type != 'contract':
                continue
            # 1. employee has a contract without end_date which started before this one
            domain = [
                '|', ('active', '=', True), ('active', '=', False), ('contract_type', '=', 'contract'),
                ('employee_id', '=', contract.employee_id.id), ('id', '<>', contract.id),
                ('date_start', '<=', contract.date_start), ('date_end_with_annexes', '=', False)
            ]
            contract_ids = self.search(domain)
            if len (contract_ids) > 0:
                c = contract_ids[0]
                msg = _(u'Contract for employee {0} is not valid. Employee has a running contract without end date: {1}, {2}.')
                raise ValidationError(msg.format(contract.employee_id.name, c.name, c.date_start))

            # 2. employee has a contract with same start_date
            domain = [
                '|', ('active', '=', True), ('active', '=', False), ('contract_type', '=', 'contract'),
                ('employee_id', '=', contract.employee_id.id), ('id', '<>', contract.id),
                ('date_start', '=', contract.date_start)
            ]
            contract_ids = self.search(domain)
            if len(contract_ids) > 0:
                c = contract_ids[0]
                msg = _(u'Contract for employee {0} is not valid. Employee already has a contract with same start date ({1}) on contract {2}.')
                raise ValidationError(msg.format(contract.employee_id.name, contract.date_start, c.name,))

            # 3. employee has a contract starting before and ending after date_start
            domain = [
                '|', ('active', '=', True), ('active', '=', False), ('contract_type', '=', 'contract'),
                ('employee_id', '=', contract.employee_id.id), ('id', '<>', contract.id),
                ('date_start', '<=', contract.date_start), ('date_end_with_annexes', '>=', contract.date_start)
            ]
            contract_ids = self.search(domain)
            if len (contract_ids) > 0:
                c = contract_ids[0]
                msg = _(u'Contract for employee {0} is not valid. Employee already has a contract starting before and ending after selected start date ({1}) on contract {2}.')
                raise ValidationError(msg.format(contract.employee_id.name, contract.date_start, c.name,))

            # 4. employee has contract starting after this one while this one has no end date
            if not contract.date_end_with_annexes:
                domain = [
                    '|', ('active', '=', True), ('active', '=', False), ('contract_type', '=', 'contract'),
                    ('employee_id', '=', contract.employee_id.id), ('id', '<>', contract.id),
                    ('date_start', '>=', contract.date_start)
                ]
                contract_ids = self.search(domain)
                if len (contract_ids) > 0:
                    c = contract_ids[0]
                    msg =  _(u'Contract for employee {0} is not valid. Contract without end date cannot be created because employee already has a contract starting after selected start date ({1}) on contract {2}.')
                    raise ValidationError(msg.format(contract.employee_id.name, contract.date_start, c.name,))

            # 5. employee has a contract starting before this one ends and ending after it
            if contract.date_end_with_annexes:
                domain = [
                    '|', ('active', '=', True), ('active', '=', False), ('contract_type', '=', 'contract'),
                    ('employee_id', '=', contract.employee_id.id), ('id', '<>', contract.id),
                    ('date_start', '<=', contract.date_end_with_annexes),
                    '|', ('date_end_with_annexes', '>=', contract.date_start), ('date_end_with_annexes', '=', False),
                ]
                contract_ids = self.search(domain)
                if len(contract_ids) > 0:
                    c = contract_ids[0]
                    msg = _(u'Contract for employee {0} is not valid. Employee already has a contract starting before selected end date ({1}) and ending after selected start date ({2}) on contract {3}.')
                    raise ValidationError(msg.format(contract.employee_id.name, contract.date_end, contract.date_start, c.name,))
        return True

    @api.constrains('date_start', 'contract_type')
    def _check_annex_start_date(self):
        for contract in self:
            if contract.contract_type == 'annex' and contract.date_start < contract.parent_id.date_start:
                msg = _(u'Contract for employee {0} is not valid. Annex can not start before parent contract does: {1}, {2}.')
                raise ValidationError(msg.format(contract.employee_id.name, contract.parent_id.name, contract.parent_id.date_start))
        return True

    @api.onchange('contract_type')
    def onchange_contract_type(self):
        self.parent_id = False

    @api.onchange('area')
    def remove_area_type(self):
        self.area_type = False

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            try:
                company = self.env['res.company'].browse(values['company_id'])
            except (KeyError, NameError):
                company = self.env.user.company_id

            is_sequence = company.is_contract_sequence
            if is_sequence:  # must be sequence
                next_no = self.env['ir.sequence'].with_context(force_company=company.id).next_by_code('hr.contract')
                if not next_no:
                    raise ValidationError(_("Must create 'hr.contract' seqeunce for %s, to be able to create new Contracts") % company.name)
                values['contract_no'] = next_no

        return super().create(vals_list)

    @api.constrains('trial_date_start', 'trial_date_end')
    def _check_trial_period(self):
        # Validate max trial period
        max_trial = self.env['ir.config_parameter'].sudo().get_param('hr_pay.hr_contract_probation_period_months')
        if (self.trial_date_start and self.trial_date_end and
                self.trial_date_end > fields.Date.add(self.trial_date_start, months=int(max_trial))):
            raise ValidationError(_("Trial period can be max %s months") % max_trial)

    @api.constrains('trial_date_start', 'trial_date_end')
    def _check_trial_dates(self):
        if self.filtered(lambda c: c.trial_date_end and c.trial_date_start and
                                   c.trial_date_start > c.trial_date_end):
            raise ValidationError(_('Trial start date must be earlier than end date.'))

    @api.constrains('internship_date_start', 'internship_date_end')
    def _check_internship_period(self):
        # Validate max internship period
        max_internship = self.env['ir.config_parameter'].sudo().get_param('hr_pay.hr_contract_trainee_period_months')
        if (self.internship_date_start and self.internship_date_end and
                self.internship_date_end > fields.Date.add(self.internship_date_start, months=int(max_internship))):
            raise ValidationError(_("Internship period can be max %s months") % max_internship)

    @api.constrains('internship_date_start', 'internship_date_end')
    def _check_intership_dates(self):
        if self.filtered(lambda c: c.internship_date_end and c.internship_date_start and
                                   c.internship_date_start > c.internship_date_end):
            raise ValidationError(_('Internship start date must be earlier than end date.'))

    @api.constrains('employee_id', 'area_type', 'date_start', 'date_end', 'state')
    def _check_used_for_internship(self):
        if self.state in ('draft', 'cancel') or \
                not self.area_type.used_in_internship_calculation:
            return

        contracts = self.env['hr.contract'].search([['employee_id', '=', self.employee_id.id],
                                                    ['state', 'not in', ['draft', 'cancel']],
                                                    ['id', '!=', self.id]])

        if internship_calculator.check_contracts_for_internship(contracts, self.date_start, self.date_end):
            raise ValidationError(_('You have multiple contracts in the same range for work experience calculation.'))

    @api.constrains('state', 'active')
    def _check_archive_status(self):
        if not self.active and self.state not in ('close', 'cancel'):
            raise ValidationError(_('Only Expired and Cancelled contracts can be archived.'))

    def write(self, vals):
        for record in self:
            if vals.get('state'):
                vals['old_state'] = vals.get('state')
        return super().write(vals)

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        doc = etree.XML(res['arch'])
        if view_type == 'form':
            for node in doc.xpath("//sheet//field"):
                attrs = json.loads(node.get('modifiers'))
                if 'readonly' in attrs and type(attrs['readonly']) is list:
                    attrs['readonly'].insert(0,('state', 'in', ('open', 'close', 'cancel')))
                    attrs['readonly'].insert(0,'|')
                elif 'readonly' not in attrs:
                    attrs.update({'readonly': [('state', 'in', ('open', 'close', 'cancel'))]})
                node.set('modifiers', json.dumps(attrs))
            res['arch'] = etree.tostring(doc)
        return res


# Adding translate option
class ContractType(models.Model):
    _inherit = 'hr.contract.type'
    name = fields.Char(string='Contract Type', required=True, translate=True)
    company_id = fields.Many2one("res.company", string="Company id", store=True, readonly=True, required=True,
                                 default=lambda self: self.env.user.company_id.id)


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"
    name = fields.Char(required=True, translate=True)
