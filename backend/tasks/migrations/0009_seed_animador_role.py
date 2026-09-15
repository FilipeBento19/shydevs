from django.db import migrations

ROLE_NAME = 'Animador'
ROLE_COLOR = 'oklch(0.62 0.15 0)'
ROLE_ORDER = 6


def seed_role(apps, schema_editor):
    Role = apps.get_model('tasks', 'Role')
    Role.objects.get_or_create(name=ROLE_NAME, defaults={'color': ROLE_COLOR, 'order': ROLE_ORDER})


def unseed_role(apps, schema_editor):
    Role = apps.get_model('tasks', 'Role')
    Role.objects.filter(name=ROLE_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0008_remove_person_role_person_roles'),
    ]

    operations = [
        migrations.RunPython(seed_role, unseed_role),
    ]
