#  Copyright 2025 Ecodica d.o.o
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def _migrate_log_invoice_to_res_ref(env):
    """``invoice_id`` (direct Many2one) -> polymorphic ``res_model``+``res_id``."""
    table = "l10n_hr_fiscal_log"
    if not openupgrade.column_exists(env.cr, table, "invoice_id"):
        return  # already migrated on a re-run, or column absent
    env.cr.execute(
        """
        UPDATE l10n_hr_fiscal_log
        SET res_model = 'account.move', res_id = invoice_id
        WHERE invoice_id IS NOT NULL
        """,
    )
    openupgrade.drop_columns(env.cr, [(table, "invoice_id")])


def _migrate_taxative_to_tax_model(env):
    """``l10n_hr_fiskal_taxative`` (Boolean) -> ``l10n_hr_tax_model`` (Selection).

    The old flag only encoded "in the VAT system" (USustPdv), so it cannot tell
    r1 (invoice basis) from r2 (payment basis) apart: in-system companies get
    the module default r1, out-of-system ones get r0 (not subject). Re-check r2
    cases by hand after the upgrade.
    """
    if not openupgrade.column_exists(env.cr, "res_company", "l10n_hr_fiskal_taxative"):
        return
    env.cr.execute(
        """
        UPDATE res_company
        SET l10n_hr_tax_model = CASE
            WHEN l10n_hr_fiskal_taxative THEN 'r1'
            ELSE 'r0'
        END
        WHERE l10n_hr_tax_model IS NULL
        """,
    )
    openupgrade.drop_columns(env.cr, [("res_company", "l10n_hr_fiskal_taxative")])


def _reformat_fiscal_time(env):
    """Old 'DD.MM.YYYY HH:MM' -> FISCAL_DATETIME_FORMAT 'DD.MM.YYYYTHH:MM:SS'.

    Idempotent: only rows still in the old space-separated, second-less layout
    are touched, so values already written by 18.x stay as they are.
    """
    env.cr.execute(
        r"""
        UPDATE account_move
        SET l10n_hr_fiscal_time = regexp_replace(
            l10n_hr_fiscal_time,
            '^(\d{2}\.\d{2}\.\d{4}) (\d{2}:\d{2})$',
            '\1T\2:00'
        )
        WHERE l10n_hr_fiscal_time ~ '^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$'
        """,
    )


def _migrate_certificates(env):
    """``l10n.hr.fiskal.certificate`` -> ``certificate.certificate``(+key).

    The old model is gone in 18.x, so its table is read with raw SQL; the new
    rows are created through the ORM so the certificate module recomputes the
    PEM/date fields and extracts the private key into a ``certificate.key``.
    """
    table = "l10n_hr_fiskal_certificate"
    if not openupgrade.table_exists(env.cr, table):
        return
    env.cr.execute(
        """
        SELECT id, company_id, cert_file, cert_file_name, cert_password,
               name, cert_type, pem_key, pem_crt, state
        FROM l10n_hr_fiskal_certificate
        """,
    )
    rows = env.cr.fetchall()
    if not rows:
        return

    Certificate = env["certificate.certificate"].sudo()
    Key = env["certificate.key"].sudo()
    id_map = {}
    for (old_id, company_id, cert_file, cert_file_name, cert_password,
         name, cert_type, pem_key, pem_crt, state) in rows:

        key_id = False
        if pem_key:
            key_id = Key.create({
                "name": (name or "fiscal") + ".key",
                "company_id": company_id,
                "content": base64.b64encode(pem_key.encode("utf-8")).decode("ascii"),
            }).id

        content = password = False
        if cert_file:
            # original P12/PFX upload; bytes() normalises memoryview -> str
            content = base64.b64encode(bytes(cert_file)).decode("ascii")
            password = cert_password or False
        elif pem_crt:
            # PEM certificate text
            content = base64.b64encode(pem_crt.encode("utf-8")).decode("ascii")

        cert = Certificate.create({
            "name": name or cert_file_name or "Fiscal certificate",
            "company_id": company_id,
            "scope": "fina",
            "l10n_hr_type": cert_type or "other",
            "active": state in ("convert", "active"),
            "content": content,
            "pkcs12_password": password,
            "private_key_id": key_id,
        })
        id_map[old_id] = cert.id

    # Relink companies: old res_company.l10n_hr_fiskal_cert_id -> m2m cert ids.
    if openupgrade.column_exists(env.cr, "res_company", "l10n_hr_fiskal_cert_id"):
        env.cr.execute(
            "SELECT id, l10n_hr_fiskal_cert_id FROM res_company "
            "WHERE l10n_hr_fiskal_cert_id IS NOT NULL",
        )
        couples = [
            (company_id, id_map[old_cert_id])
            for company_id, old_cert_id in env.cr.fetchall()
            if old_cert_id in id_map
        ]
        companies = env["res.company"].sudo().browse([c for c, _ in couples])
        for company in companies:
            new_cert_ids = [new_id for c, new_id in couples if c == company.id]
            company.write({"l10n_hr_fiscal_cert_ids": [(4, cid) for cid in new_cert_ids]})
        openupgrade.drop_columns(env.cr, [("res_company", "l10n_hr_fiskal_cert_id")])

    # NOTE: the old ``l10n_hr_fiskal_certificate`` table is left as an orphan on
    # purpose so the pre-migration data stays auditable; drop it manually once
    # the upgrade has been verified.


@openupgrade.migrate()
def migrate(env, version):
    _migrate_log_invoice_to_res_ref(env)
    _migrate_taxative_to_tax_model(env)
    _reformat_fiscal_time(env)
    _migrate_certificates(env)
