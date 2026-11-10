#  Copyright 2025 Ecodica d.o.o
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """16.0 -> 18.0: the module, its models and its fields were renamed from
    the 'fiskal' spelling to 'fiscal'.

    Renames are idempotent: openupgradelib skips a rename when the new name
    already exists, so re-running this script is safe.

    Value-shaped changes (not expressible as ``rename_fields``) are handled by
    the accompanying ``post-migration.py``:
      * ``l10n.hr.fiskal.certificate`` rows -> ``certificate.certificate`` +
        ``certificate.key``, and ``res.company.l10n_hr_fiskal_cert_id`` ->
        ``l10n_hr_fiscal_cert_ids``.
      * ``l10n_hr_fiscal_log.invoice_id`` (direct Many2one) -> polymorphic
        ``res_model`` + ``res_id``.
      * ``l10n_hr_fiskal_taxative`` (Boolean) -> ``l10n_hr_tax_model`` selection.
      * ``l10n_hr_fiscal_time`` values reformatted to 'dd.mm.yyyyThh:mm:ss'.
    """
    # Module rename (must run before the field/model renames below resolve).
    openupgrade.update_module_names(
        env.cr,
        [("l10n_hr_account_fiskal", "l10n_hr_account_fiscal")],
    )
    # Model renames (rename_models also renames the backing tables).
    openupgrade.rename_models(env.cr, [
        ("l10n.hr.fiskal.log", "l10n_hr.fiscal.log"),
        ("l10n.hr.fiskal.prostor", "l10n_hr.business.premise"),
        ("l10n.hr.fiskal.uredjaj", "l10n_hr.fiscal.device"),
    ])
    # Field renames: (model, table, old name, new name).
    openupgrade.rename_fields(env, [
        # account.move
        ("account.move", "account_move", "l10n_hr_fiskal_user_id", "l10n_hr_fiscal_user_id"),
        ("account.move", "account_move", "l10n_hr_fiskal_uredjaj_id", "l10n_hr_fiscal_device_id"),
        ("account.move", "account_move", "l10n_hr_fiskalni_broj", "l10n_hr_fiscal_number"),
        ("account.move", "account_move", "l10n_hr_fiskal_qr", "l10n_hr_fiscal_qr"),
        ("account.move", "account_move", "l10n_hr_fiskal_log_ids", "l10n_hr_fiscal_log_ids"),
        ("account.move", "account_move", "l10n_hr_nacin_placanja", "l10n_hr_payment_method"),
        # account.journal
        ("account.journal", "account_journal", "l10n_hr_default_nacin_placanja", "l10n_hr_default_fiscal_payment_method"),
        ("account.journal", "account_journal", "l10n_hr_prostor_id", "l10n_hr_business_premise_id"),
        ("account.journal", "account_journal", "l10n_hr_fiskal_uredjaj_ids", "l10n_hr_fiscal_device_ids"),
        # account.tax
        ("account.tax", "account_tax", "l10n_hr_fiskal_type", "l10n_hr_fiscal_type"),
        # res.company
        ("res.company", "res_company", "l10n_hr_fiskal_spec", "l10n_hr_fiscal_spec"),
        ("res.company", "res_company", "l10n_hr_fiskal_prostor_ids", "l10n_hr_business_premise_ids"),
        ("res.company", "res_company", "l10n_hr_fiskal_separator", "l10n_hr_fiscal_separator"),
        ("res.company", "res_company", "l10n_hr_fiskal_invoice_sequences", "l10n_hr_fiscal_invoice_sequence_ids"),
        # l10n_hr.fiscal.log (table renamed by rename_models above; columns renamed here)
        ("l10n_hr.fiscal.log", "l10n_hr_fiscal_log", "fiskal_prostor_id", "business_premise_id"),
        ("l10n_hr.fiscal.log", "l10n_hr_fiscal_log", "fiskal_uredjaj_id", "fiscal_device_id"),
        ("l10n_hr.fiscal.log", "l10n_hr_fiscal_log", "sadrzaj", "content"),
        ("l10n_hr.fiscal.log", "l10n_hr_fiscal_log", "odgovor", "reply_msg"),
        ("l10n_hr.fiscal.log", "l10n_hr_fiscal_log", "greska", "error_msg"),
        ("l10n_hr.fiscal.log", "l10n_hr_fiscal_log", "time_stamp", "reply_timestamp"),
        ("l10n_hr.fiscal.log", "l10n_hr_fiscal_log", "time_obr", "process_time"),
    ])
