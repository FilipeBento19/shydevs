# Hand-written: introduces Project and scopes Role/Person/Task to one.
# Order matters — each FK is added nullable, backfilled with a single
# default project (named after whatever ProjectSettings had, if anything),
# then tightened to NOT NULL, so no existing data is lost or orphaned.

import django.db.models.deletion
from django.db import migrations, models

DEFAULT_PROJECT_NAME = 'Slayer Reborn'


def forwards(apps, schema_editor):
    Project = apps.get_model('tasks', 'Project')
    Role = apps.get_model('tasks', 'Role')
    Person = apps.get_model('tasks', 'Person')
    Task = apps.get_model('tasks', 'Task')

    name = DEFAULT_PROJECT_NAME
    try:
        ProjectSettings = apps.get_model('tasks', 'ProjectSettings')
        existing = ProjectSettings.objects.first()
        if existing and existing.name:
            name = existing.name
    except LookupError:
        pass

    project = Project.objects.create(name=name)
    Role.objects.update(project=project)
    Person.objects.update(project=project)
    Task.objects.update(project=project)


def backwards(apps, schema_editor):
    # Nothing meaningful to restore — ProjectSettings is gone either way.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0011_activity_event_details'),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.AddField(
            model_name='role',
            name='project',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='tasks.project'),
        ),
        migrations.AlterField(
            model_name='role',
            name='name',
            field=models.CharField(max_length=40),
        ),
        migrations.AddField(
            model_name='person',
            name='project',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='people', to='tasks.project'),
        ),
        migrations.AddField(
            model_name='task',
            name='project',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='tasks.project'),
        ),
        migrations.AlterField(
            model_name='task',
            name='code',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name='role',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='tasks.project'),
        ),
        migrations.AlterField(
            model_name='person',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='people', to='tasks.project'),
        ),
        migrations.AlterField(
            model_name='task',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='tasks.project'),
        ),
        migrations.AlterUniqueTogether(
            name='role',
            unique_together={('project', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='task',
            unique_together={('project', 'code')},
        ),
        migrations.DeleteModel(
            name='ProjectSettings',
        ),
    ]
