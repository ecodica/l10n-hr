from odoo import fields, models


class FiskalProstor(models.Model):
    _inherit = "l10n.hr.fiskal.prostor"

    def button_l10n_hr_fiskal_echo(self):
        self.company_id.button_test_echo(self)


class FiskalUredjaj(models.Model):
    _inherit = "l10n.hr.fiskal.uredjaj"

    fiskalisation_active = fields.Boolean()

    def button_l10n_hr_fiskal_echo(self):
        self.prostor_id.company_id.button_test_echo(self)
