"""``l10n_hr.fiscal.operation`` is the single record of every working hours exchange
with the Porezna uprava (FINA) for a business premise.

The ``to_register`` / ``to_remove`` flags on ``l10n_hr.business.working.hours`` were
removed; the operation itself now carries the intended changes as
``l10n_hr.fiscal.operation.line`` records. Each executed operation also creates
persistent ``l10n_hr.working.hours.schedule`` snapshots before and after the call,
so the history of working hours can be reviewed over time.

These tests drive the three operations against a fake FINA client. No network, no
certificate: the fake returns canned zeep-like responses and records what it was
asked to send.
"""
from types import SimpleNamespace
from unittest.mock import patch

from lxml import etree

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..fiscal import fiscal as fiscal_module


def _ns(**kwargs):
    return SimpleNamespace(**kwargs)


class _FakeType(SimpleNamespace):
    """A zeep-like complex type: any element not explicitly set reads as ``None``
    (zeep pre-initializes every element), so ``obj.Jednokratno or []`` works."""

    def __getattr__(self, name):
        return None


class FakeTypeFactory:
    """Stand-in for ``zeep`` ``type_factory``: every FINA type is a plain namespace."""

    def __getattr__(self, name):
        def build(**kwargs):
            obj = _FakeType(**kwargs)
            obj._type = name
            return obj

        return build


class FakeFiscalization:
    """Replaces ``fiscal.Fiscalization`` - one canned response per FINA method."""

    responses = {}
    calls = []

    def __init__(self, data=None, **other):
        envelope = etree.Element("Envelope")
        self.history = _ns(last_sent={"envelope": envelope}, last_received={"envelope": envelope})
        self.fiscal_plugin = _ns(last_verification_ok=True)
        self.type_factory = FakeTypeFactory()
        self.client = _ns(service={name: name for name in (
            "dohvatiRadnoVrijeme", "prijaviRadnoVrijeme", "obrisiRadnoVrijeme")})

    def create_request_header(self):
        return _ns(IdPoruke="fake-id", DatumVrijeme="01.01.2026T00:00:00")

    def _call_service(self, service_proxy, req_kw):
        type(self).calls.append((service_proxy, req_kw))
        response = type(self).responses[service_proxy]
        if isinstance(response, Exception):
            raise response
        return response


def _ok_response(**extra):
    return _ns(Zaglavlje=_ns(IdPoruke="resp-id", DatumVrijeme="01.01.2026T00:00:01"), Greske=None, **extra)


def _error_response(code, message):
    return _ns(Zaglavlje=_ns(IdPoruke="resp-id", DatumVrijeme="01.01.2026T00:00:01"),
               Greske=_ns(Greska=[_ns(SifraGreske=code, PorukaGreske=message)]))


def _get_response(regular=(), exceptions=()):
    """A DohvatiRadnoVrijemeOdgovor with the given RedovnoType / IznimkeType entries."""
    return _ok_response(PoslovniProstor=_ns(RadnoVrijeme=_ns(Redovno=list(regular), Iznimke=list(exceptions))))


OPERATOR_OIB = "69435151530"


