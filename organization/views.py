from http import HTTPMethod

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models.query import Q
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.db.transaction import atomic
from rest_framework import status
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
from app_lib.permissions import CanAccessedObjectInstance
from app_lib.global_serializers import BulkDeleteResourceSerializer

class OrganizationViewset(ModelViewSet):
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
        user = self.request.user
        return super().get_queryset().filter(
            Q(created_by=user) | Q(owner=user) | Q(can_be_accessed_by__in=[user])
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

    @action(
        detail=False,
        methods=[HTTPMethod.DELETE],
        url_name="bulk-delete",
        url_path="bulk-delete"
    )
    def bulk_delete(self, request:Request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ressource_ids = serializer.data.get('ids')
        # get ressources
        to_be_deleted = self.get_queryset().filter(id__in=ressource_ids)
        if not to_be_deleted:
            return Response(
                {"detail": _('Orgs not found')},
                status=status.HTTP_404_NOT_FOUND
            )
        # delete ressource
        deleted = [str(deleted.id) for deleted in to_be_deleted]
        not_found = [n_id for n_id in ressource_ids if n_id not in deleted]
        with atomic():
            deleted_count = to_be_deleted.update(is_deleted=True)

        if len(ressource_ids) == deleted_count:
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {
                "deleted": deleted,
                "not_found": not_found
            }
        )
    

class DepartmentViewset(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DepartmentSerializer
    filterset_class = DepartmentDataFilter
    ordering_fields=['name', "description", "created_at"]
    queryset = Department.objects.all().select_related(
        "org"
    ).prefetch_related(
        'members'
    ).order_by("created_at")

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
        return depart
    
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