from django.db import migrations

DEFAULT_ROLES = [
    ('Modelador', 'oklch(0.62 0.15 45)', 0),
    ('Scripter', 'oklch(0.62 0.15 265)', 1),
    ('Vfx Maker', 'oklch(0.62 0.15 325)', 2),
    ('Ui Maker', 'oklch(0.62 0.15 200)', 3),
    ('Manager', 'oklch(0.62 0.15 150)', 4),
    ('SFX Maker', 'oklch(0.62 0.15 95)', 5),
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model('tasks', 'Role')
    for name, color, order in DEFAULT_ROLES:
        Role.objects.get_or_create(name=name, defaults={'color': color, 'order': order})


def unseed_roles(apps, schema_editor):
    Role = apps.get_model('tasks', 'Role')
    Role.objects.filter(name__in=[r[0] for r in DEFAULT_ROLES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0006_role_alter_person_role_alter_task_role'),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
