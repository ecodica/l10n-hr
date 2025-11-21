# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class HrPayrollStructure(models.Model):
    """
    Salary structure used to defined
    - Basic
    - Allowances
    - Deductions
    """
    _name = 'hr.payroll.structure'
    _description = 'Salary Structure'

    @api.model
    def _get_parent(self):
        return self.env.ref('l10n_hr_payroll_base.structure_base', False)

    name = fields.Char(required=True,string="Naziv")
    code = fields.Char(string='Reference', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
        copy=False, default=lambda self: self.env.company)
    note = fields.Text(string='Opis')
    parent_id = fields.Many2one('hr.payroll.structure', string='Parent', default=_get_parent)
    children_ids = fields.One2many('hr.payroll.structure', 'parent_id', string='Children', copy=True)
    rule_ids = fields.Many2many('hr.salary.rule', 'hr_structure_salary_rule_rel', 'struct_id', 'rule_id', string='Salary Rules')

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create a recursive salary structure.'))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, code=_("%s (copy)") % (self.code))
        return super(HrPayrollStructure, self).copy(default)

    def get_all_rules(self):
        """
        @return: returns a list of tuple (id, sequence) of rules that are maybe to apply
        """
        all_rules = []
        for struct in self:
            all_rules += struct.rule_ids._recursive_search_of_rules()
        return all_rules

    def _get_parent_structure(self):
        parent = self.mapped('parent_id')
        if parent:
            parent = parent._get_parent_structure()
        return parent + self


