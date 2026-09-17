from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from tasks.models import Person, Project


class UnverifiedDiscordReminderTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='Projeto de teste')
        Person.objects.create(
            project=self.project,
            name='Pessoa sem verificação',
            discord_id='123456789012345678',
        )

    @patch('tasks.discord.send_unverified_webhook', return_value=True)
    def test_first_run_sends_then_waits_one_day_unless_forced(self, send_webhook):
        call_command('send_discord_reminders', stdout=StringIO())
        self.assertEqual(send_webhook.call_count, 1)

        call_command('send_discord_reminders', stdout=StringIO())
        self.assertEqual(send_webhook.call_count, 1)

        call_command('send_discord_reminders', force_unverified=True, stdout=StringIO())
        self.assertEqual(send_webhook.call_count, 2)

