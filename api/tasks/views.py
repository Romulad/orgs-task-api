from http import HTTPMethod

from django.db.models.query import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from app_lib.views import FullModelViewSet
from app_lib.queryset import queryset_helpers
from tasks.serializers import (
    CreateTaskSerializer,
    UpdateTaskSeriliazer,
    UpdateTaskStatusSerializer
)
from app_lib.read_only_serializers import (
    TaskSerializer,
    TaskDetailSerializer,
    CreateUpdateTaskResponseSerializer
)
from app_lib.permissions import Can_Access_Org_Depart_Or_Obj
from app_lib.decorators import schema_wrapper
from .filters import TaskDataFilter


class TaskViewSet(FullModelViewSet):
    serializer_class = TaskSerializer
    queryset = queryset_helpers.get_task_queryset(
        include_nested_selected=True, 
        prefetch_org_can_be_accessed_by=True,
        prefetch_depart_can_be_accessed_by=True
    ).order_by('created_at')
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

    @schema_wrapper(
        CreateTaskSerializer,
        CreateUpdateTaskResponseSerializer,
        status.HTTP_201_CREATED
    )
    def create(self, request, *args, **kwargs):
        """
        # Create a new Task.
        """
        return super().create(request, *args, **kwargs)
    
    @schema_wrapper(
        UpdateTaskSeriliazer,
        CreateUpdateTaskResponseSerializer,
    )
    def update(self, request, *args, **kwargs):
        """
        # Update an existing task with the provided request data.
        """
        return super().update(request, *args, **kwargs)

    @schema_wrapper(
        UpdateTaskSeriliazer,
        CreateUpdateTaskResponseSerializer,
    )
    def partial_update(self, request, *args, **kwargs):
        """
        # Partially updates task with the provided data.
        """
        return super().partial_update(request, *args, **kwargs)

    @schema_wrapper(
        UpdateTaskStatusSerializer,
        UpdateTaskStatusSerializer
    )
    @action(
        detail=True,
        methods=[HTTPMethod.PATCH],
        url_name="update-status",
        url_path='update-status',
        serializer_class=UpdateTaskStatusSerializer
    )
    def update_status(self, request, **kwargs):
        """
        # Update Task status.
        """
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)