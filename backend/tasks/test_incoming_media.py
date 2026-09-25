import tempfile
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import DiscordAttachment, DiscordMessage, Person, Project
from .test_references import client_for, make_person


class FakeResponse:
    headers = {'Content-Type': 'image/png'}

    def __init__(self, data=b'\x89PNG-fake'):
        self.data = data

    def raise_for_status(self):
        pass

    def iter_content(self, size):
        yield self.data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class IncomingMediaTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='P1')
        self.admin = make_person(self.project, 'admin', is_admin=True)
        self.admin.discord_id = '42'
        self.admin.save()
        self.env = mock.patch.dict('os.environ', {'DISCORD_INCOMING_SECRET': 's3cret'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def post(self, **extra):
        body = {'secret': 's3cret', 'discord_id': '42', 'content': '', **extra}
        return APIClient().post('/api/discord/incoming/', body, format='json')

    def test_media_only_dm_is_stored_and_listed(self):
        media = [{'url': 'https://cdn.discordapp.com/attachments/1/2/foto.png', 'filename': 'foto.png', 'content_type': 'image/png'}]
        with mock.patch('tasks.incoming_media.requests.get', return_value=FakeResponse()):
            self.assertEqual(self.post(attachments=media).status_code, 204)
        att = DiscordAttachment.objects.get()
        self.assertEqual((att.kind, att.name, bool(att.file)), ('image', 'foto.png', True))
        feed = client_for(self.admin).get('/api/discord-messages/').data
        self.assertEqual(len(feed[0]['attachments']), 1)
        self.assertEqual(feed[0]['attachments'][0]['kind'], 'image')
        self.assertTrue(feed[0]['attachments'][0]['url'].endswith('.png'))

    def test_gif_embed_becomes_a_looping_video(self):
        media = [{'url': 'https://media.tenor.com/abc/clip.mp4', 'filename': '', 'content_type': '', 'gif': True}]
        with mock.patch('tasks.incoming_media.requests.get', return_value=FakeResponse(b'mp4')):
            self.post(content='https://tenor.com/view/x', attachments=media)
        att = DiscordAttachment.objects.get()
        self.assertEqual((att.kind, att.is_gif), ('video', True))

    def test_failed_download_keeps_the_original_link(self):
        import requests
        media = [{'url': 'https://cdn.discordapp.com/a/b/c.mp4', 'filename': 'c.mp4'}]
        with mock.patch('tasks.incoming_media.requests.get', side_effect=requests.ConnectionError()):
            self.post(attachments=media)
        att = DiscordAttachment.objects.get()
        self.assertFalse(att.file)
        self.assertEqual(att.source_url, media[0]['url'])

    def test_links_to_other_hosts_are_ignored(self):
        with mock.patch('tasks.incoming_media.requests.get') as get:
            self.post(content='oi', attachments=[{'url': 'https://evil.example/x.png'}, {'url': 'http://cdn.discordapp.com/x.png'}])
        get.assert_not_called()
        self.assertEqual(DiscordAttachment.objects.count(), 0)
        self.assertEqual(DiscordMessage.objects.count(), 1)

    def test_empty_dm_without_media_is_rejected(self):
        self.assertEqual(self.post().status_code, 400)
