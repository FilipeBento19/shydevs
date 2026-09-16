from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from . import discord
from .models import Activity, Attachment, Status, Subtask, Task


def actor_name(actor):
    return actor.name if actor else 'Sistema'


def display(value):
    return 'Não informado' if value is None or value == '' else str(value)


@receiver(pre_save, sender=Task)
def stash_previous_task(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous = None
        return
    previous = Task.objects.select_related('assignee').filter(pk=instance.pk).first()
    instance._previous = previous
    if not previous:
        return
    if previous.due_date != instance.due_date:
        instance.overdue_notified = False
        instance.due_soon_notified = False
    if previous.status != instance.status:
        instance.status_changed_at = timezone.now()
        instance.pending_reminder_sent = False
        instance.in_progress_reminder_sent = False


@receiver(post_save, sender=Task)
def log_task_activity(sender, instance, created, **kwargs):
    actor = getattr(instance, '_activity_actor', None)
    who = actor_name(actor)
    assignee = instance.assignee.name if instance.assignee_id else 'ninguém'

    if created:
        Activity.objects.create(
            task=instance, actor=actor,
            event_type=Activity.EventType.TASK_CREATED,
            visibility=Activity.Visibility.PUBLIC,
            message=f'{who} criou a tarefa {instance.code} · {instance.title} para {assignee}.',
            details={'responsável': assignee, 'cargo': instance.role, 'prioridade': instance.priority,
                     'prazo': display(instance.due_date), 'status': instance.status},
        )
        return

    previous = getattr(instance, '_previous', None)
    if not previous:
        return

    if previous.status != instance.status:
        completed = instance.status == Status.CONCLUIDA
        Activity.objects.create(
            task=instance, actor=actor,
            event_type=Activity.EventType.TASK_COMPLETED if completed else Activity.EventType.TASK_STATUS,
            visibility=Activity.Visibility.PUBLIC if completed else Activity.Visibility.ADMIN,
            message=(f'{who} concluiu a tarefa {instance.code} · {instance.title}.' if completed
                     else f'{who} alterou o status de {instance.code}: {previous.status} → {instance.status}.'),
            details={'antes': previous.status, 'depois': instance.status},
        )

    if previous.assignee_id != instance.assignee_id:
        old_name = previous.assignee.name if previous.assignee_id else 'ninguém'
        Activity.objects.create(
            task=instance, actor=actor,
            event_type=Activity.EventType.TASK_ASSIGNED,
            visibility=Activity.Visibility.PUBLIC,
            message=f'{who} atribuiu a tarefa {instance.code} · {instance.title} para {assignee}.',
            details={'antes': old_name, 'depois': assignee},
        )

    tracked = {'title': 'título', 'description': 'descrição', 'role': 'cargo', 'due_date': 'prazo',
               'priority': 'prioridade', 'checked': 'marcação', 'completion_note': 'nota de conclusão'}
    changes = {}
    for field, label in tracked.items():
        before, after = getattr(previous, field), getattr(instance, field)
        if before != after:
            changes[label] = {'antes': display(before), 'depois': display(after)}
    if changes:
        Activity.objects.create(
            task=instance, actor=actor,
            event_type=Activity.EventType.TASK_UPDATED,
            visibility=Activity.Visibility.ADMIN,
            message=f'{who} atualizou {len(changes)} campo(s) de {instance.code} · {instance.title}.',
            details={'alterações': changes},
        )


@receiver(pre_save, sender=Subtask)
def stash_previous_subtask(sender, instance, **kwargs):
    instance._previous = Subtask.objects.filter(pk=instance.pk).first() if instance.pk else None


@receiver(post_save, sender=Subtask)
def log_subtask_activity(sender, instance, created, **kwargs):
    actor = getattr(instance, '_activity_actor', None)
    previous = getattr(instance, '_previous', None)
    if not created and previous and previous.done == instance.done and previous.title == instance.title:
        return
    action = 'adicionou' if created else 'marcou' if instance.done else 'desmarcou'
    Activity.objects.create(
        task=instance.task, actor=actor,
        event_type=Activity.EventType.CHECKLIST,
        visibility=Activity.Visibility.ADMIN,
        message=f'{actor_name(actor)} {action} a etapa “{instance.title}” em {instance.task.code}.',
        details={'etapa': instance.title, 'concluída': instance.done},
    )


@receiver(post_delete, sender=Subtask)
def log_deleted_subtask(sender, instance, origin=None, **kwargs):
    if isinstance(origin, Task):
        return
    actor = getattr(instance, '_activity_actor', None)
    if not actor:
        return
    Activity.objects.create(
        task=instance.task, actor=actor,
        event_type=Activity.EventType.CHECKLIST,
        visibility=Activity.Visibility.ADMIN,
        message=f'{actor_name(actor)} removeu a etapa “{instance.title}” de {instance.task.code}.',
        details={'etapa removida': instance.title},
    )


@receiver(post_save, sender=Attachment)
def log_attachment_activity(sender, instance, created, **kwargs):
    if not created:
        return
    name = instance.file.name.rsplit('/', 1)[-1] if instance.file else instance.url
    Activity.objects.create(
        task=instance.task, actor=instance.uploaded_by,
        event_type=Activity.EventType.ATTACHMENT,
        visibility=Activity.Visibility.ADMIN,
        message=f'{actor_name(instance.uploaded_by)} anexou “{instance.caption or name}” em {instance.task.code}.',
        details={'arquivo': name, 'legenda': instance.caption or 'Sem legenda'},
    )


@receiver(post_save, sender=Activity)
def notify_discord_on_activity(sender, instance, created, **kwargs):
    if created:
        discord.notify(instance)


@receiver(post_delete, sender=Attachment)
def log_deleted_attachment(sender, instance, origin=None, **kwargs):
    if isinstance(origin, Task):
        return
    actor = getattr(instance, '_activity_actor', None)
    if not actor:
        return
    name = instance.file.name.rsplit('/', 1)[-1] if instance.file else instance.url
    Activity.objects.create(
        task=instance.task, actor=actor,
        event_type=Activity.EventType.ATTACHMENT,
        visibility=Activity.Visibility.ADMIN,
        message=f'{actor_name(actor)} removeu o arquivo “{instance.caption or name}” de {instance.task.code}.',
        details={'arquivo removido': name},
    )
