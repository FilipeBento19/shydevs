from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import Person, Project, Status, Subtask, Task
from .test_references import client_for, make_person


class TaskDependencyTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='P1')
        self.admin = make_person(self.project, 'admin', is_admin=True)
        self.member = make_person(self.project, 'member')
        self.first = Task.objects.create(project=self.project, title='Primeira', role='Dev', assignee=self.member)
        self.second = Task.objects.create(
            project=self.project, title='Segunda', role='Dev', assignee=self.member, depends_on=self.first,
        )
        self.api = client_for(self.admin)

    def patch(self, task, **data):
        return self.api.patch(f'/api/tasks/{task.id}/', data, format='json')

    def test_blocked_task_cannot_be_started_or_finished(self):
        for status in (Status.EM_ANDAMENTO, Status.CONCLUIDA):
            response = self.patch(self.second, status=status)
            self.assertEqual(response.status_code, 400)
            self.assertIn('status', response.data)
        self.second.refresh_from_db()
        self.assertEqual(self.second.status, Status.PENDENTE)

    def test_task_is_released_once_the_dependency_is_done(self):
        self.patch(self.first, status=Status.CONCLUIDA, completion_note='ok')
        response = self.patch(self.second, status=Status.EM_ANDAMENTO)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['blocked'])

    def test_serializer_exposes_dependency(self):
        data = self.api.get(f'/api/tasks/{self.second.id}/').data
        self.assertEqual(data['depends_on'], self.first.id)
        self.assertEqual(data['depends_on_code'], self.first.code)
        self.assertTrue(data['blocked'])

    def test_serializer_lists_tasks_waiting_on_this_one(self):
        data = self.api.get(f'/api/tasks/{self.first.id}/').data
        self.assertEqual([t['code'] for t in data['blocking']], [self.second.code])
        self.patch(self.first, status=Status.CONCLUIDA, completion_note='ok')
        self.assertEqual(self.api.get(f'/api/tasks/{self.first.id}/').data['blocking'], [])

    def test_cycles_and_self_dependency_are_rejected(self):
        self.assertEqual(self.patch(self.first, depends_on=self.first.id).status_code, 400)
        self.assertEqual(self.patch(self.first, depends_on=self.second.id).status_code, 400)

    def test_dependency_from_another_project_is_rejected(self):
        other = Task.objects.create(project=Project.objects.create(name='P2'), title='X', role='Dev')
        self.assertEqual(self.patch(self.second, depends_on=other.id).status_code, 400)

    def test_removing_dependency_unblocks(self):
        self.assertEqual(self.patch(self.second, depends_on=None).status_code, 200)
        self.assertEqual(self.patch(self.second, status=Status.EM_ANDAMENTO).status_code, 200)

    def test_checking_a_step_does_not_start_a_blocked_task(self):
        step = Subtask.objects.create(task=self.second, title='a')
        client_for(self.member).patch(f'/api/subtasks/{step.id}/', {'done': True}, format='json')
        self.second.refresh_from_db()
        self.assertEqual(self.second.status, Status.PENDENTE)

    def test_bulk_update_skips_blocked_tasks(self):
        free = Task.objects.create(project=self.project, title='Livre', role='Dev')
        response = self.api.post(
            '/api/tasks/bulk_update/',
            {'ids': [self.second.id, free.id], 'fields': {'status': Status.EM_ANDAMENTO}}, format='json',
        )
        self.assertEqual(response.data['updated'], [free.id])
        self.assertEqual(response.data['blocked'], [self.second.code])

    def test_completing_the_dependency_dms_the_waiting_assignee(self):
        with mock.patch('tasks.signals.discord.send_task_reminder_dm') as dm:
            self.patch(self.first, status=Status.CONCLUIDA, completion_note='ok')
        dm.assert_called_once()
        self.assertEqual(dm.call_args.args[0].id, self.second.id)
        self.assertEqual(dm.call_args.args[3], 'unblocked')


class PendingReminderTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='P1')
        self.person = Person(project=self.project, name='Ana', discord_id='123')
        self.person.set_password('x')
        self.person.save()
        old = timezone.now() - timedelta(days=3)
        self.pending = Task.objects.create(project=self.project, title='Parada', role='Dev', assignee=self.person)
        Task.objects.filter(pk=self.pending.pk).update(status_changed_at=old)

    def run_reminders(self):
        with mock.patch('tasks.management.commands.send_discord_reminders.d') as d:
            call_command('send_discord_reminders', stdout=StringIO())
        return [c.args[0].id for c in d.send_task_reminder_dm.call_args_list if c.args[3] == 'pending_reminder']

    def test_nudges_a_stale_pending_task_when_nothing_is_in_progress(self):
        self.assertEqual(self.run_reminders(), [self.pending.id])

    def test_stays_quiet_while_the_person_has_a_task_in_progress(self):
        Task.objects.create(project=self.project, title='Ativa', role='Dev', assignee=self.person, status=Status.EM_ANDAMENTO)
        self.assertEqual(self.run_reminders(), [])
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.pending_reminder_sent)  # can still fire later

    def test_stays_quiet_while_the_task_is_blocked(self):
        blocker = Task.objects.create(project=self.project, title='Antes', role='Dev')
        self.pending.depends_on = blocker
        self.pending.save()
        Task.objects.filter(pk=self.pending.pk).update(status_changed_at=timezone.now() - timedelta(days=3))
        self.assertEqual(self.run_reminders(), [])
