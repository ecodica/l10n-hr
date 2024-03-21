# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Croatia - PAIN Credit Transfer",
    "summary": "Generate ISO 20022 credit transfer (SEPA and not SEPA)",
    "version": "16.0.2.0.0",
    "category": "Accounting/Localizations/SEPA",
    "author": "Ecodica",
    "license": "AGPL-3",
    "website": "https://www.ecodica.eu",
    "depends": [
        "l10n_hr_pain_base",
        "account_banking_sepa_credit_transfer",
    ],
    "data": [
        'data/account_payment_method.xml',
    ],
    "installable": True,
}
