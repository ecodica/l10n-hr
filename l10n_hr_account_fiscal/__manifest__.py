{
    "name": "Croatia - Fiscalization 1.0",
    "summary": "Croatia ",
    "category": "Croatia",
    "images": [],
    "version": "19.0.2.5.2",
    "application": False,
    "author": "Daj mi 5, Ecodica, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-croatia",
    "support": "",
    "license": "AGPL-3",
    "depends": [
        "l10n_hr_account_base",
        "certificate",
        "hr",
    ],
    # signxml is pinned by the environment: cryptography==42.0.8 (an Odoo core
    # requirement) allows at most signxml==3.2.2
    "external_dependencies": {"python": ["zeep", "signxml"], "bin": []},
    "data": [
        "security/fiscal_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "wizard/l10n_hr_change_fiscal_data_views.xml",
        "views/l10n_hr_fiscal_operation_views.xml",
        "views/l10n_hr_working_hours_schedule_views.xml",
        "views/l10n_hr_business_working_hours_views.xml",
        "views/l10n_hr_pnp_category_views.xml",
        "views/product_template_views.xml",
        "views/certificate_certificate_views.xml",
        "views/res_company_views.xml",
        "views/account_tax_views.xml",
        "views/l10n_hr_business_premise_views.xml",
        "views/l10n_hr_fiscal_device_views.xml",
        "views/l10n_hr_fiscal_log_views.xml",
        "views/account_move_views.xml",
        "views/fiscal_menu_views.xml",
        "report/report_invoice.xml",

    ],
    "assets": {
        "web.assets_backend": [
            "l10n_hr_account_fiscal/static/src/js/not_fiscalized_invoices_systray.js",
            "l10n_hr_account_fiscal/static/src/xml/not_fiscalized_invoices_systray.xml",
        ]
    },
    "qweb": [],
    "demo": [],
    "auto_install": False,
    "installable": True,
}
