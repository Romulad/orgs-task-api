from http import HTTPMethod

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q

from .serializers import (
    AddPermissionsSerializer,
    RemovePermissionsSerializer,
    CreateRoleSerializer,
    UpdateRoleSerializer
)
from .filters import RoleDataFilter
from app_lib.app_permssions import get_perm_data, get_perm_list
from app_lib.views import FullModelViewSet
from app_lib.queryset import queryset_helpers
from app_lib.permissions import (
    Can_Access_Org_Or_Obj, 
    Can_Access_Org_Depart_Or_Obj
)
from app_lib.read_only_serializers import (
    RoleSerializer,
    RoleDetailSerializer,
    PermDataSerializer,
    AddPermissionResponseSerializer,
    RemovePermissionResponseSerializer
)
from app_lib.decorators import schema_wrapper


@schema_wrapper(response_serializer=PermDataSerializer(many=True))
@api_view([HTTPMethod.GET])
@permission_classes([IsAuthenticated])
def get_permissions_data(request):
    """
    # Retrieve all available permissions.
    """
    return Response(get_perm_data(get_perm_list()))


class AddPermissionView(GenericAPIView):
    queryset=None
    serializer_class=AddPermissionsSerializer
    permission_classes=[IsAuthenticated]

    @schema_wrapper(
        AddPermissionsSerializer,
        AddPermissionResponseSerializer
    )
    def post(self, request):
        """
        # Add a set of permissions to users
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        added, not_found = serializer.save()
        return Response({
            "added": added,
            "not_found": not_found
        })


class RemovePermissionView(GenericAPIView):
    queryset=None
    serializer_class=RemovePermissionsSerializer
    permission_classes=[IsAuthenticated]

    @schema_wrapper(
        AddPermissionsSerializer,
        RemovePermissionResponseSerializer
    )
    def post(self, request):
        """
        # Remove a set of permissions from users
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        removed, not_found = serializer.save()
        return Response({
            "removed": removed,
            "not_found": not_found
        })


class RoleViewSet(FullModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    queryset = queryset_helpers.get_role_queryset(
        include_nested_selected=True, prefetch_org_can_be_accessed_by=True
    ).order_by("created_at")
    filterset_class = RoleDataFilter
    ordering_fields = ['name', 'description', 'created_at', 'org__name']

    def get_serializer_class(self):
        if self.action == self.create_view_name:
            return CreateRoleSerializer
        elif self.action == self.retrieve_view_name:
            return RoleDetailSerializer
        elif self.action in [self.update_view_name, self.partial_update_view_name]:
            return UpdateRoleSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        if self.action in [
            self.update_view_name, 
            self.partial_update_view_name, 
            self.delete_view_name
        ]:
            self.permission_classes = [IsAuthenticated, Can_Access_Org_Or_Obj]
        elif self.action == self.bulk_delete_view_name:
            self.permission_classes = [IsAuthenticated, Can_Access_Org_Depart_Or_Obj]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().filter(
            Q(created_by=user) |
            Q(can_be_accessed_by=user) |
            Q(org__owner=user) | 
            Q(org__created_by=user) | 
            Q(org__can_be_accessed_by=user) |
            Q(org__members=user)
        ).distinct()
        return queryset