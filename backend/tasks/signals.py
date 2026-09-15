from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Activity, Attachment, Task


@receiver(pre_save, sender=Task)
def _stash_previous_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous = None
        return
    try:
        instance._previous = Task.objects.get(pk=instance.pk)
    except Task.DoesNotExist:
        instance._previous = None


@receiver(post_save, sender=Task)
def _log_task_activity(sender, instance, created, **kwargs):
    actor = getattr(instance, '_activity_actor', None)

    if created:
        Activity.objects.create(
            task=instance, actor=actor,
            message=f'{instance.code} · {instance.title} foi criada.'
        )
        return

    previous = getattr(instance, '_previous', None)
    if not previous:
        return

    if previous.status != instance.status:
        Activity.objects.create(
            task=instance, actor=actor,
            message=f'{instance.code} mudou de status: {previous.status} → {instance.status}.'
        )
    if previous.assignee_id != instance.assignee_id:
        old_name = previous.assignee.name if previous.assignee_id else 'ninguém'
        new_name = instance.assignee.name if instance.assignee_id else 'ninguém'
        Activity.objects.create(
            task=instance, actor=actor,
            message=f'{instance.code} foi reatribuída de {old_name} para {new_name}.'
        )
    if previous.checked != instance.checked:
        Activity.objects.create(
            task=instance, actor=actor,
            message=f'{instance.code} foi {"marcada" if instance.checked else "desmarcada"}.'
        )


KIND_LABELS = {'image': 'uma imagem', 'video': 'um vídeo', 'link': 'um link', 'file': 'um arquivo'}


@receiver(post_save, sender=Attachment)
def _log_attachment_activity(sender, instance, created, **kwargs):
    if not created:
        return
    who = instance.uploaded_by.name if instance.uploaded_by_id else 'Alguém'
    Activity.objects.create(
        task=instance.task,
        actor=instance.uploaded_by,
        message=f'{who} anexou {KIND_LABELS.get(instance.kind, "um arquivo")} em {instance.task.code}.'
    )
