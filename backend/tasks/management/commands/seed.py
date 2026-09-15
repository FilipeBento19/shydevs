from django.core.management.base import BaseCommand

from tasks.models import Activity, AuthToken, Person, Project, Role, Subtask, Task

PROJECT_NAME = 'Slayer Reborn'
ADMIN_NAME = 'Akanub'
ADMIN_PASSWORD = 'akanub123'
ADMIN_ROLE = 'Manager'
DEFAULT_ROLES = [
    ('Modelador', 'oklch(0.62 0.15 45)', 0),
    ('Scripter', 'oklch(0.62 0.15 265)', 1),
    ('Vfx Maker', 'oklch(0.62 0.15 325)', 2),
    ('Ui Maker', 'oklch(0.62 0.15 200)', 3),
    ('Manager', 'oklch(0.62 0.15 150)', 4),
    ('SFX Maker', 'oklch(0.62 0.15 95)', 5),
    ('Animador', 'oklch(0.62 0.15 0)', 6),
]


class Command(BaseCommand):
    help = 'Wipe all demo data and create a single project with the admin account (Akanub).'

    def handle(self, *args, **options):
        Activity.objects.all().delete()
        Subtask.objects.all().delete()
        Task.objects.all().delete()
        AuthToken.objects.all().delete()
        Person.objects.all().delete()
        Role.objects.all().delete()
        Project.objects.all().delete()

        project = Project.objects.create(name=PROJECT_NAME)
        for name, color, order in DEFAULT_ROLES:
            Role.objects.create(project=project, name=name, color=color, order=order)

        admin = Person(project=project, name=ADMIN_NAME, is_admin=True)
        admin.set_password(ADMIN_PASSWORD)
        admin.save()
        role = Role.objects.filter(project=project, name=ADMIN_ROLE).first()
        if role:
            admin.roles.add(role)

        self.stdout.write(self.style.SUCCESS('Backend limpo. Nenhuma tarefa ou pessoa de demonstração restante.'))
        self.stdout.write(self.style.WARNING(
            f'Login do administrador: usuário "{ADMIN_NAME}", senha "{ADMIN_PASSWORD}" '
            f'(altere depois pelo admin do Django em /admin/).'
        ))
