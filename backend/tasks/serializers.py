from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from .models import Activity, Attachment, Comment, DiscordMessage, Person, Project, Reference, Role, Subtask, Task
from .storages import kind_for_name


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['created_at']


class DiscordMessageSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source='person.name', read_only=True, default=None)

    class Meta:
        model = DiscordMessage
        fields = ['id', 'person', 'person_name', 'discord_id', 'direction', 'source', 'content', 'created_at']


class PersonSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    is_admin = serializers.BooleanField(required=False)
    roles = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    discord_verified = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = [
            'id', 'project', 'name', 'roles', 'photo', 'password', 'is_admin',
            'discord_id', 'discord_verified', 'discord_verified_at',
        ]
        read_only_fields = ['project', 'discord_verified_at']

    def get_discord_verified(self, instance):
        return bool(instance.discord_id and instance.discord_verified_at)

    def _resolve_roles(self, names, project):
        qs = Role.objects.filter(project=project, name__in=names)
        missing = set(names) - {r.name for r in qs}
        if missing:
            raise serializers.ValidationError({'roles': f'Cargo(s) inexistente(s): {", ".join(sorted(missing))}'})
        return qs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['roles'] = list(instance.roles.values_list('name', flat=True))
        return data

    def create(self, validated_data):
        raw_password = validated_data.pop('password', None)
        role_names = validated_data.pop('roles', [])
        person = Person(**validated_data)
        if raw_password:
            person.set_password(raw_password)
        person.save()
        if role_names:
            person.roles.set(self._resolve_roles(role_names, person.project))
        return person

    def update(self, instance, validated_data):
        raw_password = validated_data.pop('password', None)
        role_names = validated_data.pop('roles', None)
        old_discord_id = instance.discord_id
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if 'discord_id' in validated_data and instance.discord_id != old_discord_id:
            instance.discord_verified_at = None
            instance.discord_verification_code = ''
            instance.discord_verification_expires_at = None
        if raw_password:
            instance.set_password(raw_password)
        instance.save()
        if role_names is not None:
            instance.roles.set(self._resolve_roles(role_names, instance.project))
        return instance


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'project', 'name', 'color', 'order']
        read_only_fields = ['project']

    def update(self, instance, validated_data):
        old_name = instance.name
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        new_name = instance.name
        if new_name != old_name:
            # Person.roles is a real relation, so renaming here already
            # reflects there automatically. Task.role is still a plain
            # string field, so it needs an explicit cascade — scoped to
            # this role's own project so it can't touch another one's tasks.
            Task.objects.filter(project=instance.project, role=old_name).update(role=new_name)
        return instance


class SubtaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subtask
        fields = ['id', 'task', 'title', 'done', 'order']


class ActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.name', read_only=True, default=None)
    task_code = serializers.CharField(source='task.code', read_only=True, default=None)
    task_title = serializers.CharField(source='task.title', read_only=True, default=None)

    class Meta:
        model = Activity
        fields = [
            'id', 'task', 'task_code', 'task_title', 'actor', 'actor_name', 'message',
            'event_type', 'visibility', 'details', 'created_at',
        ]


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True, default='Pessoa removida')
    author_photo = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'task', 'author', 'author_name', 'author_photo', 'body', 'created_at']
        read_only_fields = ['author', 'created_at']

    def validate_body(self, value):
        body = value.strip()
        if not body:
            raise serializers.ValidationError('Escreva um comentário.')
        return body

    def get_author_photo(self, obj):
        if not obj.author or not obj.author.photo:
            return None
        request = self.context.get('request')
        url = obj.author.photo.url
        return request.build_absolute_uri(url) if request else url


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True, default=None)
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'task', 'kind', 'file', 'file_name', 'url', 'caption', 'uploaded_by', 'uploaded_by_name', 'created_at']
        read_only_fields = ['created_at', 'uploaded_by']
        extra_kwargs = {'kind': {'required': False}}

    def get_file_name(self, obj):
        if not obj.file:
            return None
        return obj.file.name.rsplit('/', 1)[-1]

    def validate(self, attrs):
        if not attrs.get('file'):
            raise serializers.ValidationError({'file': 'Escolha um arquivo para anexar.'})
        return attrs


class ReferenceSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True, default=None)
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Reference
        fields = [
            'id', 'task', 'group', 'kind', 'file', 'file_name', 'url', 'caption',
            'uploaded_by', 'uploaded_by_name', 'created_at',
        ]
        read_only_fields = ['kind', 'created_at', 'uploaded_by']
        extra_kwargs = {
            'file': {'required': False},
            'url': {'required': False, 'allow_blank': True},
            'group': {'required': False},
        }

    def get_file_name(self, obj):
        if not obj.file:
            return None
        return obj.file.name.rsplit('/', 1)[-1]

    def validate_group(self, value):
        return (value or '').strip() or 'Geral'

    def validate(self, attrs):
        if not attrs.get('file') and not (attrs.get('url') or '').strip():
            raise serializers.ValidationError({'url': 'Envie um arquivo ou cole um link.'})
        return attrs

    @staticmethod
    def detect_kind(file, url):
        """image/video/file by extension for uploads; for links, direct media
        URLs count as image/video (so they get the real viewer) and anything
        else stays a plain link."""
        if file:
            return kind_for_name(file.name)
        detected = kind_for_name(url or '')
        return detected if detected in ('image', 'video') else 'link'


class TaskSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source='assignee.name', read_only=True, default=None)
    assignee_photo = serializers.SerializerMethodField()
    role_color = serializers.SerializerMethodField()
    subtasks = SubtaskSerializer(many=True, read_only=True)
    subtasks_done = serializers.SerializerMethodField()
    subtasks_total = serializers.SerializerMethodField()
    attachments_total = serializers.SerializerMethodField()
    references_total = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'project', 'code', 'title', 'description', 'role', 'role_color',
            'assignee', 'assignee_name', 'assignee_photo', 'due_date', 'priority', 'status',
            'checked', 'completion_note', 'created_at', 'subtasks', 'subtasks_done',
            'subtasks_total', 'attachments_total', 'references_total',
        ]
        read_only_fields = ['project', 'code', 'created_at']

    def _actor(self):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        return user if user and getattr(user, 'is_authenticated', False) else None

    def create(self, validated_data):
        instance = Task(**validated_data)
        instance._activity_actor = self._actor()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        instance._activity_actor = self._actor()
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def get_assignee_photo(self, obj):
        person = obj.assignee
        if not person or not person.photo:
            return None
        request = self.context.get('request')
        url = person.photo.url
        return request.build_absolute_uri(url) if request else url

    def get_role_color(self, obj):
        role_colors = self.context.get('role_colors')
        if role_colors is None:
            role = Role.objects.filter(project=obj.project, name=obj.role).first()
            return role.color if role else '#9a9ab0'
        return role_colors.get(obj.role, '#9a9ab0')

    def get_subtasks_done(self, obj):
        return sum(1 for s in obj.subtasks.all() if s.done)

    def get_subtasks_total(self, obj):
        return len(obj.subtasks.all())

    def get_attachments_total(self, obj):
        return len(obj.attachments.all())

    def get_references_total(self, obj):
        return len(obj.references.all())
