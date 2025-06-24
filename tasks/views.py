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
from app_lib.permissions import Can_Access_Org_Depart_Or_Obj
from .filters import TaskDataFilter

class TaskViewSet(FullModelViewSet):
    serializer_class = TaskSerializer
    queryset = queryset_helpers.get_task_queryset().order_by('created_at')
    filterset_class = TaskDataFilter
    ordering_fields = ['name', 'description', "created_at", "status", 'priority']

    def get_serializer_class(self):
        if self.action == self.retrieve_view_name:
            return TaskDetailSerializer
        elif self.action == self.create_view_name:
            return CreateTaskSerializer
        elif self.action in [
            self.update_view_name, 
            self.partial_update_view_name
        ]:
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
            self.delete_view_name, 
            self.bulk_delete_view_name, 
            self.update_view_name, 
            self.partial_update_view_name,
        ]:
            self.permission_classes = [IsAuthenticated, Can_Access_Org_Depart_Or_Obj]
        return super().get_permissions()