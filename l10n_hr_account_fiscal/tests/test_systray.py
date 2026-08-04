"""
Browser test for the not-fiscalized-invoices systray.

The systray warns that an invoice has a ZKI but never received a JIR - it was
signed and sent, but the Tax Administration's answer never landed, so it is not
fiscalized and somebody has to retry it. Nothing else in the UI surfaces that
state, which makes a silently broken badge worse than no badge.

What is covered:

Rendering    The toggler renders with its counter badge, and the badge shows the
             number of stuck invoices. This needs a real web client: an OWL
             lifecycle guard that never passes, or a Dropdown slot name Odoo no
             longer recognises, both leave a component that raises nothing and
             simply shows no badge - a Python test on the endpoint would still
             pass.

Menu         Clicking the toggler opens the dropdown and its item, rather than
             acting as the item itself.

The endpoint behind the counter is covered separately by
``test_fiscal_tax_values.test_counter_is_scoped_to_the_enabled_companies``.
"""
from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install", "l10n_hr", "l10n_hr_account_fiscal")
class TestNotFiscalizedSystray(HttpCase):

    def _create_stuck_invoice(self):
        """A posted invoice with a ZKI and no JIR - what the badge counts."""
        tax = self.env["account.tax"].create({
            "name": "PDV 25% (systray test)",
            "amount_type": "percent",
            "amount": 25.0,
            "type_tax_use": "sale",
            "l10n_hr_fiscal_type": "Pdv",
            "company_id": self.env.company.id,
        })
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.env["res.partner"].create({"name": "Systray test"}).id,
            "invoice_date": "2026-08-03",
            "date": "2026-08-03",
            "invoice_line_ids": [
                Command.create({
                    "name": "systray test line",
                    "quantity": 1.0,
                    "price_unit": 1000.0,
                    "tax_ids": [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        invoice.l10n_hr_zki = "0" * 32
        self.assertFalse(invoice.l10n_hr_jir)
        return invoice

    def test_systray_badge_renders_and_menu_opens(self):
        self._create_stuck_invoice()
        self.env.flush_all()

        # The component polls every 5 minutes but also fetches once on start,
        # so the badge must be there without waiting for an interval.
        self.browser_js(
            "/odoo",
            """
            (async function () {
                function sleep(ms) {
                    return new Promise((resolve) => setTimeout(resolve, ms));
                }
                async function waitFor(selector, label) {
                    for (let i = 0; i < 100; i++) {
                        const el = document.querySelector(selector);
                        if (el) {
                            return el;
                        }
                        await sleep(100);
                    }
                    throw new Error("timed out waiting for " + label +
                                    " (" + selector + ")");
                }

                // The toggler (icon + red badge) must render at all.
                const icon = await waitFor(
                    "#open_not_fiscalized_invoices", "systray icon");
                const badge = icon.parentElement.querySelector(".badge");
                if (!badge) {
                    throw new Error("no counter badge next to the systray icon");
                }
                if (badge.textContent.trim() !== "1") {
                    throw new Error("badge shows '" + badge.textContent.trim() +
                                    "', expected '1'");
                }

                // The default slot is the toggler, the menu is in `content`, so
                // clicking must open a menu rather than act as the item itself.
                icon.click();
                const item = await waitFor(
                    ".o-dropdown--menu .o-mail-NotificationItem-name",
                    "dropdown menu item");
                if (!item.textContent.includes("Not Fiscalized Invoices")) {
                    throw new Error("unexpected menu item: " + item.textContent);
                }

                console.log("test successful");
            })();
            """,
            "odoo.isReady === true",
            login="admin",
            timeout=120,
        )
