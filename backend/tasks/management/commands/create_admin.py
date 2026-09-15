from django.core.management.base import BaseCommand, CommandError

from tasks.models import Person, Role


class Command(BaseCommand):
    help = (
        'Creates (or updates the password of) an admin Person. '
        'Safe to run in production: never deletes existing data. '
        'Usage: python manage.py create_admin <name> <password> [--role Manager]'
    )

    def add_arguments(self, parser):
        parser.add_argument('name')
        parser.add_argument('password')
        parser.add_argument('--role', default='Manager')

    def handle(self, *args, **options):
        name = options['name'].strip()
        password = options['password']
        role = options['role']

        if not name or not password:
            raise CommandError('Informe nome e senha.')

        person = Person.objects.filter(name__iexact=name).first()
        created = person is None
        if created:
            person = Person(name=name, is_admin=True)
        else:
            person.is_admin = True
        person.set_password(password)
        person.save()
        role_obj = Role.objects.filter(name=role).first()
        if role_obj and not person.roles.filter(pk=role_obj.pk).exists():
            person.roles.add(role_obj)

        action = 'criado' if created else 'atualizado'
        self.stdout.write(self.style.SUCCESS(
            f'Admin "{person.name}" {action} com sucesso. Login: "{person.name}" / senha informada.'
        ))
