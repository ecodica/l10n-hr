# Copyright 2023 Ecodica
{
    "name": """Croatian Fiscal 2.0 Codebooks""",
    "summary": """Defines codebook base views and menu items for Croatian fiscal 2.0""",
    "category": "Croatia",
    "images": [],
    "version": "18.0.1.0.0",
    "application": False,
    'author': "Ecodica",
    "license": 'LGPL-3',
    'website': "https://www.ecodica.eu",
    "support": "support@ecodica.eu",
    "licence": "AGPL-3",

    "depends": [
        "accountant",
    ],
    "external_dependencies": {
        "python": [],
        "bin": []
    },
    "data": [
        "views/menu_items.xml",
        "views/account_journal_views.xml",
        "views/account_tax_views.xml",
        "views/product_template_views.xml",
        "views/product_category_views.xml",
    ],
    "qweb": [],
    "demo": [],
    "auto_install": False,
    "installable": True,
}
