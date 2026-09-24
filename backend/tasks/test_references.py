import tempfile
from unittest import mock

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import AuthToken, Person, Project, Reference, Task
from .storages import kind_for_name


def make_person(project, name, is_admin=False):
    person = Person(project=project, name=name, is_admin=is_admin)
    person.set_password('x')
    person.save()
    AuthToken.objects.create(person=person, key=f'token-{name}')
    return person


def client_for(person):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token token-{person.name}')
    return client


class KindForNameTests(TestCase):
    def test_extension_decides_kind(self):
        self.assertEqual(kind_for_name('a/b/PIC.PNG'), 'image')
        self.assertEqual(kind_for_name('clip.mp4'), 'video')
        self.assertEqual(kind_for_name('https://x.com/v.webm?token=1'), 'video')
        self.assertEqual(kind_for_name('notes.zip'), 'file')
        self.assertEqual(kind_for_name('noext'), 'file')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ReferenceApiTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='P1')
        self.other_project = Project.objects.create(name='P2')
        self.admin = make_person(self.project, 'admin', is_admin=True)
        self.member = make_person(self.project, 'member')
        self.outsider = make_person(self.other_project, 'outsider', is_admin=True)
        self.task = Task.objects.create(project=self.project, title='T', role='Dev')
        self.foreign_task = Task.objects.create(project=self.other_project, title='F', role='Dev')

    def post(self, person, **data):
        return client_for(person).post('/api/references/', {'task': self.task.id, **data}, format='multipart')

    def test_upload_file_detects_kind_and_defaults_group(self):
        res = self.post(self.member, file=SimpleUploadedFile('shot.png', b'\x89PNG', content_type='image/png'))
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['kind'], 'image')
        self.assertEqual(res.data['group'], 'Geral')
        self.assertEqual(res.data['uploaded_by_name'], 'member')

    def test_video_file_and_group_name(self):
        res = self.post(self.admin, group='  Skill 1 ', file=SimpleUploadedFile('c.mp4', b'00', content_type='video/mp4'))
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['kind'], 'video')
        self.assertEqual(res.data['group'], 'Skill 1')

    def test_links_are_classified(self):
        cases = {
            'https://cdn.x.com/a.webm': 'video',
            'https://cdn.x.com/a.jpg': 'image',
            'https://www.youtube.com/watch?v=abc': 'link',
            'https://docs.google.com/document/d/1': 'link',
        }
        for url, kind in cases.items():
            res = self.post(self.member, url=url)
            self.assertEqual(res.status_code, 201, res.content)
            self.assertEqual(res.data['kind'], kind, url)

    def test_needs_file_or_link(self):
        self.assertEqual(self.post(self.member, group='Skill 1').status_code, 400)
        self.assertEqual(self.post(self.member, url='   ').status_code, 400)

    def test_anonymous_cannot_add_but_can_read(self):
        anon = APIClient()
        res = anon.post('/api/references/', {'task': self.task.id, 'url': 'https://a.com'}, format='multipart')
        self.assertIn(res.status_code, (401, 403))
        Reference.objects.create(task=self.task, kind='link', url='https://a.com', group='G')
        res = anon.get(f'/api/references/?task={self.task.id}&project={self.project.id}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_cannot_add_to_another_projects_task(self):
        res = client_for(self.outsider).post(
            '/api/references/', {'task': self.task.id, 'url': 'https://a.com'}, format='multipart')
        self.assertEqual(res.status_code, 403)
        res = client_for(self.member).post(
            '/api/references/', {'task': self.foreign_task.id, 'url': 'https://a.com'}, format='multipart')
        self.assertEqual(res.status_code, 403)

    def test_listing_is_scoped_to_own_project_and_task(self):
        Reference.objects.create(task=self.task, kind='link', url='https://a.com', group='G')
        Reference.objects.create(task=self.foreign_task, kind='link', url='https://b.com', group='G')
        res = client_for(self.member).get('/api/references/')
        self.assertEqual([r['url'] for r in res.data], ['https://a.com'])
        res = client_for(self.member).get(f'/api/references/?task={self.foreign_task.id}')
        self.assertEqual(res.data, [])

    def test_only_uploader_or_admin_can_delete(self):
        ref = Reference.objects.create(task=self.task, kind='link', url='https://a.com', group='G', uploaded_by=self.member)
        other = make_person(self.project, 'other')
        self.assertEqual(client_for(other).delete(f'/api/references/{ref.id}/').status_code, 403)
        self.assertEqual(client_for(self.member).delete(f'/api/references/{ref.id}/').status_code, 204)
        ref2 = Reference.objects.create(task=self.task, kind='link', url='https://a.com', group='G', uploaded_by=self.member)
        self.assertEqual(client_for(self.admin).delete(f'/api/references/{ref2.id}/').status_code, 204)

    def test_task_reports_references_total(self):
        Reference.objects.create(task=self.task, kind='link', url='https://a.com', group='G')
        Reference.objects.create(task=self.task, kind='link', url='https://b.com', group='H')
        res = client_for(self.member).get(f'/api/tasks/{self.task.id}/')
        self.assertEqual(res.data['references_total'], 2)


class CloudinaryStorageTests(TestCase):
    """The real Cloudinary calls are mocked — this pins down the naming/
    resource-type logic that decides whether a video or zip is findable again."""

    def storage(self):
        from .storages import _build_cloudinary_storage
        # cloudinary_storage refuses to even import without credentials.
        with mock.patch.dict('os.environ', {'CLOUDINARY_URL': 'cloudinary://key:secret@cloud'}):
            return _build_cloudinary_storage()

    def test_upload_resource_type_and_extension_preserved(self):
        storage = self.storage()
        cases = [
            ('references/clip.mp4', 'video', 'references/clip_ab', 'references/clip_ab.mp4'),
            ('references/pic.PNG', 'image', 'references/pic_ab', 'references/pic_ab.png'),
            ('references/notes.zip', 'raw', 'references/notes_ab.zip', 'references/notes_ab.zip'),
        ]
        for name, resource_type, public_id, stored in cases:
            with mock.patch('cloudinary.uploader.upload', return_value={'public_id': public_id}) as upload:
                self.assertEqual(storage._save(name, ContentFile(b'x')), stored)
                self.assertEqual(upload.call_args.kwargs['resource_type'], resource_type)

    def test_url_uses_matching_resource_type(self):
        storage = self.storage()
        with mock.patch('cloudinary.CloudinaryResource') as resource:
            resource.return_value.url = 'https://res/x'
            storage.url('references/clip_ab.mp4')
            self.assertEqual(resource.call_args.kwargs['default_resource_type'], 'video')
            storage.url('references/notes_ab.zip')
            self.assertEqual(resource.call_args.kwargs['default_resource_type'], 'raw')

    def test_delete_strips_extension_except_for_raw(self):
        storage = self.storage()
        with mock.patch('cloudinary.uploader.destroy', return_value={'result': 'ok'}) as destroy:
            storage.delete('references/clip_ab.mp4')
            self.assertEqual(destroy.call_args.args[0], 'references/clip_ab')
            self.assertEqual(destroy.call_args.kwargs['resource_type'], 'video')
            storage.delete('references/notes_ab.zip')
            self.assertEqual(destroy.call_args.args[0], 'references/notes_ab.zip')
            self.assertEqual(destroy.call_args.kwargs['resource_type'], 'raw')

    def test_falls_back_to_default_storage_without_cloudinary(self):
        from django.core.files.storage import default_storage
        from .storages import get_reference_storage
        with override_settings(USE_CLOUDINARY=False):
            self.assertIs(get_reference_storage(), default_storage)
