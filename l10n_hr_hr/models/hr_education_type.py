from odoo.exceptions import ValidationError
from odoo import models, fields, api, _

class EducationType(models.Model):
    _name = "hr.education.type"
    _description = "Education Type"
    _rec_name = "qualification_type"

    # Razina Europskog kvalifikacijskog okvira (EKO)
    eko_level = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7','7'),
        ('8', '8')
    ], 'European Qualification Level')
    # Razina Hrvatskog kvalifikacijskog okvira (HKO)
    hko_level = fields.Selection([
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4.1', '4.1'),
            ('4.2', '4.2'),
            ('5', '5'),
            ('6', '6'),
            ('7.1', '7.1'),
            ('7.2', '7.2'),
            ('8.1', '8.1'),
            ('8.2', '8.2'),
            ], 'Croatian Qualification Level')
    # Vrste kvalifikacija (vrsta obrazovanja)
    qualification_type = fields.Char(size=256, required=True)
    # Obujam kvalifikacija
    qualification_point_type = fields.Selection([
        ('1', 'HROO'),
        ('2', 'ECVET'),
        ('3', 'ECTS')
    ], "Qualification point type")
    volume_points = fields.Integer('Qualification volume')
    # Opisnice razina ishoda ucenja
    qualification_description = fields.Text('Description of Learning outcomes')
    company_id = fields.Many2one("res.company", string="Company id", store=True, readonly=True, required=True,
                                 default=lambda self: self.env.user.company_id.id)

    @api.onchange('eko_level')
    def _onchange_eko_level(self):
        hko_levels = [('1'), ('2'), ('3'), ('4.1', '4,2'), ('5'), ('6'), ('7.1', '7.2'), ('8.1', '8.2')]
        if self.eko_level:
            if not self.env.context.get("noonchange"):
                self.env.context = self.with_context(noonchange=True).env.context
                self.hko_level = hko_levels[int(self.eko_level)-1][0]
            else:
                self.env.context = self.with_context(noonchange=False).env.context

    @api.onchange('hko_level')
    def _onchange_hko_level(self):
        if self.hko_level:
            if not self.env.context.get("noonchange"):
                self.env.context = self.with_context(noonchange=True).env.context
                self.eko_level = self.hko_level.split('.')[0]
            else:
                self.env.context = self.with_context(noonchange=False).env.context

    @api.constrains('qualification_point_type', 'volume_points')
    def point_type_constraint(self):
        if self.volume_points != 0 and not self.qualification_point_type:
            raise ValidationError(_("Must select point type!"))
