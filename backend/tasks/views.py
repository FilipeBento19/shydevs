import os
from io import StringIO

from django.core.management import call_command
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status as http_status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Activity, Attachment, AuthToken, Comment, Person, Priority, Project, Role, Status, Subtask, Task,
)
from .serializers import (
    ActivitySerializer, AttachmentSerializer, CommentSerializer, PersonSerializer, ProjectSerializer,
    RoleSerializer, SubtaskSerializer, TaskSerializer,
)


def project_id_from(request):
    """The project a request is scoped to: query param on reads, body field
    on writes. Returns None (never raises) if absent/not a valid integer —
    callers decide what an absent project means for that endpoint."""
    raw = request.query_params.get('project') if request.method in permissions.SAFE_METHODS else request.data.get('project')
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def log_admin_event(actor, message, event_type=Activity.EventType.SYSTEM, details=None, task=None):
    Activity.objects.create(
        task=task,
        actor=actor,
        message=message,
        event_type=event_type,
        visibility=Activity.Visibility.ADMIN,
        details=details or {},
    )


class IsAdminOrReadOnly(permissions.BasePermission):
    """Anyone can read; only the admin person may create/update/delete."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return bool(user and getattr(user, 'is_authenticated', False) and getattr(user, 'is_admin', False))


class TaskPermission(permissions.BasePermission):
    """Anyone can read. Admins can do anything. A non-admin who is the task's
    assignee may PATCH it (view-level restricts *which* fields are settable
    below in TaskViewSet.partial_update), but cannot create, delete, or PUT."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not (user and getattr(user, 'is_authenticated', False)):
            return False
        if getattr(user, 'is_admin', False):
            return True
        return request.method == 'PATCH'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if getattr(user, 'is_admin', False):
            return True
        return request.method == 'PATCH' and obj.assignee_id == getattr(user, 'id', None)