class HrContributionRegister(models.Model):
    _name = 'hr.contribution.register'
    _description = 'Registar doprinosa'

    company_id = fields.Many2one('res.company', string='Tvrtka',
        default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Partner')
    name = fields.Char(required=True,string="Naziv")
    register_line_ids = fields.One2many('hr.payslip.line', 'register_id',
        string='Register Line', readonly=True)
    note = fields.Text(string='Opis')


class HrSalaryRuleCategory(models.Model):
    _name = 'hr.salary.rule.category'
    _description = 'Kategorije pravila obračuna'

    name = fields.Char(required=True, translate=True,string="Naziv")
    code = fields.Char(required=True)
    parent_id = fields.Many2one('hr.salary.rule.category', string='Parent',
        help="Linking a salary category to its parent is used only for the reporting purpose.")
    children_ids = fields.One2many('hr.salary.rule.category', 'parent_id', string='Children')
    note = fields.Text(string='Opis')
    company_id = fields.Many2one('res.company', string='Tvrtka',
        default=lambda self: self.env.company)


class HrSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _order = 'sequence, id'
    _description = 'Pravilo obračuna plaće'

    name = fields.Char(required=True,string="Naziv")
    code = fields.Char(required=True,
        help="The code of salary rules can be used as reference in computation of other rules. "
             "In that case, it is case sensitive.",string="Šifra")
    sequence = fields.Integer(required=True, index=True, default=5,
        help='Use to arrange calculation sequence',string ="Sekvenca")
    quantity = fields.Char(default='1.0',
        help="It is used in computation for percentage and fixed amount. "
             "For e.g. A rule for Meal Voucher having fixed amount of "
             u"1€ per worked day can have its quantity defined in expression "
             "like worked_days.WORK100.number_of_days.",string="Količina")
    category_id = fields.Many2one('hr.salary.rule.category', string='Kategorija', required=True)
    active = fields.Boolean(default=True,
        help="If the active field is set to false, it will allow you to hide the salary rule without removing it.")
    appears_on_payslip = fields.Boolean(string='Vidljivo na listiću', default=True,
        help="Used to display the salary rule on payslip.")
    parent_rule_id = fields.Many2one('hr.salary.rule', string='Nadređeno pravilo obračuna', index=True)
    company_id = fields.Many2one('res.company', string='Tvrtka',
        default=lambda self: self.env.company)
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Raspon'),
        ('python', 'Python Expression')
    ], string="Uvjet baziran na", default='none', required=True)
    condition_range = fields.Char(string='Raspon baziran na', default='contract.wage',
        help='This will be used to compute the % fields values; in general it is on basic, '
             'but you can also use categories code fields in lowercase as a variable names '
             '(hra, ma, lta, etc.) and the variable basic.')
    condition_python = fields.Text(string='Python uvjet', required=True,
        default='''
                    # Available variables:
                    #----------------------
                    # payslip: object containing the payslips
                    # employee: hr.employee object
                    # contract: hr.contract object
                    # rules: object containing the rules code (previously computed)
                    # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
                    # worked_days: object containing the computed worked days
                    # inputs: object containing the computed inputs

                    # Note: returned value have to be set in the variable 'result'

                    result = rules.NET > categories.NET * 0.10''',
        help='Primjenjuj pravilo za izračunavanje ako je uvjet točan. Može se definirati uvjet kao osnovica > 1000')
    condition_range_min = fields.Float(string='Minimalni raspon', help="Minimalni iznos za ovo pravilo.")
    condition_range_max = fields.Float(string='Maksimalni raspon', help="Maksimalni iznos za ovo pravilo")
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed amount'),
        ('code', 'Python Code'),
    ], string='Vrsta iznosa', index=True, required=True, default='fix', help="The computation method for the rule amount.")
    amount_fix = fields.Float(string='Fiksni iznos', digits=('Payroll'))
    amount_percentage = fields.Float(string='Postotak (%)', digits=('Payroll Rate'),
        help='Naprimjer 50.0 za primjenu postotka od 50%')
    amount_python_compute = fields.Text(string='Python kod',
        default='''
                    # Available variables:
                    #----------------------
                    # payslip: object containing the payslips
                    # employee: hr.employee object
                    # contract: hr.contract object
                    # rules: object containing the rules code (previously computed)
                    # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
                    # worked_days: object containing the computed worked days.
                    # inputs: object containing the computed inputs.

                    # Note: returned value have to be set in the variable 'result'

                    result = contract.wage * 0.10''')
    amount_percentage_base = fields.Char(string='Postotak baziran na', help='result will be affected to a variable')
    child_ids = fields.One2many('hr.salary.rule', 'parent_rule_id', string='Podređeno pravilo', copy=True)
    register_id = fields.Many2one('hr.contribution.register', string='Registar doprinosa',
        help="Eventualna treća strana uključena u isplatu plaće djelatnika.")
    input_ids = fields.One2many('hr.rule.input', 'input_id', string='Ulazi', copy=True)
    note = fields.Text(string='Opis')

    @api.constrains('parent_rule_id')
    def _check_parent_rule_id(self):
        if not self._check_recursion(parent='parent_rule_id'):
            raise ValidationError(_('Error! You cannot create recursive hierarchy of Salary Rules.'))

    def _recursive_search_of_rules(self):
        """
        @return: returns a list of tuple (id, sequence) which are all the children of the passed rule_ids
        """
        children_rules = []
        for rule in self.filtered(lambda rule: rule.child_ids):
            children_rules += rule.child_ids._recursive_search_of_rules()
        return [(rule.id, rule.sequence) for rule in self] + children_rules

    def _compute_rule(self, localdict):
        """
        :param localdict: dictionary containing the environement in which to compute the rule
        :return: returns a tuple build as the base/amount computed, the quantity and the rate
        :rtype: (float, float, float)
        """
        self.ensure_one()
        if self.amount_select == 'fix':
            try:
                return self.amount_fix, float(safe_eval(self.quantity, localdict)), 100.0
            except:
                raise UserError(_('Wrong quantity defined for salary rule %s (%s).') % (self.name, self.code))
        elif self.amount_select == 'percentage':
            try:
                return (float(safe_eval(self.amount_percentage_base, localdict)),
                        float(safe_eval(self.quantity, localdict)),
                        self.amount_percentage)
            except:
                raise UserError(_('Wrong percentage base or quantity defined for salary rule %s (%s).') % (self.name, self.code))
        else:
            try:
                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), 'result_qty' in localdict and localdict['result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
            except:
                raise UserError(_('Wrong python code defined for salary rule %s (%s).') % (self.name, self.code))

    def _satisfy_condition(self, localdict):
        """
        @param contract_id: id of hr.contract to be tested
        @return: returns True if the given rule match the condition for the given contract. Return False otherwise.
        """
        self.ensure_one()

        if self.condition_select == 'none':
            return True
        elif self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result and result <= self.condition_range_max or False
            except:
                raise UserError(_('Wrong range condition defined for salary rule %s (%s).') % (self.name, self.code))
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except:
                raise UserError(_('Wrong python condition defined for salary rule %s (%s).') % (self.name, self.code))


class HrRuleInput(models.Model):
    _name = 'hr.rule.input'
    _description = 'Ulazni podatak pravila obračuna'

    name = fields.Char(string='Opis', required=True)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    input_id = fields.Many2one('hr.salary.rule', string='Ulazni podatak pravila obračuna', required=True)
