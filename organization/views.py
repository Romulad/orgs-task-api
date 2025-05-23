from http import HTTPMethod

from rest_framework.permissions import IsAuthenticated
from django.db.models.query import Q
from django.utils.translation import gettext_lazy as _
from django.http.response import Http404
from django.shortcuts import get_object_or_404

from .serializers import (
    OrganizationSerializer,
    CreateOrganizationSerializer,
    UpdateOrganizationSerializer,
    CreateDepartmentSerializer,
    DepartmentSerializer,
    UpdateDepartmentSerializer
)
from .filters import (
    OrganizationDataFilter,
    DepartmentDataFilter
)
from .models import Organization, Department
from app_lib.permissions import (
    CanAccessedObjectInstance,
    IsObjectCreatorOrgCreator
)
from app_lib.global_serializers import (
    BulkDeleteResourceSerializer,
    ChangeUserOwnerListSerializer
)
from app_lib.views import DefaultModelViewSet

class OrganizationViewset(DefaultModelViewSet):
    permission_classes=[IsAuthenticated]
    serializer_class=OrganizationSerializer
    filterset_class=OrganizationDataFilter
    ordering_fields=["name", "description", "created_at"]
    queryset=Organization.objects.prefetch_related(
        "members", "can_be_accessed_by"
    ).select_related("owner", "created_by").order_by("created_at")

    def get_serializer_class(self):
        if self.action == "bulk_delete":
            return BulkDeleteResourceSerializer
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
        return self.get_access_allowed_queryset(
            with_owner_filter=True, with_self_data=False
        )
    
    def get_object(self) -> Organization:
        return super().get_object()

    def get_permissions(self):
        if self.action in [
            "update", "partial_update", "retrieve", "destroy"
        ]:
            self.permission_classes = [
                IsAuthenticated, CanAccessedObjectInstance
            ]
        return super().get_permissions()


class DepartmentViewset(DefaultModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DepartmentSerializer
    filterset_class = DepartmentDataFilter
    ordering_fields=['name', "description", "created_at"]
    queryset = Department.objects.all().select_related(
        "org"
    ).prefetch_related(
        'members'
    ).order_by("created_at")

    def get_serializer_class(self):
        if self.action == "change_owners":
            return ChangeUserOwnerListSerializer
        return super().get_serializer_class()

    def get_serializer(self, *args, **kwargs):
        user = self.request.user
        context = kwargs.get('context', {})
        context["user"] = user
        kwargs["context"] = context
        if self.action == "create":
            org_id = self.kwargs["id"]
            org = self.get_related_org_data(org_id)
            context["org"] = org
            kwargs["context"] = context
            return CreateDepartmentSerializer(*args, **kwargs)
        elif self.action in ["update", "partial_update"]:
            return UpdateDepartmentSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)
    
    def get_object(self):
        org_id = self.kwargs["id"]
        dep_id = self.kwargs["depart_id"]
        org = self.get_related_org_data(org_id)
        depart = get_object_or_404(self.get_queryset(), id=dep_id, org=org)
        self.check_object_permissions(self.request, depart)
        return depart
    
    def get_permissions(self):
        if self.action == "change_owners":
            self.permission_classes = [IsAuthenticated, IsObjectCreatorOrgCreator]
        return super().get_permissions()
    
    def get_queryset(self):
        org_id = self.kwargs["id"]
        org = self.get_related_org_data(org_id)
        return super().get_queryset().filter(org=org)
        
    def get_related_org_data(self, org_id):
        user = self.request.user
        org = Organization.objects.filter(
            Q(
                Q(created_by=user) | 
                Q(owner=user) | 
                Q(can_be_accessed_by__in=[user])
            ),
            id=org_id,
        ).prefetch_related(
            "members", "can_be_accessed_by"
        ).select_related(
            "owner", "created_by"
        )
        if not org:
            raise Http404("Organization can't be found")
        return org[0]