class SubtaskPermission(permissions.BasePermission):
    """Admins manage checklist structure; task owners may only toggle items."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not (user and getattr(user, 'is_authenticated', False)):
            return False
        if getattr(user, 'is_admin', False):
            return True
        return request.method == 'PATCH'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if getattr(user, 'is_admin', False):
            return True
        return request.method == 'PATCH' and obj.task.assignee_id == getattr(user, 'id', None)


class ProjectPermission(permissions.BasePermission):
    """Anyone can read (that's how the switcher lists projects for people who
    aren't logged in yet). Creating a new project requires being an admin
    already — of any project, since you don't belong to the new one yet.
    Renaming/deleting a project requires being an admin *of that project*."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not (user and getattr(user, 'is_authenticated', False) and getattr(user, 'is_admin', False)):
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return bool(
            getattr(user, 'is_admin', False)
            and getattr(user, 'project_id', None) == obj.id
        )


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [ProjectPermission]

    def create(self, request, *args, **kwargs):
        name = (request.data.get('name') or '').strip()
        if not name:
            return Response({'detail': 'Informe o nome do projeto.'}, status=400)
        if Project.objects.filter(name__iexact=name).exists():
            return Response({'detail': 'Já existe um projeto com esse nome.'}, status=400)

        project = Project.objects.create(name=name)

        # The admin who created it becomes this project's first admin too —
        # same name and password (copied as a hash, never re-entered), so
        # they can switch straight in without a separate signup step.
        creator = request.user
        admin = Person(project=project, name=creator.name, is_admin=True, password=creator.password)
        admin.save()
        token = AuthToken.objects.create(person=admin, key=AuthToken.generate_key())

        return Response(
            {
                'project': ProjectSerializer(project).data,
                'token': token.key,
                'person': PersonSerializer(admin).data,
            },
            status=http_status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        password = request.data.get('password') or ''
        try:
            project_id = int(request.data.get('project'))
        except (TypeError, ValueError):
            project_id = None
        if not project_id:
            return Response({'detail': 'Selecione um projeto.'}, status=400)
        try:
            person = Person.objects.get(project_id=project_id, name__iexact=name)
        except Person.DoesNotExist:
            return Response({'detail': 'Credenciais inválidas.'}, status=http_status.HTTP_401_UNAUTHORIZED)

        if not person.check_password(password):
            return Response({'detail': 'Credenciais inválidas.'}, status=http_status.HTTP_401_UNAUTHORIZED)

        token, _ = AuthToken.objects.get_or_create(
            person=person, defaults={'key': AuthToken.generate_key()}
        )
        log_admin_event(person, f'{person.name} entrou no sistema.', details={'ação': 'login'})
        return Response({'token': token.key, 'person': PersonSerializer(person).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        log_admin_event(request.user, f'{request.user.name} saiu do sistema.', details={'ação': 'logout'})
        AuthToken.objects.filter(person=request.user).delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PersonSerializer(request.user).data)


class PersonViewSet(viewsets.ModelViewSet):
    serializer_class = PersonSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_permissions(self):
        if self.action in ('photo', 'change_password'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        qs = Person.objects.all().order_by('name')
        user = self.request.user
        if getattr(user, 'is_authenticated', False):
            return qs.filter(project_id=user.project_id)
        project_id = project_id_from(self.request)
        return qs.filter(project_id=project_id) if project_id else qs.none()

    def _would_remove_last_admin(self, instance, validated_data):
        becoming_non_admin = 'is_admin' in validated_data and not validated_data['is_admin']
        return (
            instance.is_admin and becoming_non_admin
            and Person.objects.filter(project_id=instance.project_id, is_admin=True).exclude(pk=instance.pk).count() == 0
        )

    def perform_create(self, serializer):
        person = serializer.save(project=self.request.user.project)
        log_admin_event(
            self.request.user,
            f'{self.request.user.name} adicionou {person.name} à equipe.',
            Activity.EventType.TEAM,
            {'pessoa': person.name, 'cargos': list(person.roles.values_list('name', flat=True)), 'admin': person.is_admin},
        )

    def perform_update(self, serializer):
        person = serializer.instance
        before = {'nome': person.name, 'cargos': list(person.roles.values_list('name', flat=True)), 'admin': person.is_admin}
        person = serializer.save()
        after = {'nome': person.name, 'cargos': list(person.roles.values_list('name', flat=True)), 'admin': person.is_admin}
        changes = {key: {'antes': before[key], 'depois': after[key]} for key in before if before[key] != after[key]}
        if changes:
            log_admin_event(
                self.request.user, f'{self.request.user.name} atualizou o perfil de {person.name}.',
                Activity.EventType.TEAM, {'alterações': changes},
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if self._would_remove_last_admin(instance, request.data):
            return Response({'detail': 'Precisa existir pelo menos um administrador.'}, status=400)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if self._would_remove_last_admin(instance, request.data):
            return Response({'detail': 'Precisa existir pelo menos um administrador.'}, status=400)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_admin and Person.objects.filter(project_id=instance.project_id, is_admin=True).exclude(pk=instance.pk).count() == 0:
            return Response({'detail': 'Precisa existir pelo menos um administrador.'}, status=400)
        log_admin_event(
            request.user, f'{request.user.name} removeu {instance.name} da equipe.',
            Activity.EventType.TEAM, {'pessoa removida': instance.name},
        )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def photo(self, request, pk=None):
        person = self.get_object()
        user = request.user
        is_self = getattr(user, 'id', None) == person.id
        if not (getattr(user, 'is_admin', False) or is_self):
            return Response({'detail': 'Você só pode alterar a sua própria foto.'}, status=http_status.HTTP_403_FORBIDDEN)
        file = request.FILES.get('photo')
        if not file:
            return Response({'detail': 'Nenhum arquivo enviado.'}, status=400)
        person.photo = file
        person.save()
        log_admin_event(
            user, f'{user.name} alterou a foto de perfil de {person.name}.',
            Activity.EventType.TEAM, {'perfil': person.name, 'campo': 'foto'},
        )
        return Response(PersonSerializer(person, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None):
        person = self.get_object()
        user = request.user
        is_self = getattr(user, 'id', None) == person.id
        if not (getattr(user, 'is_admin', False) or is_self):
            return Response({'detail': 'Você só pode trocar a sua própria senha.'}, status=http_status.HTTP_403_FORBIDDEN)
        new_password = request.data.get('password') or ''
        if not new_password:
            return Response({'detail': 'Informe a nova senha.'}, status=400)
        person.set_password(new_password)
        person.save()
        log_admin_event(
            user, f'{user.name} alterou a senha de {person.name}.',
            Activity.EventType.TEAM, {'perfil': person.name, 'campo': 'senha', 'conteúdo': 'não registrado'},
        )
        return Response({'detail': 'Senha alterada com sucesso.'})


class RoleViewSet(viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Role.objects.all()
        user = self.request.user
        if getattr(user, 'is_authenticated', False):
            return qs.filter(project_id=user.project_id)
        project_id = project_id_from(self.request)
        return qs.filter(project_id=project_id) if project_id else qs.none()

    def perform_create(self, serializer):
        role = serializer.save(project=self.request.user.project)
        log_admin_event(
            self.request.user, f'{self.request.user.name} criou o cargo {role.name}.',
            Activity.EventType.TEAM, {'cargo': role.name, 'cor': role.color},
        )

    def perform_update(self, serializer):
        role = serializer.instance
        before = {'nome': role.name, 'cor': role.color, 'ordem': role.order}
        role = serializer.save()
        after = {'nome': role.name, 'cor': role.color, 'ordem': role.order}
        log_admin_event(
            self.request.user, f'{self.request.user.name} atualizou o cargo {role.name}.',
            Activity.EventType.TEAM,
            {'alterações': {key: {'antes': before[key], 'depois': after[key]} for key in before if before[key] != after[key]}},
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        in_use = Task.objects.filter(project_id=instance.project_id, role=instance.name).exists() or instance.people.exists()
        if in_use:
            return Response(
                {'detail': 'Esse cargo está em uso por pessoas ou tarefas e não pode ser removido.'},
                status=400,
            )
        log_admin_event(
            request.user, f'{request.user.name} removeu o cargo {instance.name}.',
            Activity.EventType.TEAM, {'cargo removido': instance.name},
        )
        return super().destroy(request, *args, **kwargs)


OWNER_EDITABLE_FIELDS = {'status', 'completion_note'}


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [TaskPermission]

    def get_permissions(self):
        if self.action in ('bulk_update', 'dashboard'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not getattr(request.user, 'is_admin', False):
            disallowed = set(request.data.keys()) - OWNER_EDITABLE_FIELDS
            if disallowed:
                return Response(
                    {'detail': 'Você só pode alterar o status e a nota de conclusão das suas próprias tarefas.'},
                    status=http_status.HTTP_403_FORBIDDEN,
                )
            new_status = request.data.get('status', instance.status)
            new_note = request.data.get('completion_note', instance.completion_note)
            if new_status == Status.CONCLUIDA and not (new_note or '').strip():
                return Response(
                    {'detail': 'Deixe uma nota de conclusão antes de marcar como concluída.'},
                    status=400,
                )
        return super().partial_update(request, *args, **kwargs)

    def get_queryset(self):
        qs = Task.objects.select_related('assignee').prefetch_related('subtasks', 'attachments').all()
        params = self.request.query_params
        user = self.request.user

        if getattr(user, 'is_authenticated', False):
            qs = qs.filter(project_id=user.project_id)
        else:
            project_id = project_id_from(self.request)
            qs = qs.filter(project_id=project_id) if project_id else qs.none()

        role = params.get('role')
        if role and role != 'Todos':
            qs = qs.filter(role=role)

        person = params.get('person')
        if person and person != 'Todos':
            qs = qs.filter(assignee__name=person)

        priority = params.get('priority')
        if priority and priority != 'Todas':
            qs = qs.filter(priority=priority)

        status_ = params.get('status')
        if status_ == 'Atrasadas':
            qs = qs.filter(due_date__lt=timezone.now().date()).exclude(status=Status.CONCLUIDA)
        elif status_ and status_ != 'Todas':
            qs = qs.filter(status=status_)

        query = params.get('query')
        if query:
            qs = qs.filter(
                Q(title__icontains=query) | Q(description__icontains=query) |
                Q(assignee__name__icontains=query) | Q(role__icontains=query) |
                Q(code__icontains=query)
            )

        return qs

    def perform_create(self, serializer):
        serializer.save(project=self.request.user.project)

    def perform_destroy(self, instance):
        log_admin_event(
            self.request.user,
            f'{self.request.user.name} excluiu a tarefa {instance.code} · {instance.title}.',
            Activity.EventType.TASK_UPDATED,
            {'tarefa excluída': instance.code, 'título': instance.title, 'responsável': instance.assignee_name if hasattr(instance, 'assignee_name') else (instance.assignee.name if instance.assignee else 'ninguém')},
        )
        instance.delete()

    def _actor(self):
        user = self.request.user
        return user if getattr(user, 'is_authenticated', False) else None

    def get_serializer_context(self):
        context = super().get_serializer_context()
        project_id = getattr(self.request.user, 'project_id', None) or project_id_from(self.request)
        context['role_colors'] = dict(Role.objects.filter(project_id=project_id).values_list('name', 'color'))
        return context

    @action(detail=False, methods=['get'])
    def balance(self, request):
        project_id = getattr(request.user, 'project_id', None) or project_id_from(request)
        best = None
        for role in Role.objects.filter(project_id=project_id):
            members = Person.objects.filter(roles=role).distinct()
            if members.count() < 2:
                continue
            load = []
            for m in members:
                n = m.tasks.exclude(status=Status.CONCLUIDA).count()
                load.append({'name': m.name, 'n': n})
            load.sort(key=lambda x: -x['n'])
            gap = load[0]['n'] - load[-1]['n']
            if best is None or gap > best['gap']:
                best = {'gap': gap, 'role': role.name, 'top': load[0], 'low': load[-1]}

        if best and best['gap'] > 0:
            text = (
                f"{best['top']['name']} está com {best['top']['n']} entregas abertas de "
                f"{best['role']} enquanto {best['low']['name']} está com {best['low']['n']}. "
                f"Considere transferir 1 tarefa para manter o cargo equilibrado."
            )
            role_name = best['role']
        else:
            text = 'Todos os cargos com mais de uma pessoa estão com a carga equilibrada no momento.'
            role_name = 'Equipe'

        return Response({'role': role_name, 'text': text})

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        project_id = request.user.project_id
        tasks = list(Task.objects.filter(project_id=project_id).select_related('assignee'))
        total = len(tasks)
        by_status = {s.value: sum(1 for t in tasks if t.status == s.value) for s in Status}
        by_role = {r.name: sum(1 for t in tasks if t.role == r.name) for r in Role.objects.filter(project_id=project_id)}
        by_priority = {p.value: sum(1 for t in tasks if t.priority == p.value) for p in Priority}

        overdue = sum(1 for t in tasks if t.due_date and t.due_date < timezone.now().date() and t.status != Status.CONCLUIDA)

        people = list(Person.objects.filter(project_id=project_id).prefetch_related('roles'))
        workload = [
            {
                'name': p.name,
                'roles': [r.name for r in p.roles.all()],
                'photo': request.build_absolute_uri(p.photo.url) if p.photo else None,
                'open': sum(1 for t in tasks if t.assignee_id == p.id and t.status != Status.CONCLUIDA),
                'done': sum(1 for t in tasks if t.assignee_id == p.id and t.status == Status.CONCLUIDA),
            }
            for p in people
        ]

        return Response({
            'total': total,
            'by_status': by_status,
            'by_role': by_role,
            'by_priority': by_priority,
            'overdue': overdue,
            'workload': workload,
        })

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        ids = request.data.get('ids') or []
        fields = request.data.get('fields') or {}
        allowed = {'status', 'priority', 'assignee', 'checked'}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not ids or not fields:
            return Response({'detail': 'Informe ids e ao menos um campo.'}, status=400)

        qs = Task.objects.filter(id__in=ids, project_id=request.user.project_id)
        if not getattr(request.user, 'is_admin', False):
            fields = {'status': fields['status']} if 'status' in fields else {}
            if not fields:
                return Response(
                    {'detail': 'Você só pode alterar o status das suas próprias tarefas.'},
                    status=http_status.HTTP_403_FORBIDDEN,
                )
            if fields['status'] == Status.CONCLUIDA:
                return Response(
                    {'detail': 'Para concluir uma tarefa, adicione a nota de conclusão nela individualmente.'},
                    status=400,
                )
            qs = qs.filter(assignee_id=request.user.id)
            if qs.count() != len(set(ids)):
                return Response(
                    {'detail': 'Algumas tarefas selecionadas não são suas.'},
                    status=http_status.HTTP_403_FORBIDDEN,
                )

        updated = []
        for task in qs:
            for k, v in fields.items():
                setattr(task, k, v)
            task._activity_actor = self._actor()
            task.save()
            updated.append(task.id)
        return Response({'updated': updated})

    @action(detail=False, methods=['delete'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids') or []
        qs = Task.objects.filter(id__in=ids, project_id=request.user.project_id)
        tasks = list(qs.select_related('assignee'))
        for task in tasks:
            log_admin_event(
                request.user, f'{request.user.name} excluiu a tarefa {task.code} · {task.title}.',
                Activity.EventType.TASK_UPDATED,
                {'tarefa excluída': task.code, 'título': task.title},
            )
        deleted, _ = qs.delete()
        return Response({'deleted': deleted})


class SubtaskViewSet(viewsets.ModelViewSet):
    serializer_class = SubtaskSerializer
    permission_classes = [SubtaskPermission]

    def get_queryset(self):
        qs = Subtask.objects.select_related('task').all()
        user = self.request.user
        if getattr(user, 'is_authenticated', False):
            qs = qs.filter(task__project_id=user.project_id)
        else:
            project_id = project_id_from(self.request)
            qs = qs.filter(task__project_id=project_id) if project_id else qs.none()
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs

    def partial_update(self, request, *args, **kwargs):
        if not getattr(request.user, 'is_admin', False) and set(request.data) - {'done'}:
            return Response(
                {'detail': 'Você só pode marcar ou desmarcar etapas da sua própria tarefa.'},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = Subtask(**serializer.validated_data)
        instance._activity_actor = self.request.user
        instance.save()
        serializer.instance = instance

    def perform_update(self, serializer):
        serializer.instance._activity_actor = self.request.user
        serializer.save()

    def perform_destroy(self, instance):
        instance._activity_actor = self.request.user
        instance.delete()


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.user.project_id
        qs = Activity.objects.select_related('actor', 'task').filter(
            Q(actor__project_id=project_id) | Q(task__project_id=project_id)
        )
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        scope = self.request.query_params.get('scope', 'normal')
        if scope == 'admin' and getattr(self.request.user, 'is_admin', False):
            return qs[:500]
        qs = qs.filter(visibility=Activity.Visibility.PUBLIC)
        return qs[:200]

    def list(self, request, *args, **kwargs):
        if request.query_params.get('scope') == 'admin' and not getattr(request.user, 'is_admin', False):
            return Response({'detail': 'Histórico administrativo restrito.'}, status=http_status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)


class CommentPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'is_authenticated', False))

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return bool(
            getattr(user, 'is_admin', False)
            or obj.author_id == getattr(user, 'id', None)
        )


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [CommentPermission]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = Comment.objects.select_related('author', 'task').filter(task__project_id=self.request.user.project_id)
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs

    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)
        Activity.objects.create(
            task=comment.task,
            actor=self.request.user,
            event_type=Activity.EventType.COMMENT,
            visibility=Activity.Visibility.ADMIN,
            message=f'{self.request.user.name} comentou em {comment.task.code} · {comment.task.title}.',
            details={'comentário': comment.body},
        )

    def perform_destroy(self, instance):
        Activity.objects.create(
            task=instance.task,
            actor=self.request.user,
            event_type=Activity.EventType.COMMENT,
            visibility=Activity.Visibility.ADMIN,
            message=f'{self.request.user.name} removeu um comentário de {instance.task.code}.',
            details={'comentário removido': instance.body},
        )
        instance.delete()


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """Anyone can read; any logged-in person may create (proof-of-work uploads).
    Only the uploader or an admin may delete."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and getattr(request.user, 'is_authenticated', False))

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if getattr(user, 'is_admin', False):
            return True
        return obj.uploaded_by_id == getattr(user, 'id', None)


class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = Attachment.objects.select_related('uploaded_by').all()
        user = self.request.user
        if getattr(user, 'is_authenticated', False):
            qs = qs.filter(task__project_id=user.project_id)
        else:
            project_id = project_id_from(self.request)
            qs = qs.filter(task__project_id=project_id) if project_id else qs.none()
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(
            kind=Attachment.Kind.FILE,
            url='',
            uploaded_by=user if getattr(user, 'is_authenticated', False) else None,
        )

    def perform_destroy(self, instance):
        instance._activity_actor = self.request.user
        instance.delete()


class BootstrapAdminView(APIView):
    """One-time-use endpoint to create/reset an admin when none can log in yet
    (e.g. fresh production database). Disabled unless BOOTSTRAP_SECRET is set
    in the environment; requires that exact secret in the request body."""

    permission_classes = [AllowAny]

    def post(self, request):
        configured_secret = os.environ.get('BOOTSTRAP_SECRET')
        if not configured_secret:
            return Response({'detail': 'Não encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)

        if (request.data.get('secret') or '') != configured_secret:
            return Response({'detail': 'Não encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)

        name = (request.data.get('name') or '').strip()
        password = request.data.get('password') or ''
        role = request.data.get('role') or 'Manager'
        project_name = (request.data.get('project') or '').strip()
        if not name or not password or not project_name:
            return Response({'detail': 'Informe nome, senha e projeto.'}, status=400)

        project, _ = Project.objects.get_or_create(name=project_name)

        person = Person.objects.filter(project=project, name__iexact=name).first()
        if person is None:
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

        return Response({'detail': f'Admin "{person.name}" pronto no projeto "{project.name}".'})


class CheckOverdueView(APIView):
    """Triggers the notify_overdue management command over HTTP, so a free
    external scheduler (cron-job.org, GitHub Actions, UptimeRobot, etc.) can
    ping it periodically without needing Render's paid Cron Jobs. Disabled
    unless CRON_SECRET is set in the environment; requires that exact secret."""

    permission_classes = [AllowAny]

    def post(self, request):
        configured_secret = os.environ.get('CRON_SECRET')
        if not configured_secret:
            return Response({'detail': 'Não encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)

        secret = request.data.get('secret') or request.query_params.get('secret') or ''
        if secret != configured_secret:
            return Response({'detail': 'Não encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)

        out = StringIO()
        call_command('notify_overdue', stdout=out)
        return Response({'detail': out.getvalue().strip()})
