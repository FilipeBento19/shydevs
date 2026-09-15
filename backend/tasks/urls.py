from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityViewSet, AttachmentViewSet, BootstrapAdminView, CommentViewSet, LoginView, LogoutView,
    MeView, PersonViewSet, ProjectViewSet, RoleViewSet, SubtaskViewSet, TaskViewSet,
)

router = DefaultRouter()
router.register('projects', ProjectViewSet, basename='project')
router.register('people', PersonViewSet, basename='person')
router.register('tasks', TaskViewSet, basename='task')
router.register('roles', RoleViewSet, basename='role')
router.register('subtasks', SubtaskViewSet, basename='subtask')
router.register('activities', ActivityViewSet, basename='activity')
router.register('attachments', AttachmentViewSet, basename='attachment')
router.register('comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('auth/login/', LoginView.as_view()),
    path('auth/logout/', LogoutView.as_view()),
    path('auth/me/', MeView.as_view()),
    path('bootstrap-admin/', BootstrapAdminView.as_view()),
] + router.urls
