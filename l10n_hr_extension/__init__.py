# -*- coding: utf-8 -*-

from . import models


def init_settings(env):
    for company in env['res.company'].search([('partner_id.country_id.code', '=', 'HR')]):
        res_config_settings = env['res.config.settings'].create({
            'company_id': company.id,
            'tax_calculation_rounding_method': 'round_globally',
            'tax_exigibility': True,
            'chart_template': 'hr',
        })
        # We need to call execute, otherwise the "implied_group" in fields are not processed.
        res_config_settings.execute()


def pre_init_hook(env):
    init_settings(env)
