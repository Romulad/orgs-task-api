from http import HTTPMethod

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q

from .serializers import (
    AddPermissionsSerializer,
    RemovePermissionsSerializer,
    RoleSerializer,
    RoleDetailSerializer,
    CreateRoleSerializer
)
from .filters import RoleDataFilter
from app_lib.app_permssions import APP_PERMISSIONS
from app_lib.views import FullModelViewSet
from app_lib.queryset import queryset_helpers


@api_view([HTTPMethod.GET])
@permission_classes([IsAuthenticated])
def get_permissions_data(request):
    return Response(APP_PERMISSIONS)


class AddPermissionView(GenericAPIView):
    queryset=None
    serializer_class=AddPermissionsSerializer
    permission_classes=[IsAuthenticated]

    def post(self, request):
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

    def post(self, request):
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
    queryset = queryset_helpers.get_role_queryset()
    filterset_class = RoleDataFilter
    ordering_fields = ['name', 'description', 'created_at', 'org__name']

    def get_serializer_class(self):
        if self.action == "create":
            return CreateRoleSerializer
        elif self.action == "retrieve":
            return RoleDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(
            Q(created_by=user) |
            Q(can_be_accessed_by=user) |
            Q(org__owner=user) | 
            Q(org__created_by=user) | 
            Q(org__can_be_accessed_by=user) |
            Q(org__members=user)
        )