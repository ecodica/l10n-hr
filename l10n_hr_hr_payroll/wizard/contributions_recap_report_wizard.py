# -*- coding: utf-8 -*-
##############################################################################

##############################################################################
from odoo import fields, models, api, _
from datetime import date

class ContributionsRecapReportWizard(models.TransientModel):

    _name = 'contributions.recap.report.wizard'
    _description = 'Forma za ispis rekapitulacije podataka za postupak kontrole'
    
    year_id = fields.Many2one('account.fiscal.year', 'Godina', help="Ispisuje se broj zaposlenika i osnovica za doprinose za mirovinsko osiguranje za svaki obračun u odabranoj godini.")
    report_date = fields.Date('Datum izvješća')

    @api.model
    def default_get(self, fields):
        "Set current year and today's date as default."
        today = date.today()
        year = self.env['account.fiscal.year'].search([('date_from', '<=', today), ('date_to', '>=', today)], limit=1)
        return {
            'year_id': year.id,
            'report_date': today,
        }

    def print_report(self):
        form = self.browse(self.id)
        data = {
            'year_id': form.year_id.id,
            'report_date': form.report_date,
        }
        return self.env.ref('l10n_hr_hr_payroll.contributions_recap_report').report_action(self, data)
