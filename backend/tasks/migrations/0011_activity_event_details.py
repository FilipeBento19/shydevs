from django.db import migrations, models


def classify_existing_activities(apps, schema_editor):
    Activity = apps.get_model('tasks', 'Activity')
    for activity in Activity.objects.all().iterator():
        message = activity.message.lower()
        event_type = 'system'
        visibility = 'admin'
        if 'foi criada' in message:
            event_type, visibility = 'task_created', 'public'
        elif 'concluída' in message and 'mudou de status' in message:
            event_type, visibility = 'task_completed', 'public'
        elif 'reatribuída' in message:
            event_type, visibility = 'task_assigned', 'public'
        elif 'mudou de status' in message:
            event_type = 'task_status'
        elif 'comentou' in message:
            event_type = 'comment'
        elif 'anexou' in message:
            event_type = 'attachment'
        elif 'nota de conclusão' in message:
            event_type = 'task_updated'
        activity.event_type = event_type
        activity.visibility = visibility
        activity.save(update_fields=['event_type', 'visibility'])


class Migration(migrations.Migration):
    dependencies = [('tasks', '0010_comment')]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='details',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='activity',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('task_created', 'Tarefa criada'), ('task_completed', 'Tarefa concluída'),
                    ('task_status', 'Status alterado'), ('task_assigned', 'Responsável alterado'),
                    ('task_updated', 'Tarefa atualizada'), ('checklist', 'Checklist'),
                    ('comment', 'Comentário'), ('attachment', 'Anexo'), ('team', 'Equipe'),
                    ('settings', 'Configuração'), ('system', 'Sistema'),
                ],
                default='system', max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='activity',
            name='visibility',
            field=models.CharField(
                choices=[('public', 'Equipe'), ('admin', 'Somente administradores')],
                default='admin', max_length=10,
            ),
        ),
        migrations.RunPython(classify_existing_activities, migrations.RunPython.noop),
    ]
