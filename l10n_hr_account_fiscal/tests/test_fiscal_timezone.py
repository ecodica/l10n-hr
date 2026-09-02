"""Fiscal timestamps belong to the business premise, not to the logged-in user.

``DatVrijeme`` is signed into the ZKI and printed on the document, and the Porezna
uprava recomputes the ZKI from that printed document during an inspection. A
timestamp that moved with whoever happened to be logged in could therefore never
be reproduced - the invoice would disagree with its own protective code.

``get_l10n_hr_time_formatted()`` used to follow ``self.env.tz``. It now pins
``Europe/Zagreb``, which is what the note at the top of ``account_move.py`` said
it should have done all along.
"""
from odoo.addons.l10n_hr_base.models.res_company import FISCAL_TIMEZONE
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFiscalTimezone(TransactionCase):
    """DatVrijeme belongs to the business premise, not to the logged-in user."""

    def test_fiscal_time_ignores_the_user_timezone(self):
        """Two users in different timezones must stamp the same instant alike.

        This is what makes the ZKI reproducible: the Porezna uprava recomputes it
        from the printed document, and a timestamp that moved with the cashier's
        profile would never match.
        """
        company = self.env.company
        honolulu = company.with_context(tz="Pacific/Honolulu").get_l10n_hr_time_formatted()
        tokyo = company.with_context(tz="Asia/Tokyo").get_l10n_hr_time_formatted()
        self.assertEqual(
            honolulu["datum_vrijeme"][:11], tokyo["datum_vrijeme"][:11],
            "fiscal date still follows the user's timezone",
        )
        self.assertEqual(str(honolulu["time_stamp"].tzinfo), FISCAL_TIMEZONE)
        self.assertEqual(str(tokyo["time_stamp"].tzinfo), FISCAL_TIMEZONE)
