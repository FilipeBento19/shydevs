from django.core.management.base import BaseCommand

from tasks.models import Activity, AuthToken, Person, Subtask, Task

ADMIN_NAME = 'Akanub'
ADMIN_PASSWORD = 'akanub123'
ADMIN_ROLE = 'Manager'


class Command(BaseCommand):
    help = 'Wipe all demo data and create the single admin account (Akanub).'

    def handle(self, *args, **options):
        Activity.objects.all().delete()
        Subtask.objects.all().delete()
        Task.objects.all().delete()
        AuthToken.objects.all().delete()
        Person.objects.all().delete()

        admin = Person(name=ADMIN_NAME, role=ADMIN_ROLE, is_admin=True)
        admin.set_password(ADMIN_PASSWORD)
        admin.save()

        self.stdout.write(self.style.SUCCESS('Backend limpo. Nenhuma tarefa ou pessoa de demonstração restante.'))
        self.stdout.write(self.style.WARNING(
            f'Login do administrador: usuário "{ADMIN_NAME}", senha "{ADMIN_PASSWORD}" '
            f'(altere depois pelo admin do Django em /admin/).'
        ))
