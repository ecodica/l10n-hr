# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrPayrollAccountingScheme(models.Model):
    _name = "hr.payroll.accounting.scheme"
    _description = "Shema knjiženja plaće"
    _rec_name = "type_name"
    
    rule_id = fields.Many2one('hr.salary.rule', 'Pravilo', required=True)
    type_id = fields.Many2one('hr.payroll.accounting.scheme.type', 'Vrsta', required=True)
    type_name = fields.Char(related='type_id.name')
    
    use_analytic_distribution = fields.Boolean('Koristi analitičku raspodjelu', default=False,
        help="Ako je opcija uključena, stavke temeljnice se razdijele prema analitičkoj raspodjeli na zaposleniku. U suprotnom nema analitičke raspodjele.")
    account_debit = fields.Many2one(
        'account.account', 'Debitni račun', domain=[('deprecated', '=', False)],
        help="Ako je unesen konto, na njega se knjiži ukupni iznos svih stavki ovog pravila s dugovne strane.\n"\
        "Može se kombinirati s opcijama grupiranja.")
    account_credit = fields.Many2one(
        'account.account', 'Kreditni račun', domain=[('deprecated', '=', False)],
        help="Ako je unesen konto, na njega se knjiži ukupni iznos svih stavki ovog pravila s potražne strane.\n"\
        "Može se kombinirati s opcijama grupiranja.")

    department_account_ids = fields.One2many(
        'hr.payroll.accounting.by.department', 'scheme_id', 'Konta po odjelima',
        help="Ukupni iznos stavki ovog pravila se raspodijeli po kontima za odjele kako je ovdje upisano.\n"\
        "Ako nema postavki za neki odjel, taj iznos se neće proknjižiti.\n"\
        "Opcija funkcionira samo ako su isključene opcije grupiranja.")
    group_by_department = fields.Boolean(
        'Grupiraj po odjelu', help="Sav iznos se knjiži na isti dugovni / potražni konto, ali se kreira po jedna stavka temeljnice za svaki odjel.")
    group_by_municipality = fields.Boolean(
        'Grupiraj po gradu', help="Sav iznos se knjiži na isti dugovni / potražni konto, ali se kreira po jedna stavka temeljnice za svaki grad / općinu.")
    group_by_employee = fields.Boolean(
        'Grupiraj po zaposleniku', help="Sav iznos se knjiži na isti dugovni / potražni konto, ali se kreira po jedna stavka temeljnice za svakog zaposlenika.")
    group_debit = fields.Boolean('Grupiraj dugovno', help="Opcija funkcionira samo ako je unesen dugovni konto. Ukupni iznos je grupiran s iznosima drugih pravila s istim kontom.")
    group_credit = fields.Boolean('Grupiraj potražno', help="Opcija funkcionira samo ako je unesen potražni konto. Ukupni iznos je grupiran s iznosima drugih pravila s istim kontom.")

    @api.constrains('rule_id', 'type_id')
    def _check_scheme_type(self):
        """
        Each rule can only have one scheme per type.
        """
        for scheme in self:
            domain = [
                ('rule_id', '=', scheme.rule_id.id),
                ('type_id', '=', scheme.type_id.id),
                ('id', '!=', scheme.id),
            ]
            if self.search(domain):
                raise ValidationError(_('Pravilo može imati samo po jednu shemu svake vrste! Pravilo: {0}, Vrsta sheme: {1}'.format(scheme.rule_id.code, scheme.type_id.name)))
