from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from .models import Activity, Attachment, Person, Role, Subtask, Task


class PersonSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    is_admin = serializers.BooleanField(required=False)

    class Meta:
        model = Person
        fields = ['id', 'name', 'role', 'photo', 'password', 'is_admin']

    def create(self, validated_data):
        raw_password = validated_data.pop('password', None)
        person = Person(**validated_data)
        if raw_password:
            person.set_password(raw_password)
        person.save()
        return person

    def update(self, instance, validated_data):
        raw_password = validated_data.pop('password', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if raw_password:
            instance.set_password(raw_password)
        instance.save()
        return instance


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'color', 'order']

    def update(self, instance, validated_data):
        old_name = instance.name
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        new_name = instance.name
        if new_name != old_name:
            Task.objects.filter(role=old_name).update(role=new_name)
            Person.objects.filter(role=old_name).update(role=new_name)
        return instance


class SubtaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subtask
        fields = ['id', 'task', 'title', 'done', 'order']


class ActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.name', read_only=True, default=None)
    task_code = serializers.CharField(source='task.code', read_only=True, default=None)

    class Meta:
        model = Activity
        fields = ['id', 'task', 'task_code', 'actor', 'actor_name', 'message', 'created_at']


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True, default=None)

    class Meta:
        model = Attachment
        fields = ['id', 'task', 'kind', 'file', 'url', 'caption', 'uploaded_by', 'uploaded_by_name', 'created_at']
        read_only_fields = ['created_at', 'uploaded_by']


class TaskSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source='assignee.name', read_only=True, default=None)
    assignee_photo = serializers.SerializerMethodField()
    role_color = serializers.SerializerMethodField()
    subtasks = SubtaskSerializer(many=True, read_only=True)
    subtasks_done = serializers.SerializerMethodField()
    subtasks_total = serializers.SerializerMethodField()
    attachments_total = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'code', 'title', 'description', 'role', 'role_color',
            'assignee', 'assignee_name', 'assignee_photo', 'due_date', 'priority', 'status',
            'checked', 'completion_note', 'created_at', 'subtasks', 'subtasks_done',
            'subtasks_total', 'attachments_total',
        ]
        read_only_fields = ['code', 'created_at']

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
            role = Role.objects.filter(name=obj.role).first()
            return role.color if role else '#9a9ab0'
        return role_colors.get(obj.role, '#9a9ab0')

    def get_subtasks_done(self, obj):
        return sum(1 for s in obj.subtasks.all() if s.done)

    def get_subtasks_total(self, obj):
        return len(obj.subtasks.all())

    def get_attachments_total(self, obj):
        return len(obj.attachments.all())
