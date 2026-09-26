from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.utils import timezone

from django.test import TestCase

from .models import Project, Status, Task
from .test_references import client_for, make_person


class GroupTaskTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='P1')
        self.admin = make_person(self.project, 'admin', is_admin=True)
        self.ana = make_person(self.project, 'ana')
        self.bia = make_person(self.project, 'bia')
        self.caio = make_person(self.project, 'caio')
        for p in (self.ana, self.bia):
            p.discord_id = f'id-{p.name}'
            p.save()
        self.api = client_for(self.admin)

    def create(self, **extra):
        body = {'title': 'Trailer', 'role': 'Dev', 'kind': 'group', **extra}
        return self.api.post('/api/tasks/', body, format='json')

    def test_group_task_keeps_all_participants_and_a_lead(self):
        response = self.create(participants=[self.bia.id, self.ana.id])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['kind'], 'group')
        self.assertEqual(sorted(response.data['participants']), sorted([self.ana.id, self.bia.id]))
        self.assertEqual(response.data['assignee'], self.bia.id)  # first one is the lead
        self.assertEqual({p['name'] for p in response.data['participants_info']}, {'ana', 'bia'})

    def test_group_needs_at_least_two_people(self):
        self.assertEqual(self.create(participants=[self.ana.id]).status_code, 400)
        self.assertEqual(self.create().status_code, 400)

    def test_solo_task_ignores_participants(self):
        response = self.api.post('/api/tasks/', {
            'title': 'Solo', 'role': 'Dev', 'kind': 'solo', 'assignee': self.ana.id, 'participants': [self.bia.id],
        }, format='json')
        self.assertEqual(response.data['participants'], [])

    def test_every_participant_can_update_status_but_outsiders_cannot(self):
        task_id = self.create(participants=[self.ana.id, self.bia.id]).data['id']
        for member in (self.ana, self.bia):
            response = client_for(member).patch(f'/api/tasks/{task_id}/', {'status': Status.EM_ANDAMENTO}, format='json')
            self.assertEqual(response.status_code, 200, member.name)
        self.assertEqual(client_for(self.caio).patch(f'/api/tasks/{task_id}/', {'status': Status.PENDENTE}, format='json').status_code, 403)

    def test_switching_back_to_solo_clears_the_group(self):
        task_id = self.create(participants=[self.ana.id, self.bia.id]).data['id']
        response = self.api.patch(f'/api/tasks/{task_id}/', {'kind': 'solo', 'assignee': self.ana.id}, format='json')
        self.assertEqual(response.data['participants'], [])

    def test_workload_counts_group_tasks_for_everyone_in_them(self):
        self.create(participants=[self.ana.id, self.bia.id])
        rows = {r['name']: r['open'] for r in self.api.get('/api/tasks/dashboard/').data['workload']}
        self.assertEqual((rows['ana'], rows['bia'], rows['caio']), (1, 1, 0))

    def test_webhook_mentions_every_participant(self):
        with mock.patch.dict('os.environ', {'DISCORD_WEBHOOK_URL': 'https://hook.example/x'}), \
                mock.patch('tasks.discord._spawn') as spawn, \
                mock.patch('tasks.discord.build_container', return_value={}) as build:
            self.create(participants=[self.ana.id, self.bia.id])
        mention_lines = [c.args[1] for c in build.call_args_list if c.args[1]]
        self.assertTrue(any('<@id-ana>' in m and '<@id-bia>' in m for m in mention_lines), mention_lines)
        self.assertTrue(spawn.called)


class GroupReminderTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='P1')
        self.ana = make_person(self.project, 'ana')
        self.bia = make_person(self.project, 'bia')
        for p in (self.ana, self.bia):
            p.discord_id = f'id-{p.name}'
            p.save()
        self.task = Task.objects.create(project=self.project, title='Grupo', role='Dev', kind='group', assignee=self.ana)
        self.task.participants.set([self.ana, self.bia])
        Task.objects.filter(pk=self.task.pk).update(status_changed_at=timezone.now() - timedelta(days=3))

    def run_reminders(self):
        with mock.patch('tasks.management.commands.send_discord_reminders.d') as d:
            call_command('send_discord_reminders', stdout=StringIO())
        return sorted(c.kwargs['person'].name for c in d.send_task_reminder_dm.call_args_list if c.args[3] == 'pending_reminder')

    def test_each_participant_gets_the_pending_nudge(self):
        self.assertEqual(self.run_reminders(), ['ana', 'bia'])

    def test_busy_participant_is_skipped_but_the_other_is_not(self):
        Task.objects.create(project=self.project, title='Ativa', role='Dev', assignee=self.bia, status=Status.EM_ANDAMENTO)
        self.assertEqual(self.run_reminders(), ['ana'])

    def test_being_busy_in_a_group_task_also_counts(self):
        other = Task.objects.create(project=self.project, title='Outra', role='Dev', kind='group', assignee=self.ana, status=Status.EM_ANDAMENTO)
        other.participants.set([self.ana, self.bia])
        self.assertEqual(self.run_reminders(), [])


class DmSafetyNetTests(TestCase):
    def test_dms_limited_to_the_allowed_ids_when_configured(self):
        from unittest import mock
        from . import discord
        with mock.patch.dict('os.environ', {'DISCORD_DM_ONLY_IDS': '1, 2'}):
            self.assertTrue(discord._dm_allowed('2'))
            self.assertFalse(discord._dm_allowed('3'))
        with mock.patch.dict('os.environ', {'DISCORD_DM_ONLY_IDS': ''}):
            self.assertTrue(discord._dm_allowed('anyone'))
