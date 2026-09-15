import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Role(models.Model):
    """A job role/department. Admin-managed so the team can add or rename
    roles over time instead of being stuck with a fixed hardcoded list."""

    name = models.CharField(max_length=40, unique=True)
    color = models.CharField(max_length=60, default='oklch(0.62 0.15 200)')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


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
    roles = models.ManyToManyField(Role, related_name='people', blank=True)
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
    role = models.CharField(max_length=40)
    assignee = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks'
    )
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIA)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    checked = models.BooleanField(default=False)
    completion_note = models.TextField(blank=True, default='')
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
    class EventType(models.TextChoices):
        TASK_CREATED = 'task_created', 'Tarefa criada'
        TASK_COMPLETED = 'task_completed', 'Tarefa concluída'
        TASK_STATUS = 'task_status', 'Status alterado'
        TASK_ASSIGNED = 'task_assigned', 'Responsável alterado'
        TASK_UPDATED = 'task_updated', 'Tarefa atualizada'
        CHECKLIST = 'checklist', 'Checklist'
        COMMENT = 'comment', 'Comentário'
        ATTACHMENT = 'attachment', 'Anexo'
        TEAM = 'team', 'Equipe'
        SETTINGS = 'settings', 'Configuração'
        SYSTEM = 'system', 'Sistema'

    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Equipe'
        ADMIN = 'admin', 'Somente administradores'

    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    actor = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    message = models.CharField(max_length=300)
    event_type = models.CharField(max_length=30, choices=EventType.choices, default=EventType.SYSTEM)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.ADMIN)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, related_name='comments'
    )
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'{self.author or "Pessoa removida"} em {self.task.code}'


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
