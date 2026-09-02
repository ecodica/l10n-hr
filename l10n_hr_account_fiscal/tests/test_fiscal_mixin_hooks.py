"""The seams that let a second model inherit the fiscalization mixin.

``l10n_hr.fiscal.v1.mixin`` had exactly one consumer, ``account.move``, and about
half of it read ``account.move`` fields directly - ``line_ids``, ``display_type``,
``amount_untaxed_signed``, ``invoice_user_id``. ``pos.order`` is about to become
the second consumer, so those bodies moved down onto ``account.move`` and the
mixin kept hooks in their place.

These tests pin the seams themselves: that a hook is *required* where no sensible
default exists, that it *defaults* where one does, and that ``account.move`` still
answers each one the way it always did. What the invoice message actually contains
is covered by ``test_fiscal_tax_values.py``, which did not change.
"""
from types import SimpleNamespace

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestFiscalMixinHooks(AccountTestInvoicingCommon):
    """The hooks the mixin exposes, and what account.move answers."""

    def test_tax_values_hook_is_required(self):
        """A model inheriting the mixin must say where its tax amounts come from.

        There is no sane default - account.move reads its 'tax' journal items,
        pos.order computes them from its lines - so the mixin refuses rather than
        silently reporting an empty breakdown, which FINA would happily accept.
        """
        mixin = self.env["l10n_hr.fiscal.v1.mixin"]
        with self.assertRaises(NotImplementedError):
            mixin._get_fisc_tax_values()

    def test_account_move_still_answers_the_tax_hook(self):
        """The body that moved out of the mixin is reachable on account.move."""
        move = self.env["account.move"]
        self.assertTrue(
            hasattr(move, "_get_fisc_tax_values"),
            "account.move lost _get_fisc_tax_values in the move-down",
        )
        self.assertNotEqual(
            type(move)._get_fisc_tax_values,
            type(self.env["l10n_hr.fiscal.v1.mixin"])._get_fisc_tax_values,
            "account.move is still using the mixin's raising stub",
        )

    def test_validate_hook_defaults_to_a_no_op(self):
        """Unlike the tax hook, validation has a safe default: do nothing.

        The checks compare the message against the document's own tax lines, which
        not every model has. A model without them is not wrong, just unchecked.
        """
        mixin = self.env["l10n_hr.fiscal.v1.mixin"]
        self.assertIsNone(mixin._validate_fiscal_invoice(SimpleNamespace()))

    def test_default_fiscal_user_prefers_the_salesperson(self):
        """OibOper identifies the person who issued the document."""
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_user_id": self.env.ref("base.user_admin").id,
        })
        self.assertEqual(
            move._l10n_hr_default_fiscal_user(),
            self.env.ref("base.user_admin").id,
        )

    def test_default_fiscal_user_falls_back_to_the_acting_user(self):
        """With no salesperson the acting user is the best available answer."""
        move = self.env["account.move"].create({
            "move_type": "entry",
            "invoice_user_id": False,
        })
        self.assertEqual(move._l10n_hr_default_fiscal_user(), self.env.user.id)

    def test_dead_date_time_helper_is_gone(self):
        """It read l10n_hr_vrijeme_izdavanja, a field that no longer exists."""
        self.assertFalse(
            hasattr(self.env["account.move"], "_prepare_fiscal_date_time"),
            "_prepare_fiscal_date_time is back; it cannot work - the field is gone",
        )
