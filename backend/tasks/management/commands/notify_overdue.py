from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks import discord as d
from tasks.models import Activity, Status, Task


class Command(BaseCommand):
    help = (
        'Finds tasks past their due date that have not been flagged yet, logs an '
        '"overdue" Activity for each (which also posts to Discord if configured), '
        'and marks them so the next run does not repeat it. Meant to be triggered '
        'periodically — see the /api/cron/check-overdue/ endpoint for a webhook-free '
        'hosting setup with an external scheduler.'
    )

    def handle(self, *args, **options):
        today = timezone.now().date()
        overdue = (
            Task.objects.select_related('assignee')
            .filter(due_date__lt=today, overdue_notified=False)
            .exclude(status=Status.CONCLUIDA)
        )

        count = 0
        for task in overdue:
            assignee = task.assignee.name if task.assignee_id else 'ninguém'
            Activity.objects.create(
                task=task, actor=None,
                event_type=Activity.EventType.OVERDUE,
                visibility=Activity.Visibility.PUBLIC,
                message=f'{task.code} · {task.title} está atrasada (responsável: {assignee}).',
                details={'responsável': assignee, 'prazo': str(task.due_date)},
            )
            task.overdue_notified = True
            task.save(update_fields=['overdue_notified'])
            count += 1

        # The Activity save above triggers Discord notifications on a
        # background thread (see signals.py); a short-lived `manage.py`
        # process would otherwise exit and kill them mid-request.
        d.flush()

        self.stdout.write(self.style.SUCCESS(f'{count} tarefa(s) marcada(s) como atrasada(s).'))
