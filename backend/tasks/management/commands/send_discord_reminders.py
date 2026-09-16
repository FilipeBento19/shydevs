from datetime import timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from tasks import discord as d
from tasks.models import Person, Status, Task

PENDING_AFTER = timedelta(hours=24)
IN_PROGRESS_AFTER = timedelta(hours=48)
DIGEST_INTERVAL = timedelta(days=2)
DIGEST_HOUR_BRASILIA = 8
BRASILIA = ZoneInfo('America/Sao_Paulo')


class Command(BaseCommand):
    help = (
        'Sends the DM-only reminder nudges the Discord webhook does not cover: a task '
        'stuck in Pendente too long, one stuck in Em andamento too long, a due-tomorrow '
        'heads up, and a periodic personal workload digest (sent once the run lands in '
        'the 8am Brasilia hour). Safe to run repeatedly, e.g. hourly via a cron pinger.'
    )

    def handle(self, *args, **options):
        now = timezone.now()
        today = now.date()
        counts = {'pending': 0, 'in_progress': 0, 'due_soon': 0, 'digest': 0}

        pending = (
            Task.objects.select_related('assignee')
            .filter(status=Status.PENDENTE, pending_reminder_sent=False, status_changed_at__lte=now - PENDING_AFTER)
            .exclude(assignee__isnull=True).exclude(assignee__discord_id='')
        )
        for task in pending:
            d.send_task_reminder_dm(
                task, 'Ainda não começou?',
                f'{task.assignee.name}, essa tarefa está esperando você desde {task.status_changed_at.strftime("%d/%m")}. '
                'Bora dar o primeiro passo?',
            )
            task.pending_reminder_sent = True
            task.save(update_fields=['pending_reminder_sent'])
            counts['pending'] += 1

        in_progress = (
            Task.objects.select_related('assignee')
            .filter(status=Status.EM_ANDAMENTO, in_progress_reminder_sent=False, status_changed_at__lte=now - IN_PROGRESS_AFTER)
            .exclude(assignee__isnull=True).exclude(assignee__discord_id='')
        )
        for task in in_progress:
            d.send_task_reminder_dm(
                task, 'Como está o andamento?',
                f'{task.assignee.name}, já faz uns dias que essa tarefa está em andamento. '
                'Continue firme, ou avise se travou em algo.',
            )
            task.in_progress_reminder_sent = True
            task.save(update_fields=['in_progress_reminder_sent'])
            counts['in_progress'] += 1

        due_soon = (
            Task.objects.select_related('assignee')
            .filter(due_date=today + timedelta(days=1), due_soon_notified=False)
            .exclude(status=Status.CONCLUIDA).exclude(assignee__isnull=True).exclude(assignee__discord_id='')
        )
        for task in due_soon:
            d.send_task_reminder_dm(
                task, 'Prazo chegando',
                f'{task.assignee.name}, o prazo é amanhã ({task.due_date.strftime("%d/%m")}). '
                'Ainda dá tempo, mas não deixe para a última hora.',
            )
            task.due_soon_notified = True
            task.save(update_fields=['due_soon_notified'])
            counts['due_soon'] += 1

        if now.astimezone(BRASILIA).hour == DIGEST_HOUR_BRASILIA:
            people = Person.objects.exclude(discord_id='').filter(
                Q(last_digest_sent_at__isnull=True) | Q(last_digest_sent_at__lte=now - DIGEST_INTERVAL)
            )
            for person in people:
                tasks = Task.objects.filter(assignee=person)
                stats = {
                    'open': tasks.exclude(status=Status.CONCLUIDA).count(),
                    'in_progress': tasks.filter(status=Status.EM_ANDAMENTO).count(),
                    'overdue': tasks.filter(due_date__lt=today).exclude(status=Status.CONCLUIDA).count(),
                }
                d.send_digest_dm(person, stats)
                person.last_digest_sent_at = now
                person.save(update_fields=['last_digest_sent_at'])
                counts['digest'] += 1

        # Every send above happens on a background thread; a short-lived
        # `manage.py` process would otherwise exit and kill them mid-request.
        d.flush()

        self.stdout.write(self.style.SUCCESS(
            f"Pendente ha muito tempo: {counts['pending']} · Em andamento ha muito tempo: {counts['in_progress']} · "
            f"Prazo proximo: {counts['due_soon']} · Resumos enviados: {counts['digest']}"
        ))
