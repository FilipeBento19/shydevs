from django.core.management.base import BaseCommand, CommandError

from tasks.models import Person, Project, Role


class Command(BaseCommand):
    help = (
        'Creates (or updates the password of) an admin Person in a project. '
        'Safe to run in production: never deletes existing data. '
        'Usage: python manage.py create_admin <name> <password> --project "Project Name" [--role Manager]'
    )

    def add_arguments(self, parser):
        parser.add_argument('name')
        parser.add_argument('password')
        parser.add_argument('--project', required=True, help='Project name (created if it does not exist yet).')
        parser.add_argument('--role', default='Manager')

    def handle(self, *args, **options):
        name = options['name'].strip()
        password = options['password']
        project_name = options['project'].strip()
        role = options['role']

        if not name or not password or not project_name:
            raise CommandError('Informe nome, senha e projeto.')

        project, _ = Project.objects.get_or_create(name=project_name)

        person = Person.objects.filter(project=project, name__iexact=name).first()
        created = person is None
        if created:
            person = Person(project=project, name=name, is_admin=True)
        else:
            person.is_admin = True
        person.set_password(password)
        person.save()
        role_obj = Role.objects.filter(project=project, name=role).first()
        if not role_obj:
            role_obj = Role.objects.create(project=project, name=role)
        if not person.roles.filter(pk=role_obj.pk).exists():
            person.roles.add(role_obj)

        action = 'criado' if created else 'atualizado'
        self.stdout.write(self.style.SUCCESS(
            f'Admin "{person.name}" {action} com sucesso. Login: "{person.name}" / senha informada.'
        ))
