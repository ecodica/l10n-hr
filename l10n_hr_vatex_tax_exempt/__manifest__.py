# Copyright 2023 Ecodica
{
    "name": """Croatian fiscal 2.0 VATEX tax exempt""",
    "summary": """Defines VATEX tax exempts for Croatian fiscal 2.0""",
    'description': """
    
        VATEX Tax Exempts
        ====================
        Implemented based on:
            * Croatian Fiscalization 2.0 instructions - https://porezna.gov.hr/fiskalizacija/bezgotovinski-racuni/fiskalizacija-bezgotovinskih-racuna
            * PEPPOL EU Instructions - https://docs.peppol.eu/poacc/billing/3.0/codelist/vatex/
    """,
    "category": "Croatia",
    "images": [],
    "version": "19.0.1.0.0",
    "application": False,
    'author': "Ecodica",
    "license": 'LGPL-3',
    'website': "https://www.ecodica.eu",
    "support": "support@ecodica.eu",
    "licence": "AGPL-3",

    "depends": [
        "l10n_hr_fiscal_codebook",
    ],
    "external_dependencies": {
        "python": [],
        "bin": []
    },
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Data
        "data/l10n.hr.vatex.tax.exempt.csv",
        # Views
        "views/l10n_hr_vatex_tax_exempt_views.xml",
        "views/account_tax_views.xml",
        "views/menu_items.xml",
    ],
    "qweb": [],
    "demo": [],
    "auto_install": False,
    "installable": True,
}
