from django.db.models.query import Q
from rest_framework.permissions import IsAuthenticated

from app_lib.views import FullModelViewSet
from app_lib.queryset import queryset_helpers
from tasks.serializers import (
    TaskSerializer, 
    TaskDetailSerializer, 
    CreateTaskSerializer,
    UpdateTaskSeriliazer
)
from app_lib.permissions import CanAccessOrgDepartOrObj, IsObjectOrOrgOrDepartCreator
from .filters import TaskDataFilter

class TaskViewSet(FullModelViewSet):
    serializer_class = TaskSerializer
    queryset = queryset_helpers.get_task_queryset().order_by('created_at')
    filterset_class = TaskDataFilter
    ordering_fields = ['name', 'description', "created_at", "status", 'priority']

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TaskDetailSerializer
        elif self.action == "create":
            return CreateTaskSerializer
        elif self.action in ["update", "partial_update"]:
            return UpdateTaskSeriliazer
        return super().get_serializer_class()
    
    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().filter(
            Q(org__created_by=user) |
            Q(org__owner=user) |
            Q(org__can_be_accessed_by__in=[user]) |
            Q(depart__created_by=user) |
            Q(depart__can_be_accessed_by__in=[user]) |
            Q(created_by=user) |
            Q(can_be_accessed_by__in=[user]) |
            Q(assigned_to__in=[user])
        ).distinct()
        return queryset
    
    def get_permissions(self):
        if self.action in [
            "destroy", 'bulk_delete', "update", "partial_update"
        ]:
            self.permission_classes = [IsAuthenticated, CanAccessOrgDepartOrObj]
        elif self.action == "change_owners":
            self.permission_classes = [IsAuthenticated, IsObjectOrOrgOrDepartCreator]
        return super().get_permissions()