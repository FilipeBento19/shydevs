from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Comment, Person, Task


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
