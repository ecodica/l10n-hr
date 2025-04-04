{
    "name": "Croatia - OPZ-STAT report",
    "description": """
Croatian localisation.
======================
OPZ-STAT Invoice report
""",
    "version": "16.0.1.0.0",
    "license": "LGPL-3",
    "author": "Ecodica",
    "category": "Localization",
    "website": "",
    "depends": [
        "l10n_hr_account_base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_account_views.xml",
        "views/res_partner_views.xml",
        "views/opz_stat_views.xml",
        "views/opz_stat_line_views.xml",
    ],
    "demo": [],
    "test": [],
    "active": False,
    "installable": True,
}
