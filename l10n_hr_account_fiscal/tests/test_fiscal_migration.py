"""Schedule upgrades must not invent company ownership or discard audit history."""
import importlib.util
from contextlib import contextmanager
from pathlib import Path

from odoo.tests import TransactionCase, tagged


_PATH = Path(__file__).resolve().parents[1] / "migrations/19.0.2.1.0/pre-migration.py"
_SPEC = importlib.util.spec_from_file_location("fiscal_schedule_pre_migration", _PATH)
_MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATION)

_PARENT = "l10n_hr_working_hours_schedule"
_LINE = "l10n_hr_working_hours_schedule_line"
_MODELS = ("l10n_hr.working.hours.schedule", "l10n_hr.working.hours.schedule.line")


class _RollbackFixture(Exception):
    pass


@tagged("post_install", "-at_install")
class TestFiscalMigration(TransactionCase):
    @contextmanager
    def _isolated_schema(self):
        # No public fallback: absent fixture tables cannot resolve the actual
        # module tables or ir_model. Roll back all fixtures and search_path.
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute("CREATE SCHEMA fiscal_migration_fixture")
                self.env.cr.execute("SET LOCAL search_path TO fiscal_migration_fixture, pg_catalog")
                yield
                raise _RollbackFixture()
        except _RollbackFixture:
            pass

    def _metadata(self, parent=True, line=True):
        self.env.cr.execute("CREATE TABLE ir_model (model varchar PRIMARY KEY, transient boolean)")
        for model, flag in zip(_MODELS, (parent, line)):
            if flag is not None:
                self.env.cr.execute("INSERT INTO ir_model VALUES (%s, %s)", [model, flag])

    def _migrate(self):
        _MIGRATION.migrate(self.env.cr, "19.0.2.0.0")

    def test_confirmed_transient_missing_and_partial_tables(self):
        for parent, line in ((False, False), (True, False), (False, True), (True, True)):
            with self.subTest(parent=parent, line=line), self._isolated_schema():
                self._metadata()
                for exists, name in ((parent, _PARENT), (line, _LINE)):
                    if exists:
                        self.env.cr.execute(f"CREATE TABLE {name} (id integer PRIMARY KEY)")
                        self.env.cr.execute(f"INSERT INTO {name} VALUES (1)")
                self._migrate()
                self._migrate()
                for exists, name in ((parent, _PARENT), (line, _LINE)):
                    self.env.cr.execute("SELECT to_regclass(%s)", [name])
                    self.assertEqual(bool(self.env.cr.fetchone()[0]), exists)
                    if exists:
                        self.env.cr.execute(f"SELECT id FROM {name}")
                        self.assertEqual(self.env.cr.fetchall(), [])

    def test_confirmed_legacy_cleanup_preserves_dependencies(self):
        with self._isolated_schema():
            self._metadata()
            self.env.cr.execute("""
                CREATE TABLE l10n_hr_working_hours_schedule (id integer PRIMARY KEY);
                CREATE TABLE l10n_hr_working_hours_schedule_line
                    (id integer PRIMARY KEY, schedule_id integer REFERENCES
                     l10n_hr_working_hours_schedule(id));
                CREATE TABLE premise_relation
                    (schedule_id integer REFERENCES l10n_hr_working_hours_schedule(id)
                     ON DELETE CASCADE);
                CREATE VIEW schedule_history AS
                    SELECT id FROM l10n_hr_working_hours_schedule;
                INSERT INTO l10n_hr_working_hours_schedule VALUES (1);
                INSERT INTO l10n_hr_working_hours_schedule_line VALUES (2, 1);
                INSERT INTO premise_relation VALUES (1);
            """)
            self._migrate()
            self._migrate()
            for table in (_PARENT, _LINE, "premise_relation", "schedule_history"):
                self.env.cr.execute(f"SELECT * FROM {table}")
                self.assertEqual(self.env.cr.fetchall(), [])
            self._assert_foreign_keys(_LINE, "premise_relation")

    def test_persistent_history_and_dependencies_survive(self):
        with self._isolated_schema():
            # Persistent schema wins even over stale transient metadata.
            self._metadata()
            self.env.cr.execute("""
                CREATE TABLE l10n_hr_working_hours_schedule
                    (id integer PRIMARY KEY, company_id integer, fiscal_operation_id integer);
                CREATE TABLE l10n_hr_working_hours_schedule_line
                    (id integer PRIMARY KEY, schedule_id integer REFERENCES
                     l10n_hr_working_hours_schedule(id));
                CREATE TABLE fiscal_operation
                    (id integer PRIMARY KEY, schedule_id integer REFERENCES
                     l10n_hr_working_hours_schedule(id));
                CREATE VIEW schedule_history AS
                    SELECT * FROM l10n_hr_working_hours_schedule;
                INSERT INTO l10n_hr_working_hours_schedule VALUES (1, 10, 42), (3, 20, NULL);
                INSERT INTO l10n_hr_working_hours_schedule_line VALUES (2, 1);
                INSERT INTO fiscal_operation VALUES (42, 1);
            """)
            self._migrate()
            self._migrate()
            self.env.cr.execute("SELECT * FROM schedule_history ORDER BY id")
            self.assertEqual(self.env.cr.fetchall(), [(1, 10, 42), (3, 20, None)])
            self.env.cr.execute(f"SELECT * FROM {_LINE}")
            self.assertEqual(self.env.cr.fetchall(), [(2, 1)])
            self.env.cr.execute("SELECT * FROM fiscal_operation")
            self.assertEqual(self.env.cr.fetchall(), [(42, 1)])
            self._assert_foreign_keys(_LINE, "fiscal_operation")

    def _assert_foreign_keys(self, first, second):
        self.env.cr.execute("""
            SELECT count(*) FROM pg_catalog.pg_constraint
            WHERE contype = 'f' AND conrelid IN
                (pg_catalog.to_regclass(%s), pg_catalog.to_regclass(%s))
        """, [first, second])
        self.assertEqual(self.env.cr.fetchone()[0], 2)

    def test_ambiguous_ownership_fails_before_any_delete(self):
        for flags in ((False, False), (True, False), (False, True), (None, True), (True, None), None):
            with self.subTest(metadata=flags), self._isolated_schema():
                if flags is not None:
                    self._metadata(*flags)
                for table in (_PARENT, _LINE):
                    self.env.cr.execute(f"CREATE TABLE {table} (id integer PRIMARY KEY)")
                    self.env.cr.execute(f"INSERT INTO {table} VALUES (1)")
                with self.assertRaisesRegex(RuntimeError, "ambiguous ownership"):
                    self._migrate()
                for table in (_PARENT, _LINE):
                    self.env.cr.execute(f"SELECT id FROM {table}")
                    self.assertEqual(self.env.cr.fetchall(), [(1,)])

    def test_empty_unknown_and_absent_tables_are_safe(self):
        for parent, line in ((False, False), (True, False), (False, True), (True, True)):
            with self.subTest(parent=parent, line=line), self._isolated_schema():
                # No metadata is needed when there is no data to lose/assign.
                for exists, table in ((parent, _PARENT), (line, _LINE)):
                    if exists:
                        self.env.cr.execute(f"CREATE TABLE {table} (id integer PRIMARY KEY)")
                self._migrate()
                self._migrate()

    def test_persistent_parent_without_lines_is_preserved(self):
        with self._isolated_schema():
            self.env.cr.execute(f"CREATE TABLE {_PARENT} (id integer PRIMARY KEY, company_id integer)")
            self.env.cr.execute(f"INSERT INTO {_PARENT} VALUES (1, 20)")
            self._migrate()
            self._migrate()
            self.env.cr.execute(f"SELECT * FROM {_PARENT}")
            self.assertEqual(self.env.cr.fetchall(), [(1, 20)])

    def test_persistent_rows_without_a_company_are_not_assigned_to_the_upgrade_company(self):
        with self._isolated_schema():
            self.env.cr.execute(f"CREATE TABLE {_PARENT} (id integer PRIMARY KEY, company_id integer)")
            self.env.cr.execute(f"INSERT INTO {_PARENT} VALUES (1, NULL)")
            with self.assertRaisesRegex(RuntimeError, "ambiguous ownership"):
                self._migrate()
            self.env.cr.execute(f"SELECT * FROM {_PARENT}")
            self.assertEqual(self.env.cr.fetchall(), [(1, None)])

    def test_ambiguous_partial_tables_fail_closed(self):
        for table in (_PARENT, _LINE):
            with self.subTest(table=table), self._isolated_schema():
                self.env.cr.execute(f"CREATE TABLE {table} (id integer PRIMARY KEY)")
                self.env.cr.execute(f"INSERT INTO {table} VALUES (1)")
                with self.assertRaisesRegex(RuntimeError, "ambiguous ownership"):
                    self._migrate()
                self.env.cr.execute(f"SELECT id FROM {table}")
                self.assertEqual(self.env.cr.fetchall(), [(1,)])
