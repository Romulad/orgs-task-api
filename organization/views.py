from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models.query import Q

from .serializers import (
    OrganizationSerializer,
    CreateOrganizationSerializer
)
from .filters import (
    OrganizationDataFilter
)

class OrganizationViewset(ModelViewSet):
    permission_classes=[IsAuthenticated]
    serializer_class=OrganizationSerializer
    filterset_class=OrganizationDataFilter
    ordering_fields=["name", "description", "created_at"]
    queryset=OrganizationSerializer.Meta.model.objects.all().order_by("created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return CreateOrganizationSerializer
        return super().get_serializer_class()

    def get_serializer(self, *args, **kwargs):
        user = self.request.user
        if self.action == "create":
            kwargs.setdefault("context", {"user": user})
            return CreateOrganizationSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(
            Q(owner=user) | Q(can_be_accessed_by__in=[user])
        )