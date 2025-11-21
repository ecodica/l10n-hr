# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class JoppdFormAReport(models.AbstractModel):
    _name = 'report.hr_joppd_form.joppd_form_a'
    _description = 'JOPPD A report'

    @api.model
    def _get_report_values(self, docids, data=None):
        obj_name = 'hr.joppd.form'
        doc_obj = self.env[obj_name]
        docs = doc_obj.browse(docids)
        data = {}
        for doc in docs:
            doc_data = {}
            for line in doc.stranaA_ids:
                if line.position.code == 'V.1': doc_data.update({'a51': line.val if line.val else 0})
                if line.position.code == 'V.1.1': doc_data.update({'a511': line.val if line.val else 0})
                if line.position.code == 'V.1.2': doc_data.update({'a512': line.val if line.val else 0})
                if line.position.code == 'V.2': doc_data.update({'a52': line.val if line.val else 0})
                if line.position.code == 'V.3': doc_data.update({'a53': line.val if line.val else 0})
                if line.position.code == 'V.4': doc_data.update({'a54': line.val if line.val else 0})
                if line.position.code == 'V.5': doc_data.update({'a55': line.val if line.val else 0})
                if line.position.code == 'V.6': doc_data.update({'a56': line.val if line.val else 0})
                if line.position.code == 'VI.1.1': doc_data.update({'a611': line.val if line.val else 0})
                if line.position.code == 'VI.1.2': doc_data.update({'a612': line.val if line.val else 0})
                if line.position.code == 'VI.1.3': doc_data.update({'a613': line.val if line.val else 0})
                if line.position.code == 'VI.1.4': doc_data.update({'a614': line.val if line.val else 0})
                if line.position.code == 'VI.1.5': doc_data.update({'a615': line.val if line.val else 0})
                if line.position.code == 'VI.1.6': doc_data.update({'a616': line.val if line.val else 0})
                if line.position.code == 'VI.1.7': doc_data.update({'a617': line.val if line.val else 0})
                if line.position.code == 'VI.2.1': doc_data.update({'a621': line.val if line.val else 0})
                if line.position.code == 'VI.2.2': doc_data.update({'a622': line.val if line.val else 0})
                if line.position.code == 'VI.2.3': doc_data.update({'a623': line.val if line.val else 0})
                if line.position.code == 'VI.2.4': doc_data.update({'a624': line.val if line.val else 0})
                if line.position.code == 'VI.2.5': doc_data.update({'a625': line.val if line.val else 0})
                if line.position.code == 'VI.2.6': doc_data.update({'a626': line.val if line.val else 0})
                if line.position.code == 'VI.3.1': doc_data.update({'a631': line.val if line.val else 0})
                if line.position.code == 'VI.3.2': doc_data.update({'a632': line.val if line.val else 0})
                if line.position.code == 'VI.3.3': doc_data.update({'a633': line.val if line.val else 0})
                if line.position.code == 'VI.3.4': doc_data.update({'a634': line.val if line.val else 0})
                if line.position.code == 'VI.3.5': doc_data.update({'a635': line.val if line.val else 0})
                if line.position.code == 'VI.3.6': doc_data.update({'a636': line.val if line.val else 0})
                if line.position.code == 'VI.3.7': doc_data.update({'a637': line.val if line.val else 0})
                if line.position.code == 'VI.3.8': doc_data.update({'a638': line.val if line.val else 0})
                if line.position.code == 'VI.3.9': doc_data.update({'a639': line.val if line.val else 0})
                if line.position.code == 'VI.3.10': doc_data.update({'a6310': line.val if line.val else 0})
                if line.position.code == 'VI.3.11': doc_data.update({'a6311': line.val if line.val else 0})
                if line.position.code == 'VI.3.12': doc_data.update({'a6312': line.val if line.val else 0})
                if line.position.code == 'VI.4.1': doc_data.update({'a641': line.val if line.val else 0})
                if line.position.code == 'VI.4.2': doc_data.update({'a642': line.val if line.val else 0})
                if line.position.code == 'VI.4.3': doc_data.update({'a643': line.val if line.val else 0})
                if line.position.code == 'VI.4.4': doc_data.update({'a644': line.val if line.val else 0})
                if line.position.code == 'VII': doc_data.update({'a7': line.val if line.val else 0})
                if line.position.code == 'VIII': doc_data.update({'a8': line.val if line.val else 0})
                if line.position.code == 'IX': doc_data.update({'a9': line.val if line.val else 0})
                if line.position.code == 'X.1': doc_data.update({'a101': line.val if line.val else 0})
                if line.position.code == 'X.2': doc_data.update({'a102': line.val if line.val else 0})
            data.update({doc.id: doc_data})
        return {
            'doc_ids': docids,
            'doc_model': obj_name,
            'docs': docs,
            'data': data,
            'prec': self.env['decimal.precision'].precision_get('Payroll')
        }
    