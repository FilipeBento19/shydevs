import tempfile
import os
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Activity, Comment, Person, Project, Subtask, Task


class DiscordVerificationApiTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name='Projeto Discord')
        self.person = Person.objects.create(project=self.project, name='Clayton')
        self.admin = Person.objects.create(project=self.project, name='Admin', is_admin=True)

    def test_person_can_verify_discord_by_sending_generated_code(self):
        self.client.force_authenticate(user=self.person)
        start = self.client.post(reverse('person-discord-verification', args=[self.person.id]), format='json')
        self.assertEqual(start.status_code, status.HTTP_200_OK)
        self.assertTrue(start.data['code'].startswith('SHY-'))

        self.client.force_authenticate(user=None)
        with patch.dict(os.environ, {'DISCORD_INCOMING_SECRET': 'segredo'}), patch(
            'tasks.views.discord.send_verification_confirmation_dm', return_value=True,
        ):
            incoming = self.client.post(
                '/api/discord/incoming/',
                {'secret': 'segredo', 'discord_id': '123456789', 'content': start.data['code']},
                format='json',
            )

        self.assertEqual(incoming.status_code, status.HTTP_200_OK)
        self.person.refresh_from_db()
        self.assertEqual(self.person.discord_id, '123456789')
        self.assertIsNotNone(self.person.discord_verified_at)
        self.assertEqual(self.person.discord_verification_code, '')

    def test_failed_confirmation_does_not_mark_person_as_verified(self):
        self.client.force_authenticate(user=self.person)
        start = self.client.post(reverse('person-discord-verification', args=[self.person.id]), format='json')
        self.client.force_authenticate(user=None)
        with patch.dict(os.environ, {'DISCORD_INCOMING_SECRET': 'segredo'}), patch(
            'tasks.views.discord.send_verification_confirmation_dm', return_value=False,
        ):
            incoming = self.client.post(
                '/api/discord/incoming/',
                {'secret': 'segredo', 'discord_id': '123456789', 'content': start.data['code']},
                format='json',
            )

        self.assertEqual(incoming.status_code, status.HTTP_409_CONFLICT)
        self.person.refresh_from_db()
        self.assertIsNone(self.person.discord_verified_at)

    def test_admin_cannot_start_verification_for_another_person(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse('person-discord-verification', args=[self.person.id]), format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manual_discord_id_change_removes_dm_verification(self):
        self.person.discord_id = '111'
        self.person.discord_verified_at = timezone.now()
        self.person.save(update_fields=['discord_id', 'discord_verified_at'])
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            reverse('person-detail', args=[self.person.id]), {'discord_id': '222'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['discord_id'], '222')
        self.assertFalse(response.data['discord_verified'])


class CommentApiTests(APITestCase):
    def setUp(self):
        self.author = Person.objects.create(name='Autor')
        self.other_person = Person.objects.create(name='Outra pessoa')
        self.admin = Person.objects.create(name='Admin', is_admin=True)
        self.task = Task.objects.create(title='Tarefa comentada', role='Scripter')
        self.list_url = reverse('comment-list')

    def test_logged_person_can_create_and_list_comment_for_task(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            self.list_url,
            {'task': self.task.id, 'body': '  Preciso revisar este ponto.  '},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['body'], 'Preciso revisar este ponto.')
        self.assertEqual(response.data['author'], self.author.id)

        response = self.client.get(self.list_url, {'task': self.task.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['author_name'], self.author.name)

    def test_person_cannot_delete_someone_elses_comment(self):
        comment = Comment.objects.create(task=self.task, author=self.author, body='Comentário')
        self.client.force_authenticate(user=self.other_person)

        response = self.client.delete(reverse('comment-detail', args=[comment.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Comment.objects.filter(id=comment.id).exists())

    def test_admin_can_delete_any_comment(self):
        comment = Comment.objects.create(task=self.task, author=self.author, body='Comentário')
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(reverse('comment-detail', args=[comment.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())

    def test_anonymous_person_cannot_read_comments(self):
        response = self.client.get(self.list_url, {'task': self.task.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_workload_includes_absolute_profile_photo_url(self):
        self.author.photo = 'avatars/tutu.png'
        self.author.save(update_fields=['photo'])
        self.task.assignee = self.author
        self.task.save(update_fields=['assignee'])
        self.client.force_authenticate(user=self.author)

        response = self.client.get(reverse('task-dashboard'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        author_workload = next(person for person in response.data['workload'] if person['name'] == self.author.name)
        self.assertTrue(author_workload['photo'].endswith('/media/avatars/tutu.png'))

    def test_anonymous_person_cannot_access_dashboard(self):
        response = self.client.get(reverse('task-dashboard'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_owner_can_toggle_own_checklist_item(self):
        self.task.assignee = self.author
        self.task.save(update_fields=['assignee'])
        subtask = Subtask.objects.create(task=self.task, title='Revisar entrega')
        self.client.force_authenticate(user=self.author)

        response = self.client.patch(reverse('subtask-detail', args=[subtask.id]), {'done': True}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subtask.refresh_from_db()
        self.assertTrue(subtask.done)

    def test_task_owner_cannot_change_checklist_item_text(self):
        self.task.assignee = self.author
        self.task.save(update_fields=['assignee'])
        subtask = Subtask.objects.create(task=self.task, title='Texto original')
        self.client.force_authenticate(user=self.author)

        response = self.client.patch(reverse('subtask-detail', args=[subtask.id]), {'title': 'Alterado'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        subtask.refresh_from_db()
        self.assertEqual(subtask.title, 'Texto original')

    def test_other_person_cannot_toggle_someone_elses_checklist_item(self):
        self.task.assignee = self.author
        self.task.save(update_fields=['assignee'])
        subtask = Subtask.objects.create(task=self.task, title='Etapa protegida')
        self.client.force_authenticate(user=self.other_person)

        response = self.client.patch(reverse('subtask-detail', args=[subtask.id]), {'done': True}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        subtask.refresh_from_db()
        self.assertFalse(subtask.done)


class AttachmentApiTests(APITestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.person = Person.objects.create(name='Pessoa com arquivo')
        self.task = Task.objects.create(title='Tarefa com arquivo', role='Scripter')
        self.client.force_authenticate(user=self.person)

    def test_upload_accepts_any_file_without_attachment_type(self):
        uploaded = SimpleUploadedFile(
            'material.custom',
            b'conteudo de teste',
            content_type='application/octet-stream',
        )

        response = self.client.post(
            reverse('attachment-list'),
            {'task': self.task.id, 'caption': 'Material da entrega', 'file': uploaded},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['kind'], 'file')
        self.assertEqual(response.data['caption'], 'Material da entrega')
        self.assertTrue(response.data['file_name'].endswith('.custom'))

    def test_upload_requires_a_file(self):
        response = self.client.post(
            reverse('attachment-list'),
            {'task': self.task.id, 'caption': 'Sem arquivo'},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ActivityApiTests(APITestCase):
    def setUp(self):
        self.person = Person.objects.create(name='Pessoa comum')
        self.admin = Person.objects.create(name='Administrador', is_admin=True)
        self.task = Task.objects.create(title='Evento testado', role='Scripter', assignee=self.person)
        Activity.objects.create(
            task=self.task, actor=self.person, message='Evento restrito',
            event_type=Activity.EventType.TASK_UPDATED,
            visibility=Activity.Visibility.ADMIN,
            details={'prioridade': {'antes': 'Baixa', 'depois': 'Alta'}},
        )

    def test_normal_history_only_returns_public_events(self):
        self.client.force_authenticate(user=self.person)

        response = self.client.get(reverse('activity-list'), {'scope': 'normal'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data)
        self.assertTrue(all(item['visibility'] == 'public' for item in response.data))

    def test_regular_user_cannot_access_admin_history(self):
        self.client.force_authenticate(user=self.person)

        response = self.client.get(reverse('activity-list'), {'scope': 'admin'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_history_contains_detailed_restricted_events(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(reverse('activity-list'), {'scope': 'admin'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        restricted = next(item for item in response.data if item['message'] == 'Evento restrito')
        self.assertEqual(restricted['details']['prioridade']['depois'], 'Alta')
