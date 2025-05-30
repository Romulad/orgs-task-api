from django.db.models.query import Q
from rest_framework.permissions import IsAuthenticated

from app_lib.views import FullModelViewSet
from app_lib.queryset import queryset_helpers
from tasks.serializers import (
    TaskSerializer, 
    TaskDetailSerializer, 
    CreateTaskSerializer
)
from app_lib.permissions import CanAccessOrgDepartOrObj
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
        )
        return queryset
    
    def get_permissions(self):
        if self.action == "destroy":
            self.permission_classes = [IsAuthenticated, CanAccessOrgDepartOrObj]
        return super().get_permissions()