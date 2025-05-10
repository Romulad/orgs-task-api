from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models.query import Q
from django.shortcuts import get_object_or_404

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
    queryset=OrganizationSerializer.Meta.model.objects.prefetch_related(
        "members", "can_be_accessed_by").select_related("owner", "created_by").order_by("created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return CreateOrganizationSerializer
        elif self.action in ["update", "partial_update"]:
            return UpdateOrganizationSerializer
        return super().get_serializer_class()

    def get_serializer(self, *args, **kwargs):
        if self.action in [
            "create", "update", "partial_update"
        ]:
            user = self.request.user
            context = kwargs.get("context", {})
            context["user"] = user
            kwargs["context"] = context
        if self.action == "create":
            return CreateOrganizationSerializer(*args, **kwargs)
        elif self.action in ["update", "partial_update"]:
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