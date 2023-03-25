{
    "name": """JOPPD Croatia - Accounting setup""",
    "summary": """JOPPD Croatia - Accounting setup""",
    "category": "Croatia",
    "images": [],
    "version": "16.0.1.0.1",
    "application": False,
    "author": "Ecodica d.o.o",
    "website": "https:www.ecodica.eu",
    "support": "",
    "license": "AGPL-3",
    "depends": ["l10n_hr_joppd_base", "account"],
    "external_dependencies": [],
    "data": [
        "security/ir.model.access.csv",
        "views/account_account_view.xml",
        "views/account_move_view.xml",
        "views/l10n_hr_joppd_account_move_entry_view.xml",
        "views/joppd_menu_view.xml",
        "wizard/account_move_post_joppd_view.xml",
    ],
    "qweb": [],
    "demo": [],
    "auto_install": False,
    "installable": True,
}
