from odoo import models
from odoo.tools.misc import str2bool


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super(IrHttp, self).session_info()
        res['skip_distribute_delta_amount_smoothly'] = str2bool(self.env['ir.config_parameter'].sudo().get_param('skip_distribute_delta_amount_smoothly'))
        return res
