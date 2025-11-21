from odoo import api, fields, models, _

class HrPayrollSalaryRuleConfiguration(models.Model):
    _name = 'hr.payroll.salary.rule.configuration'
    _description = 'Konfiguracija pravila obračuna plaće'
    
    name = fields.Char('Naziv', size=128, required=True)
    description = fields.Char('Opis', size=512)
    salary_rule_ids = fields.Many2many('hr.salary.rule','salary_rule_configuration_rel','payroll_config_id','salary_rule_id','Pravila')
    
    def get_rules(self, rules):
        payroll_category = 'l10n_hr_hr_payroll.hr_payroll_configuration_' + rules
        payroll_config = self.env.ref(payroll_category)
        if payroll_config:
            code_list = payroll_config.salary_rule_ids.mapped('code')
            return tuple(code_list)
        payroll_config = self.search([('name','=',rules)],limit=1)
        if payroll_config:
            code_list = payroll_config.salary_rule_ids.mapped('code')
            return tuple(code_list)
        return False
    
class HrPayrollSalaryRuleCategoryConfiguration(models.Model):
    _name = 'hr.payroll.salary.rule.category.configuration'
    _description = 'Konfiguracija kategorije pravila obračuna plaće'
    
    name = fields.Char('Naziv', size=128, required=True)
    description = fields.Char('Opis', size=512)
    salary_rule_category_ids = fields.Many2many('hr.salary.rule.category','salary_rule_category_configuration_rel','payroll_config_id','salary_rule_category_id','Kategorije')
    
    def get_category(self, category):
        payroll_category = 'l10n_hr_hr_payroll.hr_payroll_configuration_' + category
        payroll_config = self.env.ref(payroll_category)
        if payroll_config:
            code_list = payroll_config.salary_rule_category_ids.mapped('code')
            return tuple(code_list)
        payroll_config = self.search([('name','=',category)],limit=1)
        if payroll_config:
            code_list = payroll_config.salary_rule_ids.mapped('code')
            return tuple(code_list) if len(code_list) > 1 else code_list[0]
        return False