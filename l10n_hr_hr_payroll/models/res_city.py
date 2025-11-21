from odoo import models, fields, api

class City(models.Model):
    _inherit = "res.city"

    acc_number = fields.Char('Broj računa')
    tax_rate_ids = fields.One2many('res.city.tax.rate', 'city_id', 'Porezna stopa')
    code = fields.Char(size=8, string="Šifra grada")

    @api.depends('tax_rate_ids')
    def _get_tax_rate_on_date(self, date):
        """
        Get tax pct on given date.
        Return 0 if there is no data for corresponding period.
        """
        history_obj = self.env['res.city.tax.rate']
        city_id = self.id
        tax_line = history_obj.search([('city_id', '=', city_id), ('tax_date_from', '<=', date)], order="tax_date_from desc", limit=1)
        return tax_line.lower_tax_rate or 0, tax_line.higher_tax_rate or 0

class CityTaxRate(models.Model):
    _name = 'res.city.tax.rate'
    _description = 'Tax rate for city'
    _order = 'tax_date_from DESC'
    _rec_name = 'city_id'

    city_id = fields.Many2one('res.city', 'Grad', required=True)
    lower_tax_rate = fields.Float('Niža porezna stopa',required=True)
    higher_tax_rate = fields.Float('Viša porezna stopa',required=True)
    tax_date_from = fields.Date('Vrijedi od datuma',required=True)
