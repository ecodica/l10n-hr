"""Shared Croatian test setup for modules built on l10n_hr_account_base.

Posting a Croatian out_invoice or out_refund needs an active business premise and
fiscal device on the sale journal: the device codes are part of the invoice number.
"""
from odoo import Command

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


def setup_hr_fiscal_device(env, company, journals=None, premise_code="PP1", device_code=1):
    """Give the journals (default: the company's sale journals) an active premise and device.

    Returns the device; its premise is ``device.l10n_hr_business_premise_id``.
    """
    if journals is None:
        journals = env["account.journal"].search([
            *env["account.journal"]._check_company_domain(company),
            ("type", "=", "sale"),
        ])
    sequence = env["ir.sequence"].create({
        "name": "HR test fiscal sequence %s" % premise_code,
        "code": "l10n_hr.fiscal",
        "padding": 4,
        "company_id": company.id,
    })
    premise = env["l10n_hr.business.premise"].create({
        "l10n_hr_name": "Test premise %s" % premise_code,
        "l10n_hr_fiscal_code": premise_code,
        "l10n_hr_invoice_sequence_by": "P",
        "l10n_hr_state": "active",
        "l10n_hr_sequence_id": sequence.id,
        "company_id": company.id,
    })
    device = env["l10n_hr.fiscal.device"].create({
        "l10n_hr_name": "Test device %s" % device_code,
        "l10n_hr_business_premise_id": premise.id,
        "l10n_hr_fiscal_device_code": device_code,
        "l10n_hr_state": "active",
        "l10n_hr_journal_ids": [Command.set(journals.ids)],
    })
    journals.l10n_hr_business_premise_id = premise
    return device


class L10nHrAccountTestCommon(AccountTestInvoicingCommon):
    """A Croatian test company with a fiscal device, plus an EU company on demand.

    The chart defaults to ``generic_coa`` so the class works without l10n_hr; a module
    that depends on l10n_hr sets ``chart_template = "hr"``. With the generic chart, use
    untaxed invoices: its taxes do not belong to the Croatian fiscal country.
    """

    country_code = "HR"
    chart_template = "generic_coa"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_company = cls.company_data["company"]
        cls.hr_company.account_fiscal_country_id = cls.env.ref("base.hr")
        cls.fiscal_device = setup_hr_fiscal_device(
            cls.env, cls.hr_company, journals=cls.company_data["default_journal_sale"])
        cls.premise = cls.fiscal_device.l10n_hr_business_premise_id

    @classmethod
    def setup_eu_company(cls, country_code="SI", **kwargs):
        """A company in another EU country, on its own chart when that is installed."""
        country = cls.env.ref("base.%s" % country_code.lower())
        template = cls.env["account.chart.template"]._guess_chart_template(country)
        if cls.env["ir.module.module"]._get(
                cls.env["account.chart.template"]._get_chart_template_mapping()[template]["module"]).state != "installed":
            template = "generic_coa"
        chart_template, cls.chart_template = cls.chart_template, template
        try:
            data = cls.setup_other_company(
                name="EU company %s" % country_code,
                country_id=country.id,
                currency_id=country.currency_id.id,
                **kwargs)
        finally:
            cls.chart_template = chart_template
        data["company"].account_fiscal_country_id = country
        return data
