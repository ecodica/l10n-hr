# -*- coding: utf-8 -*-
# Copyright 2023 Ecodica
{
    "name": """JOPPD obrazac""",
    "summary": """joppd obrazac osnova""",
    "category": "Croatia",
    "images": [],
    "version": "16.0.1.0.1",
    "application": False,

    'author': "Ecodica",
    'website': "https://www.ecodica.eu",
    "support": "support@ecodica.eu",
    "licence": "AGPL-3",

    "depends": [
        "l10n_hr_base",
        "l10n_hr_joppd_base",
        "base_address_extended",  # Zbog adrese i kucnog broja!
        # "partner_fiskal_responsible",
        "partner_firstname",
        "date_range",
        "report_xlsx",
    ],
    "external_dependencies": {
        "python": [],
        "bin": []
    },
    "data": [
        "security/joppd_security.xml",
        "security/ir.model.access.csv",
        "views/joppd_views.xml",
        "views/joppd_menuitems.xml",
        # "data/partner_fiskal_tags.xml",
        "report/joppd_obrazac_xlsx.xml",
    ],
    "qweb": [],
    "demo": [],

    "post_load": None,
    "pre_init_hook": None,
    "post_init_hook": None,

    "auto_install": False,
    "installable": True,
}
