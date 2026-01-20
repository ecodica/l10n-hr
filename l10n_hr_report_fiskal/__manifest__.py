{
    "name": """Account Report Fiskal""",
    "summary": """
        Ensuring that the qr code and payment reference are not printed on 
        fiscalized invoices.
    """,
    "category": "Accounting",
    "images": [],
    "version": "16.0.2.0.0",
    "application": False,
    "author": "Ecodica d.o.o.",
    "license": "AGPL-3",
    "depends": [
        "l10n_hr_account_reference",
        "l10n_hr_account_fiskal",
    ],
    "data": [
        "reports/report_invoice.xml",
    ],
    "demo": [],
    "auto_install": True,
    "installable": True,
}
