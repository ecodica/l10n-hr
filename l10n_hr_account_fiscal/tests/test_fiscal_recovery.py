"""Recovery boundaries after dispatch: retain the exchange, roll back local changes.

This fixture deliberately does not inherit TestFiscalOperation: importing its
helpers must not cause that class's test methods to run a second time.
"""
from copy import deepcopy
from unittest.mock import patch

from lxml import etree
from requests.exceptions import ReadTimeout

from odoo import Command, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..fiscal import fiscal as fiscal_module
from .test_fiscal_operation import (
    FakeFiscalization, OPERATOR_OIB, _error_response, _get_response, _ns,
    _ok_response,
)


@tagged("post_install", "-at_install")
class TestFiscalRecovery(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # These tests exercise recovery, not the manager-group access contract.
        cls.env = cls.env(user=SUPERUSER_ID)
        cls.company = cls.env.company
        cls.company.write({
            "company_registry": "12345678901",
            "l10n_hr_fiscal_silent_error_logging": False,
        })
        cls.operator = cls.env["hr.employee"].create({
            "name": "Recovery operator",
            "company_id": cls.company.id,
            "user_id": cls.env.user.id,
        })
        cls.operator.work_contact_id.company_registry = OPERATOR_OIB
        cls.premise = cls.env["l10n_hr.business.premise"].create({
            "l10n_hr_name": "Recovery premise",
            "l10n_hr_fiscal_code": "RECOVERY",
            "company_id": cls.company.id,
        })
        cls.Operation = cls.env["l10n_hr.fiscal.operation"]
        cls.WorkingHours = cls.env["l10n_hr.business.working.hours"]
        cls.Schedule = cls.env["l10n_hr.working.hours.schedule"]

    def setUp(self):
        super().setUp()
        FakeFiscalization.calls = []
        FakeFiscalization.responses = {}
        for patcher in (
            patch.object(fiscal_module, "Fiscalization", FakeFiscalization),
            patch.object(type(self.company), "get_fiscal_data", lambda company: {}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _hours(self, premise=None, **values):
        return self.WorkingHours.create({
            "business_premise_id": (premise or self.premise).id,
            "type": "regular", "dow": "1", "valid_from": "2026-01-01",
            "time_from": "08:00", "time_to": "16:00", **values,
        })

    def _register_line(self, **values):
        return {
            "action": "register", "type": "regular", "dow": "2",
            "valid_from": "2026-01-01", "time_from": "09:00",
            "time_to": "17:00", **values,
        }

    def _operation(self, operation, premise=None, lines=(), **values):
        return self.Operation.create({
            "business_premise_id": (premise or self.premise).id,
            "operation": operation,
            "line_ids": [Command.create(line) for line in lines],
            **values,
        })

    def _remote_hours(self):
        return _get_response(regular=[_ns(
            DatumOd="01.01.2026", Napomena=None,
            Jednokratno=[_ns(DanUTjednu="3", RadnoVrijemeOd="10:00", RadnoVrijemeDo="18:00")],
            Dvokratno=[], PoDogovoru=None, ParniNeparni=None,
        )])

    def _assert_unchanged(self, op, before, state="uncertain"):
        self.assertEqual(op.state, state)
        self.assertEqual(op.business_premise_id._get_working_hours_snapshot(), before)
        self.assertEqual(op.snapshot_before or [], before)
        self.assertEqual(op.snapshot_after or [], before)
        self.assertFalse(op.diff)
        self.assertEqual((op.added_count, op.removed_count, op.changed_count), (0, 0, 0))
        self.assertFalse(op.has_changes)
        self.assertTrue(op.error_msg)
        self.assertTrue(op.fiscal_log_id.exists(), "the exchange survives local rollback")
        self.assertEqual(op.fiscal_log_id.res_id, op.id)
        self.assertEqual(op.fiscal_log_id.res_model, op._name)
        self.assertTrue(op.schedule_before_id.exists())
        self.assertEqual(op.schedule_after_id, op.schedule_before_id)
        self.assertEqual(self.Schedule.search_count([("fiscal_operation_id", "=", op.id)]), 1)

    def _history(self, op):
        return deepcopy(op.read([
            "state", "operation", "execution_date", "user_id", "error_msg",
            "fiscal_log_id", "snapshot_before", "snapshot_after", "diff",
            "added_count", "removed_count", "changed_count",
            "schedule_before_id", "schedule_after_id",
        ])[0])

    def _uncertain_registration(self):
        FakeFiscalization.responses["prijaviRadnoVrijeme"] = ReadTimeout("reply lost")
        op = self._operation("register", lines=[self._register_line()])
        op.action_execute()
        self.assertEqual(op.state, "uncertain")
        return op

    def test_register_partial_create_sql_failure_rolls_back(self):
        self._hours()
        before = self.premise._get_working_hours_snapshot()
        op = self._operation("register", lines=[
            self._register_line(), self._register_line(dow="3"),
        ])
        FakeFiscalization.responses["prijaviRadnoVrijeme"] = _ok_response()
        original = type(self.WorkingHours).create
        inserted = []

        def create_then_sql_failure(records, values):
            result = original(records, values)
            if result.business_premise_id == self.premise:
                inserted.extend(result.ids)
                # A real PostgreSQL failure poisons the cursor until rollback;
                # merely raising a Python exception would not cover that boundary.
                records.env.cr.execute("SELECT 1 / 0")
            return result

        with patch.object(type(self.WorkingHours), "create", create_then_sql_failure):
            op.action_execute()

        self.assertTrue(inserted, "a local insert happened before the SQL failure")
        self.assertFalse(self.WorkingHours.browse(inserted).exists())
        self._assert_unchanged(op, before)
        self.assertEqual(len(FakeFiscalization.calls), 1)

    def test_remove_unlink_failure_restores_hours_and_line_references(self):
        hours = self._hours()
        before = self.premise._get_working_hours_snapshot()
        op = self._operation("remove", lines=[{"action": "remove", "working_hours_id": hours.id}])
        FakeFiscalization.responses["obrisiRadnoVrijeme"] = _ok_response()
        original = type(self.WorkingHours).unlink

        def unlink_then_fail(records):
            target = hours.id in records.ids
            result = original(records)
            if target:
                raise RuntimeError("unlink completion failed")
            return result

        with patch.object(type(self.WorkingHours), "unlink", unlink_then_fail):
            op.action_execute()

        self.assertTrue(hours.exists())
        self.assertEqual(op.line_ids.working_hours_id, hours)
        self._assert_unchanged(op, before)
        self.assertIn("unlink completion failed", op.error_msg)

    def test_get_replace_failure_restores_deleted_and_created_hours(self):
        hours = self._hours()
        before = self.premise._get_working_hours_snapshot()
        op = self._operation("get")
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = self._remote_hours()
        original = type(self.premise)._replace_working_hours

        def replace_then_fail(premise, values):
            result = original(premise, values)
            if premise == self.premise:
                raise RuntimeError("replace completion failed")
            return result

        with patch.object(type(self.premise), "_replace_working_hours", replace_then_fail):
            op.action_execute()

        self.assertTrue(hours.exists())
        self._assert_unchanged(op, before)

    def test_post_snapshot_failure_falls_back_without_rebuilding(self):
        self._hours()
        before = self.premise._get_working_hours_snapshot()
        op = self._operation("register", lines=[self._register_line()])
        FakeFiscalization.responses["prijaviRadnoVrijeme"] = _ok_response()
        original = type(op)._create_schedule_snapshot
        attempts = []

        def snapshot(records):
            if records == op:
                attempts.append(records.id)
                if len(attempts) > 1:
                    raise RuntimeError("post snapshot unavailable")
            return original(records)

        with patch.object(type(op), "_create_schedule_snapshot", snapshot):
            op.action_execute()

        self.assertEqual(len(attempts), 2, "fallback must reuse the original before snapshot")
        self._assert_unchanged(op, before)
        self.assertIn("post snapshot unavailable", op.error_msg)

    def test_remove_final_write_fails_once_then_retains_log_and_before_state(self):
        hours = self._hours()
        before = self.premise._get_working_hours_snapshot()
        op = self._operation("remove", lines=[{"action": "remove", "working_hours_id": hours.id}])
        FakeFiscalization.responses["obrisiRadnoVrijeme"] = _ok_response()
        original = type(op)._write_execution
        attempts = []

        def write_execution(records, values):
            if records == op:
                attempts.append(values.get("state"))
                if len(attempts) == 1:
                    # Fail after writing too: the finalization itself is atomic.
                    original(records, values)
                    raise RuntimeError("final write failed once")
            return original(records, values)

        with patch.object(type(op), "_write_execution", write_execution):
            op.action_execute()

        self.assertEqual(attempts, ["done", "uncertain"])
        self.assertTrue(hours.exists())
        self.assertEqual(op.line_ids.working_hours_id, hours)
        self._assert_unchanged(op, before)
        self.assertIn("final write failed once", op.error_msg)

    def test_timeout_retains_sent_xml_and_classifies_changes_differently_from_get(self):
        class TimeoutFiscalization(FakeFiscalization):
            def _call_service(client, service_proxy, req_kw):
                # Match HistoryPlugin after dispatch but before any response.
                client.history = _ns(last_sent={
                    "envelope": etree.fromstring(b"<Envelope><SentBeforeTimeout/></Envelope>"),
                })
                return super()._call_service(service_proxy, req_kw)

        for operation, method, state in (
            ("register", "prijaviRadnoVrijeme", "uncertain"),
            ("remove", "obrisiRadnoVrijeme", "uncertain"),
            ("get", "dohvatiRadnoVrijeme", "error"),
        ):
            with self.subTest(operation=operation):
                premise = self.env["l10n_hr.business.premise"].create({
                    "l10n_hr_name": operation, "l10n_hr_fiscal_code": "TIME" + operation.upper(),
                    "company_id": self.company.id,
                })
                hours = self._hours(premise)
                before = premise._get_working_hours_snapshot()
                lines = []
                if operation == "register":
                    lines = [self._register_line()]
                elif operation == "remove":
                    lines = [{"action": "remove", "working_hours_id": hours.id}]
                op = self._operation(operation, premise=premise, lines=lines)
                FakeFiscalization.responses[method] = ReadTimeout("response timed out")
                with patch.object(fiscal_module, "Fiscalization", TimeoutFiscalization):
                    op.action_execute()
                self._assert_unchanged(op, before, state=state)
                self.assertIn("SentBeforeTimeout", op.request_msg)
                self.assertFalse(op.response_msg, "there was no received XML")
                self.assertIn("response timed out", op.error_msg)
        self.assertEqual(len(FakeFiscalization.calls), 3)

    def test_malformed_get_does_not_treat_missing_data_as_empty(self):
        hours = self._hours()
        before = self.premise._get_working_hours_snapshot()
        for response in (_ok_response(), _ok_response(PoslovniProstor=_ns(RadnoVrijeme=None))):
            with self.subTest(response=response):
                FakeFiscalization.responses["dohvatiRadnoVrijeme"] = response
                op = self._operation("get")
                op.action_execute()
                self._assert_unchanged(op, before)
                self.assertTrue(hours.exists())

    def test_unverified_responses_never_apply_get_or_register(self):
        class UnverifiedFiscalization(FakeFiscalization):
            def _call_service(client, service_proxy, req_kw):
                response = super()._call_service(service_proxy, req_kw)
                client.fiscal_plugin.last_verification_ok = False
                return response

        self._hours()
        before = self.premise._get_working_hours_snapshot()
        # GET is safe to attempt even while an earlier change is unresolved.
        for operation, method, response, state in (
            ("register", "prijaviRadnoVrijeme", _ok_response(), "uncertain"),
            ("get", "dohvatiRadnoVrijeme", _get_response(), "error"),
        ):
            with self.subTest(operation=operation):
                FakeFiscalization.responses[method] = response
                op = self._operation(operation, lines=[self._register_line()] if operation == "register" else [])
                with patch.object(fiscal_module, "Fiscalization", UnverifiedFiscalization):
                    op.action_execute()
                self._assert_unchanged(op, before, state=state)
                self.assertIn("signature", op.error_msg.lower())

    def test_schema_110_absent_business_premise_is_a_legitimate_empty_schedule(self):
        self._hours()
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = _ok_response(PoslovniProstor=None)
        op = self._operation("get")
        op.action_execute()
        self.assertEqual(op.state, "done")
        self.assertFalse(self.premise._get_all_working_hours())
        self.assertFalse(op.snapshot_after)
        self.assertEqual(op.removed_count, 1)
        self.assertTrue(op.fiscal_log_id)

    def test_unsupported_regular_variants_refuse_to_replace_local_hours(self):
        self._hours()
        before = self.premise._get_working_hours_snapshot()
        for variant in ("PoDogovoru", "ParniNeparni"):
            with self.subTest(variant=variant):
                regular = _ns(DatumOd="01.01.2026", Jednokratno=[], Dvokratno=[], **{variant: True})
                FakeFiscalization.responses["dohvatiRadnoVrijeme"] = _get_response(regular=[regular])
                op = self._operation("get")
                op.action_execute()
                self._assert_unchanged(op, before)
                self.assertIn("not supported", op.error_msg)

    def test_batch_prepares_every_child_then_continues_after_middle_apply_failure(self):
        premises = self.premise
        for code in ("RECOVERYB", "RECOVERYC"):
            premises |= self.env["l10n_hr.business.premise"].create({
                "l10n_hr_name": code, "l10n_hr_fiscal_code": code, "company_id": self.company.id,
            })
        target = premises[1]
        launcher = self.Operation.create({
            "operation": "register", "business_premise_ids": [Command.set(premises.ids)],
            "line_ids": [Command.create(self._register_line())],
        })
        FakeFiscalization.responses["prijaviRadnoVrijeme"] = _ok_response()
        prepare = type(launcher)._prepare_execution
        apply = type(launcher)._handle_fisc_response
        call = FakeFiscalization._call_service
        prepared = []

        def prepare_all(op):
            result = prepare(op)
            prepared.append(op.business_premise_id.id)
            return result

        def dispatch(client, service_proxy, req_kw):
            self.assertEqual(set(prepared), set(premises.ids), "no dispatch before all local preparation")
            return call(client, service_proxy, req_kw)

        def apply_then_fail(op, response, msg_type):
            result = apply(op, response, msg_type)
            if op.business_premise_id == target:
                raise RuntimeError("middle child apply failed")
            return result

        with patch.object(type(launcher), "_prepare_execution", prepare_all), \
                patch.object(type(launcher), "_handle_fisc_response", apply_then_fail), \
                patch.object(FakeFiscalization, "_call_service", dispatch):
            launcher.action_execute()

        self.assertFalse(launcher.exists())
        children = self.Operation.search([("business_premise_id", "in", premises.ids)], order="id")
        self.assertEqual(children.mapped("state"), ["done", "uncertain", "done"])
        self.assertEqual(len(FakeFiscalization.calls), 3)
        self.assertEqual(len(children.fiscal_log_id), 3)
        self.assertEqual(self.env["l10n_hr.fiscal.log"].search_count([
            ("res_model", "=", self.Operation._name), ("res_id", "in", children.ids),
        ]), 3)
        for child in children:
            if child.business_premise_id == target:
                self._assert_unchanged(child, [])
            else:
                self.assertEqual(len(child.business_premise_id._get_all_working_hours()), 1)
                self.assertEqual(child.added_count, 1)

    def test_batch_preparation_failure_makes_no_external_calls(self):
        other = self.env["l10n_hr.business.premise"].create({
            "l10n_hr_name": "Preparation failure", "l10n_hr_fiscal_code": "PREPFAIL",
            "company_id": self.company.id,
        })
        launcher = self.Operation.create({
            "operation": "get", "business_premise_ids": [Command.set((self.premise | other).ids)],
        })
        original = type(launcher)._create_schedule_snapshot

        def snapshot(op):
            if op.business_premise_id == other:
                raise RuntimeError("before snapshot failed")
            return original(op)

        with patch.object(type(launcher), "_create_schedule_snapshot", snapshot):
            with self.assertRaisesRegex(RuntimeError, "before snapshot failed"), self.env.cr.savepoint():
                launcher.action_execute()
        self.assertFalse(FakeFiscalization.calls)
        self.assertTrue(launcher.exists())
        self.assertEqual(launcher.state, "draft")

    def test_successful_recovery_is_a_new_linked_get_and_original_stays_immutable(self):
        original = self._uncertain_registration()
        history = self._history(original)
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = self._remote_hours()
        action = original.action_reconcile()
        recovery = self.Operation.browse(action["res_id"])
        self.assertNotEqual(recovery, original)
        self.assertEqual(recovery.reconciliation_of_id, original)
        self.assertEqual(recovery.operation, "get")
        self.assertEqual(recovery.state, "done")
        self.assertEqual(recovery.business_premise_id, original.business_premise_id)
        self.assertEqual(original.reconciliation_ids, recovery)
        self.assertTrue(original.is_reconciled)
        self.assertEqual(self._history(original), history)
        self.assertEqual([method for method, payload in FakeFiscalization.calls], [
            "prijaviRadnoVrijeme", "dohvatiRadnoVrijeme",
        ])
        self.assertNotEqual(recovery.fiscal_log_id, original.fiscal_log_id)
        self.assertEqual(self.premise._get_all_working_hours().mapped("dow"), ["3"])
        # Reopening an already successful reconciliation must not dispatch again.
        self.assertEqual(original.action_reconcile()["res_id"], recovery.id)
        self.assertEqual(len(FakeFiscalization.calls), 2)
        with self.assertRaises(UserError):
            original.write({"operation": "get"})
        with self.assertRaises(UserError):
            original.action_execute()
        with self.assertRaises(UserError):
            original.unlink()
        # A completed linked GET unblocks subsequent changes without changing history.
        FakeFiscalization.responses["prijaviRadnoVrijeme"] = _ok_response()
        fresh = self._operation("register", lines=[self._register_line()])
        fresh.action_execute()
        self.assertEqual(fresh.state, "done")
        self.assertEqual(self._history(original), history)

    def test_failed_recovery_stays_unresolved_and_retry_creates_another_get(self):
        self._hours()
        original = self._uncertain_registration()
        history = self._history(original)
        before = self.premise._get_working_hours_snapshot()
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = ReadTimeout("recovery timed out")
        first = self.Operation.browse(original.action_reconcile()["res_id"])
        self._assert_unchanged(first, before, state="error")
        self.assertFalse(original.is_reconciled)
        self.assertEqual(first.reconciliation_of_id, original)
        self.assertEqual(self._history(original), history)
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = self._remote_hours()
        second = self.Operation.browse(original.action_reconcile()["res_id"])
        self.assertNotEqual(first, second)
        self.assertEqual(second.operation, "get")
        self.assertEqual(second.state, "done")
        self.assertEqual(second.reconciliation_of_id, original)
        self.assertEqual(len(original.reconciliation_ids), 2)
        self.assertTrue(original.is_reconciled)
        self.assertEqual(self._history(original), history)
        self.assertEqual([method for method, payload in FakeFiscalization.calls], [
            "prijaviRadnoVrijeme", "dohvatiRadnoVrijeme", "dohvatiRadnoVrijeme",
        ])

    def test_unresolved_operation_blocks_new_register_and_remove_without_dispatch(self):
        hours = self._hours()
        original = self._uncertain_registration()
        history = self._history(original)
        for operation, lines in (
            ("register", [self._register_line()]),
            ("remove", [{"action": "remove", "working_hours_id": hours.id}]),
        ):
            with self.subTest(operation=operation):
                fresh = self._operation(operation, lines=lines)
                with self.assertRaisesRegex(UserError, "Reconcile"), self.env.cr.savepoint():
                    fresh.action_execute()
                self.assertEqual(fresh.state, "draft")
                self.assertFalse(fresh.fiscal_log_id)
        # An unrelated GET does not resolve the original: only a linked GET does.
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = self._remote_hours()
        unrelated = self._operation("get")
        unrelated.action_execute()
        self.assertEqual(unrelated.state, "done")
        self.assertFalse(original.is_reconciled)
        self.assertEqual(self._history(original), history)
        self.assertEqual(len(FakeFiscalization.calls), 2)

    def test_multi_record_preparation_failure_sends_nothing(self):
        other = self.env['l10n_hr.business.premise'].create({
            'l10n_hr_name': 'Second direct operation', 'l10n_hr_fiscal_code': 'DIRECT2',
            'company_id': self.company.id,
        })
        first = self._operation('get')
        second = self._operation('get', premise=other)
        original_snapshot = type(first)._create_schedule_snapshot
        FakeFiscalization.responses['dohvatiRadnoVrijeme'] = _get_response()

        def fail_second(op):
            if op == second:
                raise RuntimeError('second direct preparation failed')
            return original_snapshot(op)

        with patch.object(type(first), '_create_schedule_snapshot', fail_second):
            with self.assertRaisesRegex(RuntimeError, 'second direct'), self.env.cr.savepoint():
                (first | second).action_execute()
        self.assertFalse(FakeFiscalization.calls)
        self.assertEqual((first | second).mapped('state'), ['draft', 'draft'])

    def test_multi_record_execution_refuses_duplicate_premises(self):
        first = self._operation('get')
        second = self._operation('register', lines=[self._register_line()])
        with self.assertRaisesRegex(UserError, 'one operation per business premise'), self.env.cr.savepoint():
            (first | second).action_execute()
        self.assertFalse(FakeFiscalization.calls)

    def test_logging_exit_flush_failure_does_not_keep_a_rolled_back_log_id(self):
        self._hours()
        before = self.premise._get_working_hours_snapshot()
        op = self._operation('register', lines=[self._register_line()])
        FakeFiscalization.responses['prijaviRadnoVrijeme'] = _ok_response()
        original_log = type(self.company).create_fiscal_log
        original_flush = type(self.env.cr).flush
        armed = []
        created = []

        def log_then_arm(company, *args, **kwargs):
            log = original_log(company, *args, **kwargs)
            created.extend(log.ids)
            armed.append(True)
            return log

        def flush(cursor):
            if cursor is self.env.cr and armed:
                armed.clear()
                raise RuntimeError('log exit flush failed')
            return original_flush(cursor)

        with (
            patch.object(type(self.company), 'create_fiscal_log', log_then_arm),
            patch.object(type(self.env.cr), 'flush', flush),
        ):
            op.action_execute()
        self.assertTrue(created)
        self.assertFalse(self.env['l10n_hr.fiscal.log'].browse(created).exists())
        self.assertFalse(op.fiscal_log_id)
        self.assertEqual(op.state, 'uncertain')
        self.assertEqual(op.snapshot_before or [], before)
        self.assertEqual(op.snapshot_after or [], before)
        self.assertEqual(self.premise._get_working_hours_snapshot(), before)
        self.assertIn('log exit flush failed', op.error_msg)

    def test_mixed_launcher_and_executed_record_are_rejected_before_dispatch(self):
        other = self.env['l10n_hr.business.premise'].create({
            'l10n_hr_name': 'Already done premise', 'l10n_hr_fiscal_code': 'ALREADYDONE',
            'company_id': self.company.id,
        })
        FakeFiscalization.responses['dohvatiRadnoVrijeme'] = _get_response()
        done = self._operation('get', premise=other)
        done.action_execute()
        FakeFiscalization.calls = []
        launcher = self.Operation.create({'business_premise_ids': [Command.set(self.premise.ids)]})
        with self.assertRaises(UserError), self.env.cr.savepoint():
            (launcher | done).action_execute()
        self.assertFalse(FakeFiscalization.calls)
        self.assertEqual(done.state, 'done')

    def test_failed_local_recovery_can_be_reconciled_through_the_original(self):
        original = self._uncertain_registration()
        FakeFiscalization.responses['dohvatiRadnoVrijeme'] = self._remote_hours()
        with patch.object(type(self.premise), '_replace_working_hours', side_effect=RuntimeError('local recovery failed')):
            first = self.Operation.browse(original.action_reconcile()['res_id'])
        self.assertEqual(first.state, 'uncertain')
        self.assertFalse(original.is_reconciled)

        successful = self.Operation.browse(first.action_reconcile()['res_id'])

        self.assertEqual(successful.state, 'done')
        self.assertEqual(successful.reconciliation_of_id, original)
        self.assertEqual(len(original.reconciliation_ids), 2)
        self.assertTrue(original.is_reconciled)
        FakeFiscalization.responses['prijaviRadnoVrijeme'] = _ok_response()
        fresh = self._operation('register', lines=[self._register_line()])
        fresh.action_execute()
        self.assertEqual(fresh.state, 'done', 'failed linked attempts must not block a reconciled original')

    def test_trusted_structured_errors_are_rejections_independent_of_silent_flag(self):
        self._hours()
        before = self.premise._get_working_hours_snapshot()
        for silent in (False, True):
            with self.subTest(silent=silent):
                self.company.l10n_hr_fiscal_silent_error_logging = silent
                FakeFiscalization.responses["prijaviRadnoVrijeme"] = _error_response("s002", "Trusted rejection")
                op = self._operation("register", lines=[self._register_line()])
                op.action_execute()
                self._assert_unchanged(op, before, state="error")
                self.assertIn("Trusted rejection", op.error_msg)
                self.assertFalse(op.reconciliation_ids)
        self.assertEqual(len(FakeFiscalization.calls), 2)
