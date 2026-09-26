from django.test import TestCase

from .models import Project, Status, Subtask, Task
from .test_references import client_for, make_person


class GroupChecklistTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='P1')
        self.admin = make_person(self.project, 'admin', is_admin=True)
        self.ana = make_person(self.project, 'ana')
        self.bia = make_person(self.project, 'bia')
        self.task = Task.objects.create(project=self.project, title='Grupo', role='Dev', kind='group', assignee=self.ana)
        self.task.participants.set([self.ana, self.bia])
        self.s1 = Subtask.objects.create(task=self.task, title='Um')
        self.s2 = Subtask.objects.create(task=self.task, title='Dois')

    def tick(self, who, step, done=True):
        return client_for(who).patch(f'/api/subtasks/{step.id}/', {'done': done}, format='json')

    def test_a_step_is_only_done_when_everyone_did_it(self):
        response = self.tick(self.ana, self.s1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['done_by'], [self.ana.id])
        self.assertTrue(response.data['my_done'])
        self.assertFalse(response.data['done'])
        self.assertTrue(self.tick(self.bia, self.s1).data['done'])

    def test_each_person_only_ticks_for_themselves(self):
        self.tick(self.ana, self.s1)
        bia_view = client_for(self.bia).get(f'/api/subtasks/{self.s1.id}/').data
        self.assertFalse(bia_view['my_done'])
        self.assertEqual(bia_view['done_by'], [self.ana.id])

    def test_unticking_reopens_the_step_for_everyone(self):
        self.tick(self.ana, self.s1)
        self.tick(self.bia, self.s1)
        self.assertFalse(self.tick(self.bia, self.s1, done=False).data['done'])
        self.s1.refresh_from_db()
        self.assertFalse(self.s1.done)

    def test_admin_outside_the_group_ticks_for_everyone(self):
        self.assertTrue(self.tick(self.admin, self.s1).data['done'])
        self.assertEqual(sorted(client_for(self.admin).get(f'/api/subtasks/{self.s1.id}/').data['done_by']), sorted([self.ana.id, self.bia.id]))

    def test_outsiders_cannot_tick(self):
        outsider = make_person(self.project, 'caio')
        self.assertEqual(self.tick(outsider, self.s1).status_code, 403)

    def test_first_tick_starts_a_pending_task(self):
        self.tick(self.ana, self.s1)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Status.EM_ANDAMENTO)

    def test_progress_per_person_is_reported(self):
        self.tick(self.ana, self.s1)
        self.tick(self.ana, self.s2)
        self.tick(self.bia, self.s1)
        rows = {r['name']: (r['done'], r['total']) for r in client_for(self.admin).get(f'/api/tasks/{self.task.id}/').data['participants_progress']}
        self.assertEqual(rows, {'ana': (2, 2), 'bia': (1, 2)})

    def test_adding_a_person_reopens_finished_steps(self):
        self.tick(self.ana, self.s1)
        self.tick(self.bia, self.s1)
        caio = make_person(self.project, 'caio')
        client_for(self.admin).patch(f'/api/tasks/{self.task.id}/', {'participants': [self.ana.id, self.bia.id, caio.id]}, format='json')
        self.s1.refresh_from_db()
        self.assertFalse(self.s1.done)

    def test_solo_to_group_keeps_credit_for_the_lead(self):
        solo = Task.objects.create(project=self.project, title='Solo', role='Dev', assignee=self.ana)
        step = Subtask.objects.create(task=solo, title='Feita', done=True)
        client_for(self.admin).patch(
            f'/api/tasks/{solo.id}/', {'kind': 'group', 'participants': [self.ana.id, self.bia.id]}, format='json',
        )
        step.refresh_from_db()
        self.assertFalse(step.done)  # bia still has to do it
        self.assertEqual([c.person_id for c in step.completions.all()], [self.ana.id])

    def test_solo_checklist_is_unchanged(self):
        solo = Task.objects.create(project=self.project, title='Solo', role='Dev', assignee=self.ana)
        step = Subtask.objects.create(task=solo, title='X')
        self.assertTrue(self.tick(self.ana, step).data['done'])


class TurnOrderTests(TestCase):
    """animator -> scripter -> vfx: nobody ticks a step before the person ahead of them."""

    def setUp(self):
        self.project = Project.objects.create(name='P1')
        self.admin = make_person(self.project, 'admin', is_admin=True)
        self.anim = make_person(self.project, 'anim')
        self.script = make_person(self.project, 'script')
        self.vfx = make_person(self.project, 'vfx')
        for p in (self.script, self.vfx):
            p.discord_id = f'id-{p.name}'
            p.save()
        self.task = Task.objects.create(project=self.project, title='Skill', role='Dev', kind='group', assignee=self.anim)
        self.task.participants.set([self.anim, self.script, self.vfx])
        self.step = Subtask.objects.create(task=self.task, title='Fazer')
        self.api = client_for(self.admin)
        self.set_order([self.anim.id, self.script.id, self.vfx.id])

    def set_order(self, ids):
        return self.api.patch(f'/api/tasks/{self.task.id}/', {'participant_order': ids}, format='json')

    def tick(self, who, done=True):
        return client_for(who).patch(f'/api/subtasks/{self.step.id}/', {'done': done}, format='json')

    def test_order_is_saved_and_reported(self):
        data = self.api.get(f'/api/tasks/{self.task.id}/').data
        self.assertEqual(data['participant_order'], [self.anim.id, self.script.id, self.vfx.id])
        self.assertEqual([p['name'] for p in data['participants_info']], ['anim', 'script', 'vfx'])

    def test_cannot_tick_before_the_person_ahead(self):
        self.assertEqual(self.tick(self.script).status_code, 403)
        self.assertEqual(self.tick(self.vfx).status_code, 403)
        self.assertEqual(self.tick(self.anim).status_code, 200)
        self.assertEqual(self.tick(self.vfx).status_code, 403)  # still waiting on the scripter
        self.assertEqual(self.tick(self.script).status_code, 200)
        self.assertTrue(self.tick(self.vfx).data['done'])

    def test_cannot_untick_while_someone_behind_has_done_it(self):
        self.tick(self.anim)
        self.tick(self.script)
        self.assertEqual(self.tick(self.anim, done=False).status_code, 403)
        self.tick(self.script, done=False)
        self.assertEqual(self.tick(self.anim, done=False).status_code, 200)

    def test_next_person_gets_a_dm_when_the_one_before_finishes(self):
        from unittest import mock
        with mock.patch('tasks.views.discord.send_task_reminder_dm') as dm:
            self.tick(self.anim)
        dm.assert_called_once()
        self.assertEqual(dm.call_args.kwargs['person'].id, self.script.id)
        self.assertEqual(dm.call_args.args[3], 'your_turn')

    def test_no_order_means_everyone_at_once(self):
        self.set_order([])
        self.assertEqual(self.tick(self.vfx).status_code, 200)

    def test_order_with_a_stranger_is_rejected(self):
        outsider = make_person(self.project, 'x')
        self.assertEqual(self.set_order([self.anim.id, outsider.id]).status_code, 400)

    def test_order_follows_group_membership(self):
        self.api.patch(f'/api/tasks/{self.task.id}/', {'participants': [self.anim.id, self.script.id]}, format='json')
        self.task.refresh_from_db()
        self.assertEqual(self.task.participant_order, [self.anim.id, self.script.id])
