# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ClassName(models.AbstractModel):
    _name = 'report.module_name.report_template_id'
    # if module name has CAPS, omit module_name and add report to models/ir_actions_report.py
    _description = 'Report description'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        doc_ids = self.env.context['active_ids']
        doc_model = self.env.context['active_model']
        docs = self.env[doc_model].browse(doc_ids)
        report_data = {'name': 'name'}
        return {
            'doc_ids': doc_ids,
            'doc_model': doc_model,
            'docs': docs,
            'data': report_data,
        }
