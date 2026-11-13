"""Odoo's core l10n_hr_edi must not be installed next to the Croatian localization.

It defines the same models (l10n.hr.tax.category) and company fields (MER credentials)
with different meanings; l10n_hr_base declares it in ``excludes``.
"""
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestL10nHrEdiExclusion(TransactionCase):

    def test_installing_core_l10n_hr_edi_is_refused(self):
        module = self.env["ir.module.module"]._get("l10n_hr_edi")
        if not module:
            self.skipTest("l10n_hr_edi is not in the addons path")
        self.assertIn("l10n_hr_edi", self.env["ir.module.module"]._get("l10n_hr_base").exclusion_ids.mapped("name"))
        with self.assertRaises(UserError) as cm:
            module.with_context(lang="en_US").button_install()
        self.assertIn("are incompatible", str(cm.exception))
        self.assertEqual(module.state, "uninstalled")
