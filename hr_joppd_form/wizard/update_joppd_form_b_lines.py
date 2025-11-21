# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _


class UpdateJoppdFormBLines(models.TransientModel):
    """
    Class added to handle duplicate case where we want to copy B side lines and only change period (b101 and b102).
    """
    _name = 'update.joppd.form.b.lines'
    _description = 'Update JOPPD form B lines'

    def _default_date_from(self):
        """
        Set default period as current month.
        Wizard should be used at the time of reporting the JOPPD form.
        Since it is supposed to be used for taxless reciepts -> period = month od payment.
        """
        return (fields.Date.context_today(self)).replace(day=1)
    
    def _default_date_to(self):
        return (fields.Date.context_today(self) + relativedelta(months=+1)).replace(day=1) + relativedelta(days=-1)

    date_from = fields.Date('Od datuma', required=True, default=_default_date_from)
    date_to = fields.Date('Do datuma', required=True, default=_default_date_to)

    def action_update_joppd_form(self):
        joppd_form_ids = self._context.get('active_ids')
        joppd_forms = self.env['hr.joppd.form'].browse(joppd_form_ids)
        joppd_forms.mapped('stranaB_ids').write({'b101': self.date_from, 'b102': self.date_to})
        return True