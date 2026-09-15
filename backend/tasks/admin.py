from django.contrib import admin

from .models import Activity, Attachment, AuthToken, Comment, Person, Project, Role, Subtask, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'role_list', 'is_admin']
    list_filter = ['project', 'roles', 'is_admin']

    def role_list(self, obj):
        return ', '.join(obj.roles.values_list('name', flat=True))
    role_list.short_description = 'Cargos'


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'color', 'order']
    list_filter = ['project']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'project', 'role', 'assignee', 'priority', 'status', 'due_date']
    list_filter = ['project', 'role', 'priority', 'status']
    search_fields = ['code', 'title', 'description']


@admin.register(Subtask)
class SubtaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'task', 'done', 'order']
    list_filter = ['done']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['message', 'task', 'actor', 'created_at']
    readonly_fields = ['created_at']


@admin.register(AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
    list_display = ['person', 'key', 'created_at']


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'task', 'kind', 'uploaded_by', 'created_at']
    list_filter = ['kind']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'author', 'created_at']
    search_fields = ['body', 'task__code', 'author__name']
    readonly_fields = ['created_at']


