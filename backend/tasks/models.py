import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Role(models.TextChoices):
    MODELADOR = 'Modelador', 'Modelador'
    SCRIPTER = 'Scripter', 'Scripter'
    VFX_MAKER = 'Vfx Maker', 'Vfx Maker'
    UI_MAKER = 'Ui Maker', 'Ui Maker'
    MANAGER = 'Manager', 'Manager'
    SFX_MAKER = 'SFX Maker', 'SFX Maker'


ROLE_COLORS = {
    Role.MODELADOR: 'oklch(0.62 0.15 45)',
    Role.SCRIPTER: 'oklch(0.62 0.15 265)',
    Role.VFX_MAKER: 'oklch(0.62 0.15 325)',
    Role.UI_MAKER: 'oklch(0.62 0.15 200)',
    Role.MANAGER: 'oklch(0.62 0.15 150)',
    Role.SFX_MAKER: 'oklch(0.62 0.15 95)',
}


class Priority(models.TextChoices):
    BAIXA = 'Baixa', 'Baixa'
    MEDIA = 'Média', 'Média'
    ALTA = 'Alta', 'Alta'


class Status(models.TextChoices):
    PENDENTE = 'Pendente', 'Pendente'
    EM_ANDAMENTO = 'Em andamento', 'Em andamento'
    CONCLUIDA = 'Concluída', 'Concluída'


class Person(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=20, choices=Role.choices)
    password = models.CharField(max_length=128, blank=True)
    photo = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_admin = models.BooleanField(default=False)

    # Minimal shape expected by DRF permission checks (IsAuthenticated etc.)
    is_authenticated = True

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        if not self.password:
            return False
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.name


class AuthToken(models.Model):
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name='auth_token')
    key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_key():
        return secrets.token_hex(20)

    def __str__(self):
        return f'Token({self.person.name})'


class Task(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    assignee = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks'
    )
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIA)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            last = Task.objects.order_by('-id').first()
            next_id = (last.id if last else 0) + 1
            self.code = f'SD-{100 + next_id}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.code} - {self.title}'


class Subtask(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    title = models.CharField(max_length=200)
    done = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class Activity(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    actor = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    message = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message


class Attachment(models.Model):
    class Kind(models.TextChoices):
        IMAGE = 'image', 'Imagem'
        VIDEO = 'video', 'Vídeo'
        LINK = 'link', 'Link'
        FILE = 'file', 'Arquivo'

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    kind = models.CharField(max_length=10, choices=Kind.choices)
    file = models.FileField(upload_to='attachments/', blank=True, null=True)
    url = models.URLField(blank=True, max_length=500)
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='attachments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.caption or self.url or (self.file.name if self.file else f'Anexo #{self.pk}')


class ProjectSettings(models.Model):
    name = models.CharField(max_length=120, default='Slayer Reborn')

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.name
