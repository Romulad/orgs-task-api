from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models.query import Q

from .serializers import (
    OrganizationSerializer,
    CreateOrganizationSerializer,
    UpdateOrganizationSerializer
)
from .filters import (
    OrganizationDataFilter
)
from app_lib.permissions import CanAccessedObjectInstance

class OrganizationViewset(ModelViewSet):
    permission_classes=[IsAuthenticated]
    serializer_class=OrganizationSerializer
    filterset_class=OrganizationDataFilter
    ordering_fields=["name", "description", "created_at"]
    queryset=OrganizationSerializer.Meta.model.objects.all().prefetch_related(
        "members").select_related("owner").order_by("created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return CreateOrganizationSerializer
        elif self.action in ["update", "partial_update"]:
            return UpdateOrganizationSerializer
        return super().get_serializer_class()

    def get_serializer(self, *args, **kwargs):
        user = self.request.user
        if self.action == "create":
            kwargs.setdefault("context", {"user": user})
            return CreateOrganizationSerializer(*args, **kwargs)
        elif self.action in ["update", "partial_update"]:
            kwargs.setdefault("context", {"user": user})
            return UpdateOrganizationSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(
            Q(owner=user) | Q(can_be_accessed_by__in=[user])
        )

    def get_permissions(self):
        if self.action in [
            "update", "partial_update", "retrieve", "destroy"
        ]:
            self.permission_classes = [
                IsAuthenticated, CanAccessedObjectInstance
            ]
        return super().get_permissions()