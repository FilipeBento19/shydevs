import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class Project(models.Model):
    """A workspace: its own tasks, people and roles. Selected via the
    dropdown in the header; nothing below is shared across projects."""

    name = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_unverified_discord_reminder_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Role(models.Model):
    """A job role/department. Admin-managed so the team can add or rename
    roles over time instead of being stuck with a fixed hardcoded list."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=40)
    color = models.CharField(max_length=60, default='oklch(0.62 0.15 200)')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('project', 'name')]

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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='people')
    name = models.CharField(max_length=120)
    roles = models.ManyToManyField(Role, related_name='people', blank=True)
    password = models.CharField(max_length=128, blank=True)
    photo = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    # Discord's numeric user ID (not a username) — set by an admin on the
    # Team screen, used to @mention this person in webhook notifications
    # and to DM them directly.
    discord_id = models.CharField(max_length=32, blank=True)
    discord_verified_at = models.DateTimeField(null=True, blank=True)
    discord_verification_code = models.CharField(max_length=16, blank=True)
    discord_verification_expires_at = models.DateTimeField(null=True, blank=True)
    # Set by send_discord_reminders after DMing a workload digest, so the
    # every-2-days cadence is tracked per person.
    last_digest_sent_at = models.DateTimeField(null=True, blank=True)

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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    code = models.CharField(max_length=20, blank=True)
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
    # Set by the notify_overdue command once it's posted an overdue notice for
    # the task's current due_date, so it doesn't re-notify every run; reset
    # whenever due_date changes (see signals.stash_previous_task).
    overdue_notified = models.BooleanField(default=False)
    # Set by send_discord_reminders once it's DM'd a "due soon" nudge for the
    # task's current due_date; reset whenever due_date changes.
    due_soon_notified = models.BooleanField(default=False)
    # When `status` last changed (defaults to creation time). Drives the
    # "stuck in this status too long" DM reminders below; reset whenever
    # status actually changes (see signals.stash_previous_task).
    status_changed_at = models.DateTimeField(default=timezone.now)
    pending_reminder_sent = models.BooleanField(default=False)
    in_progress_reminder_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('project', 'code')]

    def save(self, *args, **kwargs):
        if not self.code:
            last = Task.objects.filter(project=self.project).order_by('-id').first()
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
        OVERDUE = 'overdue', 'Atraso'
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


class DiscordMessage(models.Model):
    """A log of every DM the bot sent or received — automatic reminders,
    admin-sent broadcasts, and replies people send back to the bot. Does
    NOT cover the webhook channel notifications (task events, comments,
    etc.), which are a separate, unlogged system."""

    class Direction(models.TextChoices):
        OUTGOING = 'outgoing', 'Enviada'
        INCOMING = 'incoming', 'Recebida'

    class Source(models.TextChoices):
        ADMIN = 'admin', 'Mensagem manual (admin)'
        PENDING_REMINDER = 'pending_reminder', 'Lembrete: parada em Pendente'
        IN_PROGRESS_REMINDER = 'in_progress_reminder', 'Lembrete: presa em Em andamento'
        DUE_SOON_REMINDER = 'due_soon_reminder', 'Lembrete: prazo chegando'
        DIGEST = 'digest', 'Resumo periódico'
        DM = 'dm', 'DM recebida'

    # Nullable: an incoming DM might come from a Discord ID that doesn't
    # match any registered Person (project can't be inferred either, then).
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='discord_messages')
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='discord_messages')
    discord_id = models.CharField(max_length=32, blank=True)
    direction = models.CharField(max_length=10, choices=Direction.choices)
    source = models.CharField(max_length=30, choices=Source.choices)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        who = self.person.name if self.person else (self.discord_id or 'desconhecido')
        return f'{self.direction} · {who}'


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
