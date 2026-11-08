"""Real transaction snapshots must conflict before a stale fiscal dispatch."""
from uuid import uuid4

from psycopg2.errors import SerializationFailure

from odoo import SUPERUSER_ID, api, sql_db
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFiscalConcurrency(TransactionCase):

    def test_premise_revision_rejects_a_stale_repeatable_read_snapshot(self):
        # Separate real connections are essential: test savepoints on one cursor
        # cannot reproduce PostgreSQL MVCC. Commit only this unique fixture, and
        # always remove it through a separate cleanup transaction.
        database = sql_db.db_connect(self.env.cr.dbname)
        premise_id = None
        try:
            with database.cursor() as seed:
                env = api.Environment(seed, SUPERUSER_ID, {})
                premise = env['l10n_hr.business.premise'].create({
                    'l10n_hr_name': 'Concurrency fixture',
                    'l10n_hr_fiscal_code': 'MVCC' + uuid4().hex[:12],
                    'company_id': self.env.company.id,
                })
                premise_id = premise.id

            with database.cursor() as stale:
                stale.execute('SHOW transaction_isolation')
                self.assertEqual(stale.fetchone()[0], 'repeatable read')
                stale.execute(
                    'SELECT fiscal_execution_revision FROM l10n_hr_business_premise WHERE id = %s',
                    [premise_id],
                )
                self.assertEqual(stale.fetchone()[0], 0)
                with database.cursor() as writer:
                    env = api.Environment(writer, SUPERUSER_ID, {})
                    env['l10n_hr.business.premise'].browse(premise_id)._lock_fiscal_execution()
                # The first request committed an updated row version. A stale
                # request cannot acquire the lock and miss its new uncertainty.
                stale_env = api.Environment(stale, SUPERUSER_ID, {})
                with self.assertRaises(SerializationFailure):
                    stale_env['l10n_hr.business.premise'].browse(premise_id)._lock_fiscal_execution()
                stale.rollback()
        finally:
            if premise_id:
                with database.cursor() as cleanup:
                    env = api.Environment(cleanup, SUPERUSER_ID, {})
                    env['l10n_hr.business.premise'].browse(premise_id).exists().unlink()
