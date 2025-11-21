from odoo import models, api, fields, _


class Ip1FormReportConfig(models.Model):
    _name = 'ip1.form.report.config'
    _description = 'Konfiguracija izvještaja IP1 obrazac'

    name = fields.Char('Naziv', required=True)
    active = fields.Boolean('Aktivan', default=True)
    position_ids = fields.One2many('ip1.form.report.position', 'config_id', 'Pozicije', context={'active_test': False})


class Ip1FormReportPosition(models.Model):
    _name = 'ip1.form.report.position'
    _description = 'Pozicija u izvještaju IP1 obrazac'
    _order = 'section, subsection, sequence'

    config_id = fields.Many2one('ip1.form.report.config', 'Konfiguracija', required=True, ondelete='restrict', context={'active_test': False})
    # using two-digit identifiers and not roman numerals to enable sorting
    section = fields.Selection([
        ('062', 'VI.2'),
        ('10', 'X'),
        ('132', 'XIII.2'),
    ], 'Sekcija', required=True)
    subsection = fields.Selection([
        ('01', '1'),
        ('02', '2'),
        ('03', '3'),
        ('04', '4'),
        ('05', '5'),
        ('06', '6'),
    ], 'Podsekcija', help='Podsekcija u kojoj se pozicija pojavljuje u izvještaju. Potrebno odabrati samo ako sekcija ima podsekcije.')
    sequence = fields.Integer('Sekvenca', required=True,
        help='Slijed unutar sekcije gdje se pozicija pojavljuje.')
    name = fields.Char('Naziv', required=True, help='Naziv pozicije koji će se ispisati u izvještaju.')
    print_always = fields.Boolean('Uvijek ispiši',
        help='Ako je ova opcija označena, pozicija će se uvijek ispisati u izvještaju. Standardno ponašanje je da se pozicija ispisuje ako joj je suma različita 0.')
    rule_ids = fields.Many2many('hr.salary.rule', 'ip1_position_salary_rule_rel',
        'position_id', 'salary_rule_id', 'Pravila plaće',
        help='Pravila plaće koja će se uračunati u sumu pozicije.', context={'active_test': False})
    active = fields.Boolean(related='config_id.active')