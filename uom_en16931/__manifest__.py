# Copyright 2025 Ecodica
{
    "name": """EN16931 UoM Code Book""",
    "summary": """Defines additional codebook for unit of measures based on EN16931 standard""",
    'description': """
    """,
    "category": "Sales/Sales",
    "images": [],
    "version": "18.0.2.0.0",
    "application": False,
    'author': "Ecodica",
    "license": 'LGPL-3',
    'website': "https://www.ecodica.eu",
    "support": "support@ecodica.eu",
    "licence": "LGPL-3",

    "depends": [
        "uom",
        "sale",
    ],
    "external_dependencies": {
        "python": [],
        "bin": []
    },
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Data
        "data/uom.en16931.csv",
        "data/uom_data.xml",
        # Views
        "views/uom_en16931_views.xml",
        "views/product_uom_views.xml",
        "views/menu_items.xml",
    ],
    "pre_init_hook": '_pre_init_hook',
    "post_init_hook": '_post_init_hook',
    "qweb": [],
    "demo": [],
    "auto_install": False,
    "installable": True,
}
