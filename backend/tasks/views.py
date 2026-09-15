import os

from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status as http_status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Activity, Attachment, AuthToken, Comment, Person, Priority, ProjectSettings, Role, Status, Subtask, Task,
)
from .serializers import (
    ActivitySerializer, AttachmentSerializer, CommentSerializer, PersonSerializer, RoleSerializer,
    SubtaskSerializer, TaskSerializer,
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


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        password = request.data.get('password') or ''
        try:
            person = Person.objects.get(name__iexact=name)
        except Person.DoesNotExist:
            return Response({'detail': 'Credenciais inválidas.'}, status=http_status.HTTP_401_UNAUTHORIZED)

        if not person.check_password(password):
            return Response({'detail': 'Credenciais inválidas.'}, status=http_status.HTTP_401_UNAUTHORIZED)

        token, _ = AuthToken.objects.get_or_create(
            person=person, defaults={'key': AuthToken.generate_key()}
        )
        return Response({'token': token.key, 'person': PersonSerializer(person).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        AuthToken.objects.filter(person=request.user).delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PersonSerializer(request.user).data)


class PersonViewSet(viewsets.ModelViewSet):
    queryset = Person.objects.all().order_by('name')
    serializer_class = PersonSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_permissions(self):
        if self.action in ('photo', 'change_password'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def _would_remove_last_admin(self, instance, validated_data):
        becoming_non_admin = 'is_admin' in validated_data and not validated_data['is_admin']
        return (
            instance.is_admin and becoming_non_admin
            and Person.objects.filter(is_admin=True).exclude(pk=instance.pk).count() == 0
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
        if instance.is_admin and Person.objects.filter(is_admin=True).exclude(pk=instance.pk).count() == 0:
            return Response({'detail': 'Precisa existir pelo menos um administrador.'}, status=400)
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
        return Response({'detail': 'Senha alterada com sucesso.'})


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        in_use = Task.objects.filter(role=instance.name).exists() or instance.people.exists()
        if in_use:
            return Response(
                {'detail': 'Esse cargo está em uso por pessoas ou tarefas e não pode ser removido.'},
                status=400,
            )
        return super().destroy(request, *args, **kwargs)


OWNER_EDITABLE_FIELDS = {'status', 'completion_note'}


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [TaskPermission]

    def get_permissions(self):
        if self.action == 'bulk_update':
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

    def _actor(self):
        user = self.request.user
        return user if getattr(user, 'is_authenticated', False) else None

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['role_colors'] = dict(Role.objects.values_list('name', 'color'))
        return context

    @action(detail=False, methods=['get'])
    def balance(self, request):
        best = None
        for role in Role.objects.all():
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
        tasks = list(Task.objects.select_related('assignee').all())
        total = len(tasks)
        by_status = {s.value: sum(1 for t in tasks if t.status == s.value) for s in Status}
        by_role = {r.name: sum(1 for t in tasks if t.role == r.name) for r in Role.objects.all()}
        by_priority = {p.value: sum(1 for t in tasks if t.priority == p.value) for p in Priority}

        overdue = sum(1 for t in tasks if t.due_date and t.due_date < timezone.now().date() and t.status != Status.CONCLUIDA)

        people = list(Person.objects.prefetch_related('roles').all())
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

        qs = Task.objects.filter(id__in=ids)
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
        deleted, _ = Task.objects.filter(id__in=ids).delete()
        return Response({'deleted': deleted})


class SubtaskViewSet(viewsets.ModelViewSet):
    serializer_class = SubtaskSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Subtask.objects.all()
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Activity.objects.select_related('actor', 'task').all()
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs[:200]


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
        qs = Comment.objects.select_related('author', 'task').all()
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs

    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)
        Activity.objects.create(
            task=comment.task,
            actor=self.request.user,
            message=f'{self.request.user.name} comentou na tarefa',
        )


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
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(uploaded_by=user if getattr(user, 'is_authenticated', False) else None)


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
        if not name or not password:
            return Response({'detail': 'Informe nome e senha.'}, status=400)

        person = Person.objects.filter(name__iexact=name).first()
        if person is None:
            person = Person(name=name, is_admin=True)
        else:
            person.is_admin = True
        person.set_password(password)
        person.save()
        role_obj = Role.objects.filter(name=role).first()
        if role_obj and not person.roles.filter(pk=role_obj.pk).exists():
            person.roles.add(role_obj)

        return Response({'detail': f'Admin "{person.name}" pronto.'})


class ProjectSettingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'name': ProjectSettings.load().name})

    def patch(self, request):
        user = request.user
        if not (user and getattr(user, 'is_authenticated', False) and getattr(user, 'is_admin', False)):
            return Response({'detail': 'Apenas administradores.'}, status=http_status.HTTP_403_FORBIDDEN)
        name = (request.data.get('name') or '').strip()
        if not name:
            return Response({'detail': 'Nome inválido.'}, status=400)
        settings_obj = ProjectSettings.load()
        settings_obj.name = name[:120]
        settings_obj.save()
        return Response({'name': settings_obj.name})
