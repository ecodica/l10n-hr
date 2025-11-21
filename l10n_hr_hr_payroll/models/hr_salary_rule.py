# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class HrPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure"
    
    b61 = fields.Many2one('l10n.hr.joppd.sifre','6.1. Oznaka stjecatelja/ osiguranika', required=False, domain=[('code_type','=','P-2')])

class HrSalaryRuleCategory(models.Model):
    _inherit = 'hr.salary.rule.category'

    skip_hours = fields.Boolean('Ne računaj sate', help="Ako je označeno, sati na ovom atributu neće biti dodani ukupnim satima, umjesto toga ti će sati biti dodani/oduzeti vrijednosti radnih sati redovnog radnog vremena.")
    

class HrSalaryRule(models.Model):
    _inherit="hr.salary.rule"

    def _search_ip1_form_positions(self, operator, value):
        if value != False:
            return super()._search_ip1_form_positions(operator, value)
        # handling predefined filters on salary rule view
        all_rules = self.search([])
        ip1_positions_rules = self.env['ip1.form.report.position'].search([]).mapped('rule_ids')
        rule_ids = []
        if operator == '!=':
            rule_ids = ip1_positions_rules.ids
        elif operator == '=':
            rule_ids = (all_rules - ip1_positions_rules).ids
        return [('id', 'in', rule_ids)]
        
    bank_account_number = fields.Char('Broj uplatnog računa', size=32)
    broj_modela = fields.Char( "Model",size=4)                
    poziv_na_broj = fields.Char( "Poziv na broj", size=35)
    joppd_b61 = fields.Many2one('l10n.hr.joppd.sifre','6.1. Oznaka stjecatelja/ osiguranika', domain=[('code_type','=','P-2')])
    joppd_b62 = fields.Many2one('l10n.hr.joppd.sifre','6.2. Oznaka primitka/ obveze doprinosa', domain=[('code_type','=','P-3')])
    joppd_b151 = fields.Many2one('l10n.hr.joppd.sifre','15.1. Oznaka neopor. primitka', domain=[('code_type','=','P-4')])
    joppd_b161 = fields.Many2one('l10n.hr.joppd.sifre','16.1. Oznaka načina isplate', domain=[('code_type','=','P-5')])
    crediting = fields.Boolean('Knjiži', compute='_compute_crediting_settings', store=True,
        help="Govori da li postoje postavke knjiženja za pravilo. Uglavnom se koristi za filtriranje.")
    scheme_ids = fields.One2many('hr.payroll.accounting.scheme', 'rule_id', 'Sheme knjiženja')
    # tried to add the direct counterpart m2m relation,
    # but then there are problems with the foreign key in the m2m table
    # because hr.payslip.line inherits hr.salary.rule
    ip1_position_ids = fields.Many2many('ip1.form.report.position', string='Pozicije IP1 obrasca',
        compute='_compute_ip1_form_positions', search='_search_ip1_form_positions')
    ip1_form_coef = fields.Float('Koeficijent složenosti posla', default=1.00, help='Koeficijent koji će se ispisati u koloni Elementi obračuna u obrascu')
    is_for_contributions_base_deduction = fields.Boolean(
        'Primitak za koji se umanjuje osnovica za doprinose',
        help='Ako je opcija uključena, primitak ulazi u sumu za umanjenje osnovice.'\
'Zakonsko pravilo kaže da svi primici koji se smatraju plaćom ulaze u sumu za umanjenje osnovice.'
    )

    def _compute_ip1_form_positions(self):
        ip1_positions = self.env['ip1.form.report.position'].search([])
        for rule in self:
            rule.ip1_position_ids = ip1_positions.filtered(lambda p: rule in p.rule_ids)

    @api.depends('scheme_ids')
    def _compute_crediting_settings(self):
        for rule in self:
            rule.crediting = False if not rule.scheme_ids else True

    def _satisfy_condition(self, localdict):
        exists = False
        input_or_days = False
            
        if 'worked_days.' in self.condition_python:
            input_or_days = True                        
            exists = self.code in localdict['worked_days'].dict                                                
            #print localdict['worked_days'].dict
            
        if not exists and 'inputs.' in self.condition_python:
            input_or_days = True
            exists = self.code in localdict['inputs'].dict
            #print localdict['inputs'].dict
        
        if input_or_days and not exists:
            return False
                
        return super(HrSalaryRule, self)._satisfy_condition(localdict)

    @api.depends('code', 'name')
    def _compute_display_name(self):
        "Override to show code on taxless payments tree view."
        res = super(HrSalaryRule, self)._compute_display_name()
        if self.env.context.get('show_code', False):
            for rule in self:
                rule.display_name = rule.code + ' - ' + rule.name
        return super(HrSalaryRule, self)._compute_display_name()

    def set_defaults_on_install(self):
        salary_rule_codes = self.env['hr.payroll.salary.rule.configuration'].get_rules('umanjenje_osnovice_za_doprinose')
        
        rules_with_deduction = self.search([('code', 'in', salary_rule_codes)])
        rules_with_deduction.write({'is_for_contributions_base_deduction': True})
        return True
