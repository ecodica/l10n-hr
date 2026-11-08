"""Fiscal permissions, company boundaries and audit history are enforced server-side."""
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged

from ..fiscal import fiscal as fiscal_module
from .test_fiscal_operation import FakeFiscalization, OPERATOR_OIB, _get_response, _ok_response


@tagged('post_install', '-at_install')
class TestFiscalSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.company_registry = '12345678901'
        cls.other_company = cls.env['res.company'].create({'name': 'Other fiscal company'})
        cls.premise = cls.env['l10n_hr.business.premise'].create({
            'l10n_hr_name': 'Allowed premise', 'l10n_hr_fiscal_code': 'SEC1', 'company_id': cls.company.id,
        })
        cls.other_premise = cls.env['l10n_hr.business.premise'].create({
            'l10n_hr_name': 'Other company premise', 'l10n_hr_fiscal_code': 'SEC2',
            'company_id': cls.other_company.id,
        })
        companies = cls.company | cls.other_company
        cls.manager = new_test_user(
            cls.env, login='fiscal_manager', groups='l10n_hr_account_fiscal.group_fiscal_manager',
            company_id=cls.company.id, company_ids=[Command.set(companies.ids)],
        )
        cls.other_manager = new_test_user(
            cls.env, login='other_fiscal_manager', groups='l10n_hr_account_fiscal.group_fiscal_manager',
            company_id=cls.company.id, company_ids=[Command.set(companies.ids)],
        )
        cls.billing = new_test_user(
            cls.env, login='fiscal_billing', groups='account.group_account_invoice',
            company_id=cls.company.id, company_ids=[Command.set(companies.ids)],
        )
        cls.internal = new_test_user(cls.env, login='fiscal_internal', groups='base.group_user')
        operator = cls.env['hr.employee'].create({
            'name': 'Fiscal manager operator', 'user_id': cls.manager.id, 'company_id': cls.company.id,
        })
        operator.work_contact_id.company_registry = OPERATOR_OIB
        cls.Operation = cls.env['l10n_hr.fiscal.operation']

    def setUp(self):
        super().setUp()
        FakeFiscalization.calls = []
        FakeFiscalization.responses = {
            'dohvatiRadnoVrijeme': _get_response(),
            'prijaviRadnoVrijeme': _ok_response(),
            'obrisiRadnoVrijeme': _ok_response(),
        }
        for patcher in (
            patch.object(fiscal_module, 'Fiscalization', FakeFiscalization),
            patch.object(type(self.company), 'get_fiscal_data', lambda company: {}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _as(self, records, user, company=None):
        return records.with_user(user).with_context(allowed_company_ids=(company or self.company).ids)

    def _operation(self, operation='get', **extra):
        return self._as(self.Operation, self.manager).create({
            'business_premise_id': self.premise.id, 'operation': operation, **extra,
        })

    def _register(self):
        op = self._operation('register', line_ids=[Command.create({
            'action': 'register', 'type': 'regular', 'valid_from': '2026-01-01',
            'dow': '1', 'time_from': '08:00', 'time_to': '16:00',
        })])
        op.action_execute()
        return op

    def test_fiscal_manager_needs_no_accounting_role(self):
        self.assertFalse(self.manager.has_group('account.group_account_invoice'))
        self.assertFalse(self.manager.has_group('account.group_account_manager'))
        op = self._operation()
        op.action_execute()
        self.assertEqual(op.state, 'done')
        self.assertTrue(op.fiscal_log_id)
        self.assertEqual(len(FakeFiscalization.calls), 1)
        self.assertTrue(op.schedule_before_id)

    def test_standalone_premise_view_needs_no_accounting_access(self):
        premise = self._as(self.premise, self.manager)
        view = premise.get_view(
            view_id=self.env.ref('l10n_hr_account_fiscal.fiscal_premise_form_view').id,
            view_type='form',
        )
        self.assertNotIn('l10n_hr_journal_ids', view['arch'])
        self.assertNotIn('l10n_hr_sequence_id', view['arch'])
        self.assertTrue(premise.web_read({
            'l10n_hr_name': {}, 'l10n_hr_fiscal_code': {},
            'regular_working_hours_ids': {'fields': {'display_name': {}}},
            'exception_working_hours_ids': {'fields': {'display_name': {}}},
        }))

    def test_billing_can_read_but_not_execute_or_create_operations(self):
        op = self._operation()
        self.assertEqual(self._as(op, self.billing).read(['state'])[0]['state'], 'draft')
        with self.assertRaises(AccessError):
            self._as(op, self.billing).action_execute()
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self._as(self.Operation, self.billing).create({'business_premise_id': self.premise.id})
        self.assertFalse(FakeFiscalization.calls)

    def test_internal_users_cannot_read_raw_fiscal_data(self):
        for model in (
            'l10n_hr.fiscal.log', 'l10n_hr.fiscal.operation', 'l10n_hr.fiscal.operation.line',
            'l10n_hr.business.working.hours', 'l10n_hr.working.hours.schedule',
            'l10n_hr.working.hours.schedule.line',
        ):
            with self.subTest(model=model), self.assertRaises(AccessError):
                self._as(self.env[model], self.internal).check_access('read')

    def test_logs_are_read_only_and_created_only_by_private_logging(self):
        op = self._operation()
        op.action_execute()
        log = op.fiscal_log_id
        self.assertTrue(getattr(type(self.company).create_fiscal_log, '_api_private', False))
        for user in (self.manager, self.billing):
            with self.subTest(user=user.login):
                scoped_log = self._as(log, user)
                self.assertTrue(scoped_log.read(['content']))
                with self.assertRaises(AccessError), self.env.cr.savepoint():
                    scoped_log.create({
                        'company_id': self.company.id, 'res_model': op._name, 'res_id': op.id,
                        'error_msg': 'Fabricated success',
                    })
                with self.assertRaises(AccessError):
                    scoped_log.write({'error_msg': 'Forged'})
                with self.assertRaises(AccessError):
                    scoped_log.unlink()

    def test_context_cannot_bypass_history_guards(self):
        op = self._operation()
        op.action_execute()
        with self.assertRaises(UserError):
            op.with_context(l10n_hr_fiscal_operation_execute=True).write({
                'state': 'draft', 'snapshot_after': [{'forged': True}],
            })
        self.assertEqual(op.state, 'done')
        draft = self._operation()
        with self.assertRaises(UserError):
            draft.write({'state': 'done'})
        with self.assertRaises(UserError):
            draft.write({'fiscal_log_id': op.fiscal_log_id.id})
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self._as(self.Operation, self.manager).create({
                'business_premise_id': self.premise.id, 'snapshot_before': [{'forged': True}],
            })

    def test_context_defaults_cannot_fabricate_audit_history(self):
        op = self._operation()
        op.action_execute()
        for defaults in (
            {'default_state': 'done'},
            {'default_snapshot_after': [{'forged': True}]},
            {'default_fiscal_log_id': op.fiscal_log_id.id},
        ):
            with self.subTest(defaults=defaults), self.assertRaises(UserError), self.env.cr.savepoint():
                self._as(self.Operation, self.manager).with_context(**defaults).create({
                    'business_premise_id': self.premise.id,
                })
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self._as(self.env['l10n_hr.working.hours.schedule'], self.manager).with_context(
                default_fiscal_operation_id=op.id,
            ).create({'company_id': self.company.id})

    def test_inactive_lines_cannot_copy_another_company_into_history(self):
        other_hours = self.env['l10n_hr.business.working.hours'].create({
            'business_premise_id': self.other_premise.id, 'valid_from': '2026-01-01',
            'time_from': '08:00', 'time_to': '16:00', 'description': 'Other company data',
        })
        with self.assertRaisesRegex(UserError, 'must belong'), self.env.cr.savepoint():
            self._as(self.Operation, self.manager, self.company | self.other_company).create({
                'business_premise_id': self.premise.id,
                'operation': 'get',
                'line_ids': [Command.create({'action': 'register', 'working_hours_id': other_hours.id})],
            })
        self.assertFalse(FakeFiscalization.calls)

    def test_executed_lines_cannot_be_edited_moved_or_appended(self):
        op = self._register()
        line = op.line_ids
        draft = self._operation('register')
        with self.assertRaises(UserError):
            line.write({'time_from': '10:00'})
        with self.assertRaises(UserError):
            line.write({'operation_id': draft.id})
        with self.assertRaises(UserError):
            line.unlink()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self._as(self.env[line._name], self.manager).create({
                'operation_id': op.id, 'action': 'register', 'working_hours_id': line.working_hours_id.id,
            })

    def test_deleting_source_hours_keeps_executed_lines_and_values(self):
        existing = self.env['l10n_hr.business.working.hours'].create({
            'business_premise_id': self.premise.id, 'valid_from': '2026-01-01',
            'time_from': '08:00', 'time_to': '16:00',
        })
        op = self._operation('register', line_ids=[Command.create({
            'action': 'register', 'working_hours_id': existing.id,
        })])
        op.action_execute()
        line = op.line_ids
        self.assertTrue(line.working_hours_id)
        refresh = self._operation()
        refresh.action_execute()
        line.invalidate_recordset()
        self.assertTrue(line.exists())
        self.assertFalse(line.working_hours_id)
        self.assertEqual((line.time_from, line.time_to), ('08:00', '16:00'))
        self.assertEqual(str(line.valid_from), '2026-01-01')

    def test_audit_snapshots_cannot_be_rebuilt_or_forged(self):
        op = self._register()
        schedule = self._as(op.schedule_after_id, self.manager)
        line = schedule.line_ids[:1]
        self.assertTrue(line)
        with self.assertRaises(UserError):
            schedule.action_compute()
        with self.assertRaises(UserError):
            schedule.write({'date_from': '2027-01-01'})
        with self.assertRaises(UserError):
            schedule.write({'fiscal_operation_id': False})
        with self.assertRaises(UserError):
            schedule.unlink()
        with self.assertRaises(UserError):
            line.write({'closed': True})
        with self.assertRaises(UserError):
            line.unlink()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self._as(self.env[schedule._name], self.manager).create({
                'fiscal_operation_id': op.id, 'company_id': self.company.id,
            })

    def test_other_company_records_are_hidden(self):
        other_op = self.Operation.create({'business_premise_id': self.other_premise.id})
        other_line = self.env['l10n_hr.fiscal.operation.line'].create({
            'operation_id': other_op.id, 'action': 'register', 'valid_from': '2026-01-01',
            'time_from': '08:00', 'time_to': '16:00',
        })
        other_hours = self.env['l10n_hr.business.working.hours'].create({
            'business_premise_id': self.other_premise.id, 'time_from': '08:00', 'time_to': '16:00',
        })
        other_log = self.env['l10n_hr.fiscal.log'].create({
            'company_id': self.other_company.id, 'res_model': other_op._name, 'res_id': other_op.id,
        })
        schedule = self.env['l10n_hr.working.hours.schedule'].create({'company_id': self.other_company.id})
        schedule_line = self.env['l10n_hr.working.hours.schedule.line'].create({
            'schedule_id': schedule.id, 'business_premise_id': self.other_premise.id,
            'date': '2026-01-01', 'closed': True,
        })
        device = self.env['l10n_hr.fiscal.device'].create({
            'l10n_hr_name': 'Other device', 'l10n_hr_business_premise_id': self.other_premise.id,
            'l10n_hr_fiscal_device_code': 1,
        })
        for record in (self.other_premise, device, other_op, other_line, other_hours, other_log,
                       schedule, schedule_line):
            with self.subTest(model=record._name):
                scoped = self._as(record, self.manager)
                self.assertFalse(scoped.search([('id', '=', record.id)]))
                with self.assertRaises(AccessError):
                    scoped.read(['id'])
                self.assertTrue(self._as(record, self.manager, self.other_company).search([('id', '=', record.id)]))

    def test_launcher_cannot_reference_a_disabled_company(self):
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self._as(self.Operation, self.manager).create({
                'business_premise_ids': [Command.set(self.other_premise.ids)],
            })
        self.assertFalse(FakeFiscalization.calls)

    def test_companyless_launchers_are_private_to_their_creator(self):
        launcher = self._as(self.Operation, self.manager).create({
            'business_premise_ids': [Command.set(self.premise.ids)],
        })
        self.assertTrue(launcher.search([('id', '=', launcher.id)]))
        for user in (self.other_manager, self.billing):
            self.assertFalse(self._as(launcher, user).search([('id', '=', launcher.id)]))