@tagged("post_install", "-at_install")
class TestFiscalOperation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({"company_registry": "12345678901", "l10n_hr_fiscal_silent_error_logging": False})
        # OibOper is the sending user's employee's OIB, on their work contact
        cls.operator = cls.env["hr.employee"].create({
            "name": "Operations operator",
            "company_id": cls.company.id,
            "user_id": cls.env.user.id,
        })
        cls.operator.work_contact_id.company_registry = OPERATOR_OIB
        cls.premise = cls.env["l10n_hr.business.premise"].create({
            "l10n_hr_name": "Test premise",
            "l10n_hr_fiscal_code": "TESTPP",
            "company_id": cls.company.id,
        })
        cls.WorkingHours = cls.env["l10n_hr.business.working.hours"]
        cls.Operation = cls.env["l10n_hr.fiscal.operation"]
        cls.OperationLine = cls.env["l10n_hr.fiscal.operation.line"]
        cls.Schedule = cls.env["l10n_hr.working.hours.schedule"]

    def setUp(self):
        super().setUp()
        FakeFiscalization.responses = {}
        FakeFiscalization.calls = []
        self.patchers = [
            patch.object(fiscal_module, "Fiscalization", FakeFiscalization),
            patch.object(type(self.company), "get_fiscal_data", lambda company: {}),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def _hours(self, **vals):
        return self.WorkingHours.create(dict({
            "business_premise_id": self.premise.id,
            "type": "regular",
            "dow": "1",
            "valid_from": "2026-01-01",
            "time_from": "08:00",
            "time_to": "16:00",
        }, **vals))

    def _other_premise(self):
        return self.env['l10n_hr.business.premise'].create({
            'l10n_hr_name': 'Second premise',
            'l10n_hr_fiscal_code': 'TESTPP2',
            'company_id': self.company.id,
        })

    def _run(self, operation, lines=None):
        vals = {"business_premise_id": self.premise.id, "operation": operation}
        op = self.Operation.create(vals)
        if lines:
            for line in lines:
                line.setdefault("operation_id", op.id)
                self.OperationLine.create(line)
        op.action_execute()
        return op

    # -- get -----------------------------------------------------------------
    def test_get_replaces_local_hours_and_records_the_diff(self):
        """``get`` mirrors FINA locally; the operation shows exactly what that changed."""
        # unchanged: FINA sends Napomena="Note" for the whole group, so the local
        # shift must already carry it to stay identical
        self._hours(dow="1", time_from="08:00", time_to="16:00", description="Note")
        self._hours(dow="2", time_from="08:00", time_to="16:00")  # changed times
        self._hours(dow="3", time_from="08:00", time_to="16:00")  # removed
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = _get_response(
            regular=[_ns(DatumOd="01.01.2026", Napomena="Note",
                         Jednokratno=[_ns(DanUTjednu="1", RadnoVrijemeOd="08:00", RadnoVrijemeDo="16:00"),
                                      _ns(DanUTjednu="2", RadnoVrijemeOd="09:00", RadnoVrijemeDo="17:00")],
                         Dvokratno=[_ns(DanUTjednu="4", DioDvokratnog="1",
                                        RadnoVrijemeOd="08:00", RadnoVrijemeDo="12:00")],
                         PoDogovoru=None, ParniNeparni=None)],
            exceptions=[_ns(Datum="24.12.2026",
                            Jednokratno=[_ns(RadnoVrijemeOd="08:00", RadnoVrijemeDo="12:00")],
                            Dvokratno=[])],
        )

        op = self._run("get")

        self.assertEqual(op.state, "done")
        self.assertEqual(op.msg_type, "dohvatiRadnoVrijeme")
        hours = self.premise._get_all_working_hours()
        self.assertEqual(len(hours), 4)
        self.assertEqual(set(hours.mapped("type")), {"regular", "exception"})
        exception = hours.filtered(lambda h: h.type == "exception")
        self.assertEqual(str(exception.valid_on), "2026-12-24")
        self.assertEqual(exception.dow, "4", "exception day of week derived from its date (Thursday)")

        self.assertEqual(len(op.snapshot_before), 3)
        self.assertEqual(len(op.snapshot_after), 4)
        by_status = {}
        for line in op.diff:
            by_status.setdefault(line["status"], []).append(line)
        # dow 1: identical, so not in the diff at all
        self.assertNotIn("1", [d["key"]["dow"] for d in op.diff if d["key"]["type"] == "regular"])
        # dow 2: same key, different value -> changed (description also arrived)
        self.assertEqual(op.changed_count, 1)
        changed = by_status["changed"][0]
        self.assertEqual(changed["key"]["dow"], "2")
        self.assertEqual(changed["before"]["time_from"], "08:00")
        self.assertEqual(changed["after"], {"time_from": "09:00", "time_to": "17:00", "description": "Note"})
        # dow 3: gone
        self.assertEqual(op.removed_count, 1)
        self.assertEqual(by_status["removed"][0]["key"]["dow"], "3")
        # dow 4 split shift + the exception: new
        self.assertEqual(op.added_count, 2)
        self.assertTrue(op.has_changes)
        # rendered for humans
        self.assertIn("table-danger", op.diff_html)
        self.assertIn("Thursday", op.snapshot_after_html)

    def test_get_creates_persistent_schedule_snapshots(self):
        """Each executed operation stores before/after schedule snapshots."""
        self._hours(dow="1", time_from="08:00", time_to="16:00")
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = _get_response(
            regular=[_ns(DatumOd="01.01.2026",
                         Jednokratno=[_ns(DanUTjednu="1", RadnoVrijemeOd="08:00", RadnoVrijemeDo="16:00")],
                         Dvokratno=[], PoDogovoru=None, ParniNeparni=None)],
        )

        op = self._run("get")

        self.assertTrue(op.schedule_before_id)
        self.assertTrue(op.schedule_after_id)
        self.assertNotEqual(op.schedule_before_id, op.schedule_after_id)
        self.assertEqual(op.schedule_before_id.fiscal_operation_id, op)
        self.assertEqual(op.schedule_after_id.fiscal_operation_id, op)
        self.assertIn(self.premise, op.schedule_before_id.business_premise_ids)
        self.assertTrue(op.schedule_before_id.line_ids)

    # -- register ------------------------------------------------------------
    def test_register_sends_inline_lines_and_creates_them(self):
        """Register lines without a referenced record create new working hours."""
        lines = [
            {"action": "register", "type": "regular", "dow": "1", "valid_from": "2026-01-01",
             "time_from": "08:00", "time_to": "16:00", "description": "Open"},
            {"action": "register", "type": "regular", "dow": "3", "valid_from": "2026-01-01",
             "time_from": "14:00", "time_to": "20:00", "split_shift": "2"},
            {"action": "register", "type": "exception", "valid_on": "2026-05-01",
             "time_from": "10:00", "time_to": "12:00"},
        ]
        FakeFiscalization.responses["prijaviRadnoVrijeme"] = _ok_response()

        op = self._run("register", lines=lines)

        self.assertEqual(op.state, "done")
        method, payload = FakeFiscalization.calls[-1]
        self.assertEqual(method, "prijaviRadnoVrijeme")
        premise_payload = payload["PoslovniProstor"]
        self.assertEqual(premise_payload.OznPosPr, "TESTPP")
        self.assertEqual(premise_payload.Oib, "12345678901")
        (regular,) = premise_payload.RadnoVrijeme.Redovno
        self.assertEqual(regular.DatumOd, "01.01.2026")
        self.assertEqual(regular.Napomena, "Open")
        self.assertEqual([s.DanUTjednu for s in regular.Jednokratno], ["1"])
        self.assertEqual([s.DanUTjednu for s in regular.Dvokratno], ["3"])
        (exception,) = premise_payload.RadnoVrijeme.Iznimke
        self.assertEqual(exception.Datum, "01.05.2026")
        self.assertEqual(exception.Jednokratno[0].RadnoVrijemeOd, "10:00")

        hours = self.premise._get_all_working_hours()
        self.assertEqual(len(hours), 3)
        self.assertTrue(op.has_changes)
        self.assertEqual(op.added_count, 3)

    def test_register_can_re_register_existing_record(self):
        """A register line can reference an existing local record to avoid duplicates."""
        existing = self._hours(dow="1", time_from="08:00", time_to="16:00", description="Existing")
        lines = [
            {"action": "register", "working_hours_id": existing.id},
        ]
        FakeFiscalization.responses["prijaviRadnoVrijeme"] = _ok_response()

        op = self._run("register", lines=lines)

        self.assertEqual(len(self.premise._get_all_working_hours()), 1)
        method, payload = FakeFiscalization.calls[-1]
        regular = payload["PoslovniProstor"].RadnoVrijeme.Redovno[0]
        self.assertEqual(regular.Jednokratno[0].DanUTjednu, "1")

    def test_register_refuses_when_no_lines_are_selected(self):
        op = self.Operation.create({"business_premise_id": self.premise.id, "operation": "register"})
        with self.assertRaises(UserError):
            op.action_execute()
        self.assertEqual(op.state, "draft")
        self.assertFalse(FakeFiscalization.calls, "nothing must reach FINA")

    # -- remove --------------------------------------------------------------
    def test_remove_sends_distinct_dates_and_deletes_referenced_hours(self):
        to_remove_1 = self._hours(dow="1", valid_from="2026-01-01")
        to_remove_2 = self._hours(dow="2", valid_from="2026-01-01")
        kept = self._hours(dow="3", valid_from="2026-02-01")
        lines = [
            {"action": "remove", "working_hours_id": to_remove_1.id},
            {"action": "remove", "working_hours_id": to_remove_2.id},
        ]
        FakeFiscalization.responses["obrisiRadnoVrijeme"] = _ok_response()

        op = self._run("remove", lines=lines)

        self.assertEqual(op.state, "done")
        _, payload = FakeFiscalization.calls[-1]
        brisanje = payload["PoslovniProstor"].BrisanjeRadnogVremena
        self.assertEqual(brisanje.Redovno, [{"DatumOd": "01.01.2026"}], "one entry per distinct DatumOd")
        self.assertEqual(brisanje.Iznimke, [])
        self.assertEqual(self.premise._get_all_working_hours(), kept)
        self.assertEqual(op.removed_count, 2)
        self.assertEqual((op.added_count, op.changed_count), (0, 0))

    def test_remove_all_sends_every_date_and_deletes_all_hours(self):
        self._hours(dow="1", valid_from="2026-01-01")
        self._hours(dow="2", valid_from="2026-01-01")
        self._hours(dow="3", valid_from="2026-02-01")
        self._hours(type="exception", valid_on="2026-01-01", dow="1", time_from="10:00", time_to="12:00")
        FakeFiscalization.responses["obrisiRadnoVrijeme"] = _ok_response()

        op = self.Operation.create({
            "business_premise_id": self.premise.id,
            "operation": "remove",
            "remove_all": True,
        })
        op.action_execute()

        self.assertEqual(op.state, "done")
        self.assertFalse(self.premise._get_all_working_hours())
        _, payload = FakeFiscalization.calls[-1]
        brisanje = payload["PoslovniProstor"].BrisanjeRadnogVremena
        self.assertEqual(
            brisanje.Redovno,
            [{"DatumOd": "01.01.2026"}, {"DatumOd": "01.02.2026"}],
        )
        self.assertEqual(brisanje.Iznimke, [{"Datum": "01.01.2026"}])

    def test_remove_all_with_no_hours_skips_fina_call(self):
        FakeFiscalization.responses["obrisiRadnoVrijeme"] = _ok_response()

        op = self.Operation.create({
            "business_premise_id": self.premise.id,
            "operation": "remove",
            "remove_all": True,
        })
        op.action_execute()

        self.assertEqual(op.state, "done")
        self.assertFalse(FakeFiscalization.calls, "no FINA call when there is nothing to remove")

    def test_remove_all_fans_out_to_all_selected_premises(self):
        other = self.env["l10n_hr.business.premise"].create({
            "l10n_hr_name": "Second premise",
            "l10n_hr_fiscal_code": "TESTPP2",
            "company_id": self.company.id,
        })
        self._hours()
        self.WorkingHours.create({
            "business_premise_id": other.id,
            "type": "regular",
            "dow": "2",
            "valid_from": "2026-01-01",
            "time_from": "08:00",
            "time_to": "16:00",
        })
        FakeFiscalization.responses["obrisiRadnoVrijeme"] = _ok_response()

        launcher = self.Operation.create({
            "operation": "remove",
            "remove_all": True,
            "business_premise_ids": [(6, 0, (self.premise + other).ids)],
        })
        launcher.action_execute()

        self.assertFalse(launcher.exists())
        children = self.Operation.search([
            ("business_premise_id", "in", (self.premise + other).ids),
            ("operation", "=", "remove"),
        ])
        self.assertEqual(len(children), 2)
        self.assertEqual(set(children.mapped("state")), {"done"})
        self.assertFalse(self.premise._get_all_working_hours())
        self.assertFalse(other._get_all_working_hours())

    def test_remove_all_launcher_discards_obsolete_manual_selections(self):
        other = self._other_premise()
        selected_hours = self._hours()
        unselected_hours = self._hours(business_premise_id=other.id)
        FakeFiscalization.responses['obrisiRadnoVrijeme'] = _ok_response()
        launcher = self.Operation.create({
            'operation': 'remove',
            'business_premise_ids': [Command.set((self.premise | other).ids)],
            'line_ids': [Command.create({'action': 'remove', 'working_hours_id': unselected_hours.id})],
        })
        # The user narrows the premises and switches from selected removal to All.
        launcher.write({'business_premise_ids': [Command.set(self.premise.ids)], 'remove_all': True})

        launcher.action_execute()

        self.assertFalse(launcher.exists())
        self.assertFalse(selected_hours.exists())
        self.assertTrue(unselected_hours.exists())
        self.assertEqual(len(FakeFiscalization.calls), 1)
        self.assertEqual(FakeFiscalization.calls[0][1]['PoslovniProstor'].OznPosPr, 'TESTPP')

    # -- errors --------------------------------------------------------------
    def test_fina_error_is_kept_as_history_not_raised(self):
        """A rejected message must not roll back the record that documents it."""
        lines = [
            {"action": "register", "type": "regular", "dow": "1", "valid_from": "2026-01-01",
             "time_from": "08:00", "time_to": "16:00"},
        ]
        FakeFiscalization.responses["prijaviRadnoVrijeme"] = _error_response("s002", "Certifikat nije valjan")

        op = self._run("register", lines=lines)

        self.assertEqual(op.state, "error")
        self.assertIn("Certifikat nije valjan", op.error_msg)
        self.assertFalse(self.premise._get_all_working_hours(), "no record created on error")
        self.assertFalse(op.has_changes)
        self.assertTrue(op.fiscal_log_id, "the failed exchange is still logged")

    def test_fina_error_with_silent_logging_is_still_an_error(self):
        self.company.l10n_hr_fiscal_silent_error_logging = True
        lines = [
            {"action": "register", "type": "regular", "dow": "1", "valid_from": "2026-01-01",
             "time_from": "08:00", "time_to": "16:00"},
        ]
        FakeFiscalization.responses["prijaviRadnoVrijeme"] = _error_response("s002", "Certifikat nije valjan")

        op = self._run("register", lines=lines)

        self.assertEqual(op.state, "error", "the log is the authority even when nothing was raised")
        self.assertIn("Certifikat nije valjan", op.error_msg)

    def test_transport_error_is_kept_as_history(self):
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = ConnectionError("FINA unreachable")
        self._hours()

        op = self._run("get")

        self.assertEqual(op.state, "error")
        self.assertIn("FINA unreachable", op.error_msg)
        self.assertEqual(len(self.premise._get_all_working_hours()), 1, "local data untouched")
        self.assertEqual(op.snapshot_before, op.snapshot_after)

    # -- log linkage & immutability ------------------------------------------
    def test_fiscal_log_points_back_at_the_operation(self):
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = _get_response()
        op = self._run("get")
        # created and executed after op, so it is the most recent operation
        other = self.Operation.create({"business_premise_id": self.premise.id, "operation": "get"})
        other.action_execute()

        for record in (op, other):
            log = record.fiscal_log_id
            self.assertTrue(log)
            self.assertEqual((log.res_model, log.res_id), ("l10n_hr.fiscal.operation", record.id))
            self.assertEqual(log.business_premise_id, self.premise)
            self.assertEqual(log.type, "dohvatiRadnoVrijeme")
            self.assertEqual(record.request_msg, log.content)
        self.assertNotEqual(op.fiscal_log_id, other.fiscal_log_id, "no guessing: each operation owns its log")
        self.assertIn(op, self.premise.fiscal_operation_ids)
        self.assertEqual(self.premise.fiscal_operation_count, 2)
        self.assertEqual(self.premise.last_fiscal_operation_id, other)

    def test_executed_operation_is_immutable(self):
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = _get_response()
        op = self._run("get")

        with self.assertRaises(UserError):
            op.write({"operation": "remove"})
        with self.assertRaises(UserError):
            op.unlink()
        with self.assertRaises(UserError):
            op.action_execute()
        # drafts are still disposable
        draft = self.Operation.create({"business_premise_id": self.premise.id})
        draft.write({"operation": "remove"})
        draft.unlink()

    # -- multiple premises ---------------------------------------------------
    def test_draft_launcher_fans_out_one_operation_per_premise(self):
        """A draft with several premises spawns one executed operation each."""
        other = self.env["l10n_hr.business.premise"].create({
            "l10n_hr_name": "Second premise",
            "l10n_hr_fiscal_code": "TESTPP2",
            "company_id": self.company.id,
        })
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = _get_response()
        launcher = self.Operation.create({
            "operation": "get",
            "business_premise_ids": [(6, 0, (self.premise + other).ids)],
        })

        launcher.action_execute()

        self.assertFalse(launcher.exists(), "the launcher is discarded once fanned out")
        children = self.Operation.search([
            ("business_premise_id", "in", (self.premise + other).ids),
            ("operation", "=", "get")])
        self.assertEqual(len(children), 2, "one operation per premise")
        self.assertEqual(set(children.mapped("state")), {"done"})
        self.assertEqual(children.business_premise_id, self.premise + other)

    def test_batch_children_do_not_inherit_the_launchers_premise_defaults(self):
        other = self._other_premise()
        action = (self.premise | other).action_new_fiscal_operation()
        launcher = self.Operation.with_context(**action['context']).create({'operation': 'get'})
        FakeFiscalization.responses['dohvatiRadnoVrijeme'] = _get_response()

        launcher.action_execute()

        children = self.Operation.search([('business_premise_id', 'in', (self.premise | other).ids)])
        self.assertEqual(len(children), 2)
        self.assertEqual(set(children.mapped('state')), {'done'})
        self.assertFalse(children.business_premise_ids, 'a child must represent only its own premise')

    def test_register_launcher_copies_inline_lines_to_every_premise(self):
        other = self._other_premise()
        FakeFiscalization.responses['prijaviRadnoVrijeme'] = _ok_response()
        launcher = self.Operation.create({
            'operation': 'register',
            'business_premise_ids': [Command.set((self.premise | other).ids)],
            'line_ids': [
                Command.create({
                    'action': 'register', 'type': 'regular', 'dow': '2',
                    'valid_from': '2026-01-01', 'time_from': '09:00', 'time_to': '17:00',
                    'description': 'Shared schedule', 'sequence': 20,
                }),
                Command.create({
                    'action': 'register', 'type': 'exception', 'valid_on': '2026-05-01',
                    'time_from': '10:00', 'time_to': '12:00', 'sequence': 30,
                }),
            ],
        })
        launcher_lines = launcher.line_ids

        launcher.action_execute()

        self.assertFalse(launcher.exists())
        self.assertFalse(launcher_lines.exists())
        children = self.Operation.search([('business_premise_id', 'in', (self.premise | other).ids)])
        self.assertEqual(len(children), 2)
        self.assertEqual(set(children.mapped('state')), {'done'})
        self.assertEqual(len(children.line_ids), 4, 'each child owns independent copies')
        for child in children:
            self.assertEqual(child.line_ids.mapped('sequence'), [20, 30])
            self.assertEqual(len(child.business_premise_id._get_all_working_hours()), 2)
            self.assertEqual(child.added_count, 2)
        payloads = {payload['PoslovniProstor'].OznPosPr: payload['PoslovniProstor']
                    for method, payload in FakeFiscalization.calls}
        self.assertEqual(set(payloads), {'TESTPP', 'TESTPP2'})
        for payload in payloads.values():
            regular = payload.RadnoVrijeme.Redovno[0]
            self.assertEqual(regular.Napomena, 'Shared schedule')
            self.assertEqual(regular.Jednokratno[0].DanUTjednu, '2')
            self.assertEqual(regular.Jednokratno[0].RadnoVrijemeOd, '09:00')
            self.assertEqual(payload.RadnoVrijeme.Iznimke[0].Datum, '01.05.2026')

    def test_register_launcher_keeps_existing_references_with_their_premise(self):
        other = self._other_premise()
        first_hours = self._hours(dow='1')
        second_hours = self._hours(business_premise_id=other.id, dow='3')
        FakeFiscalization.responses['prijaviRadnoVrijeme'] = _ok_response()
        launcher = self.Operation.create({
            'operation': 'register',
            'business_premise_ids': [Command.set((self.premise | other).ids)],
            'line_ids': [Command.create({'action': 'register', 'working_hours_id': hours.id})
                         for hours in first_hours | second_hours],
        })

        launcher.action_execute()

        children = self.Operation.search([('business_premise_id', 'in', (self.premise | other).ids)])
        for child in children:
            self.assertEqual(len(child.line_ids), 1)
            self.assertEqual(child.line_ids.working_hours_id.business_premise_id, child.business_premise_id)
            self.assertEqual(len(child.business_premise_id._get_all_working_hours()), 1, 'no duplicates')
        by_code = {payload['PoslovniProstor'].OznPosPr:
                   payload['PoslovniProstor'].RadnoVrijeme.Redovno[0].Jednokratno[0].DanUTjednu
                   for method, payload in FakeFiscalization.calls}
        self.assertEqual(by_code, {'TESTPP': '1', 'TESTPP2': '3'})

    def test_remove_launcher_partitions_selected_hours_by_premise(self):
        other = self._other_premise()
        first_hours = self._hours(valid_from='2026-01-01')
        second_hours = self._hours(business_premise_id=other.id, valid_from='2026-02-01')
        kept_first = self._hours(valid_from='2026-03-01')
        kept_second = self._hours(business_premise_id=other.id, valid_from='2026-03-01')
        FakeFiscalization.responses['obrisiRadnoVrijeme'] = _ok_response()
        launcher = self.Operation.create({
            'operation': 'remove',
            'business_premise_ids': [Command.set((self.premise | other).ids)],
            'line_ids': [Command.create({'action': 'remove', 'working_hours_id': hours.id})
                         for hours in first_hours | second_hours],
        })

        launcher.action_execute()

        self.assertFalse(launcher.exists())
        self.assertFalse((first_hours | second_hours).exists())
        self.assertEqual(self.premise._get_all_working_hours(), kept_first)
        self.assertEqual(other._get_all_working_hours(), kept_second)
        by_code = {payload['PoslovniProstor'].OznPosPr:
                   payload['PoslovniProstor'].BrisanjeRadnogVremena.Redovno
                   for method, payload in FakeFiscalization.calls}
        self.assertEqual(by_code, {
            'TESTPP': [{'DatumOd': '01.01.2026'}],
            'TESTPP2': [{'DatumOd': '01.02.2026'}],
        })

    def test_launcher_checks_every_premise_before_sending(self):
        other = self._other_premise()
        hours = self._hours()
        for operation in ('register', 'remove'):
            with self.subTest(operation=operation):
                launcher = self.Operation.create({
                    'operation': operation,
                    'business_premise_ids': [Command.set((self.premise | other).ids)],
                    'line_ids': [Command.create({'action': operation, 'working_hours_id': hours.id})],
                })
                with self.assertRaises(UserError), self.env.cr.savepoint():
                    launcher.action_execute()
                self.assertTrue(launcher.exists())
                self.assertEqual(launcher.state, 'draft')
                self.assertFalse(FakeFiscalization.calls, 'the second premise has no selected hours')
                self.assertFalse(self.Operation.search([('business_premise_id', '!=', False)]))

    def test_referenced_hours_cannot_be_sent_under_another_premise(self):
        other = self._other_premise()
        foreign_hours = self._hours(business_premise_id=other.id)
        for operation in ('register', 'remove'):
            for batch in (False, True):
                with self.subTest(operation=operation, batch=batch):
                    vals = {
                        'operation': operation,
                        'line_ids': [Command.create({'action': operation, 'working_hours_id': foreign_hours.id})],
                    }
                    if batch:
                        vals['business_premise_ids'] = [Command.set(self.premise.ids)]
                    else:
                        vals['business_premise_id'] = self.premise.id
                    with self.assertRaisesRegex(UserError, 'must belong'), self.env.cr.savepoint():
                        op = self.Operation.create(vals)
                        op.action_execute()
                    self.assertTrue(foreign_hours.exists())
                    self.assertFalse(FakeFiscalization.calls)

    def test_remove_refuses_partial_date_groups(self):
        regular_first = self._hours(dow='1')
        regular_second = self._hours(dow='2')
        exception_first = self._hours(type='exception', valid_on='2026-05-01', split_shift='1')
        exception_second = self._hours(type='exception', valid_on='2026-05-01', split_shift='2')
        for selected in (regular_first, exception_first):
            with self.subTest(type=selected.type):
                op = self.Operation.create({
                    'business_premise_id': self.premise.id,
                    'operation': 'remove',
                    'line_ids': [Command.create({'action': 'remove', 'working_hours_id': selected.id})],
                })
                with self.assertRaisesRegex(UserError, 'Select every entry'), self.env.cr.savepoint():
                    op.action_execute()
                self.assertEqual(op.state, 'draft')
                self.assertFalse(FakeFiscalization.calls)
        self.assertEqual(len((regular_first | regular_second | exception_first | exception_second).exists()), 4)

    def test_remove_launcher_checks_complete_dates_before_sending(self):
        other = self._other_premise()
        first_hours = self._hours()
        second_hours = self._hours(business_premise_id=other.id, dow='1')
        self._hours(business_premise_id=other.id, dow='2')
        launcher = self.Operation.create({
            'operation': 'remove',
            'business_premise_ids': [Command.set((self.premise | other).ids)],
            'line_ids': [Command.create({'action': 'remove', 'working_hours_id': hours.id})
                         for hours in first_hours | second_hours],
        })
        with self.assertRaisesRegex(UserError, 'Select every entry'), self.env.cr.savepoint():
            launcher.action_execute()
        self.assertFalse(FakeFiscalization.calls)
        self.assertTrue((first_hours | second_hours).exists())

    def test_register_and_remove_actions_open_a_draft_for_selection(self):
        other = self._other_premise()
        for premises in (self.premise, self.premise | other):
            for operation in ('register', 'remove'):
                with self.subTest(premises=premises.ids, operation=operation):
                    action = getattr(premises, f'action_{operation}_working_hours')()
                    self.assertEqual(action['res_model'], self.Operation._name)
                    self.assertEqual(action['context']['default_operation'], operation)
                    self.assertEqual(action['context']['default_business_premise_ids'], premises.ids)
                    self.assertFalse(FakeFiscalization.calls, 'the user must select entries first')

    def test_operation_needs_a_premise_to_execute(self):
        op = self.Operation.create({"operation": "get"})
        with self.assertRaises(UserError):
            op.action_execute()
        self.assertEqual(op.state, "draft")

    # -- pure diff -----------------------------------------------------------
    def test_diff_pairs_changed_shifts_and_ignores_order(self):
        line = lambda dow, tf, tt, desc="": {  # noqa: E731
            "type": "regular", "valid_from": "2026-01-01", "valid_on": None, "dow": dow,
            "split_shift": None, "time_from": tf, "time_to": tt, "description": desc}
        before = [line("1", "08:00", "16:00"), line("2", "08:00", "16:00")]
        after = [line("2", "08:00", "16:00"), line("1", "09:00", "16:00"), line("3", "08:00", "12:00")]
        diff = self.Operation._compute_diff(before, after)
        self.assertEqual([d["status"] for d in diff], ["changed", "added"])
        self.assertEqual(diff[0]["key"]["dow"], "1")
        self.assertEqual(diff[1]["key"]["dow"], "3")
        self.assertEqual(self.Operation._compute_diff(before, list(reversed(before))), [])
        self.assertEqual(self.Operation._compute_diff(None, None), [])

    # -- operator ------------------------------------------------------------
    def test_messages_carry_the_sending_users_employee_oib(self):
        """``OibOper`` is the OIB on the sending user's employee."""
        FakeFiscalization.responses["dohvatiRadnoVrijeme"] = _get_response()
        self._run("get")
        self.assertEqual(FakeFiscalization.calls[0][1]["OibOper"], OPERATOR_OIB)

    def test_nothing_is_sent_without_an_operator_oib(self):
        """An operator without an OIB stops the operation before FINA is called."""
        self.operator.work_contact_id.company_registry = False
        op = self._run("get")
        self.assertEqual(op.state, "error")
        self.assertIn("has no OIB", op.error_msg)
        self.assertFalse(FakeFiscalization.calls)

    def test_a_login_oib_without_employee_is_not_reported(self):
        """A login whose own contact has an OIB but who is no employee sends nothing."""
        self.operator.user_id = False
        self.assertEqual(self.env.user.partner_id.company_registry, OPERATOR_OIB)
        op = self._run("get")
        self.assertEqual(op.state, "error")
        self.assertIn("No fiscal operator", op.error_msg)
        self.assertFalse(FakeFiscalization.calls)
