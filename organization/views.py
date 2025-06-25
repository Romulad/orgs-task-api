from rest_framework.permissions import IsAuthenticated
from django.db.models.query import Q
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

from .serializers import (
    OrganizationSerializer,
    OrganizationDetailSerializer,
    CreateOrganizationSerializer,
    UpdateOrganizationSerializer,
    CreateDepartmentSerializer,
    DepartmentSerializer,
    DepartmentDeailSerializer,
    UpdateDepartmentSerializer
)
from .filters import (
    OrganizationDataFilter,
    DepartmentDataFilter
)
from .models import Organization
from app_lib.permissions import (
    Can_Access_ObjectInstance,
    Is_Object_Or_Org_Or_Depart_Creator,
    Can_Access_Org_Depart_Or_Obj
)
from app_lib.global_serializers import (
    ChangeUserOwnerListSerializer
)
from app_lib.views import FullModelViewSet
from app_lib.queryset import queryset_helpers
from app_lib.authorization import auth_checker
from app_lib.app_permssions import CAN_CREATE_DEPART

class OrganizationViewset(FullModelViewSet):
    permission_classes=[IsAuthenticated]
    serializer_class=OrganizationSerializer
    filterset_class=OrganizationDataFilter
    ordering_fields=["name", "description", "created_at"]
    queryset=queryset_helpers.get_org_queryset().order_by("created_at")

    def get_serializer_class(self):
        if self.action == self.retrieve_view_name:
            return OrganizationDetailSerializer
        return super().get_serializer_class()
    
    def get_serializer(self, *args, **kwargs):
        if self.action in [
            self.create_view_name, 
            self.update_view_name, 
            self.partial_update_view_name
        ]:
            user = self.request.user
            context = kwargs.get("context", {})
            context["user"] = user
            kwargs["context"] = context
        if self.action == "create":
            return CreateOrganizationSerializer(*args, **kwargs)
        elif self.action in [self.update_view_name, self.partial_update_view_name]:
            return UpdateOrganizationSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(
            Q(created_by=user) |
            Q(owner=user) |
            Q(can_be_accessed_by=user) |
            Q(members=user)
        )
    
    def get_object(self) -> Organization:
        return super().get_object()

    def get_permissions(self):
        if self.action in [
            self.update_view_name, 
            self.partial_update_view_name, 
            self.delete_view_name,
            self.bulk_delete_view_name
        ]:
            self.permission_classes = [
                IsAuthenticated, Can_Access_ObjectInstance
            ]
        
        return super().get_permissions()


class DepartmentViewset(FullModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DepartmentSerializer
    filterset_class = DepartmentDataFilter
    ordering_fields=['name', "description", "created_at"]
    queryset = queryset_helpers.get_depart_queryset().order_by("created_at")
    lookup_url_kwarg = "depart_id"

    def get_serializer_class(self):
        if self.action == self.owner_view_name:
            return ChangeUserOwnerListSerializer
        elif self.action == self.retrieve_view_name:
            return DepartmentDeailSerializer
        return super().get_serializer_class()

    def get_serializer(self, *args, **kwargs):
        user = self.request.user
        context = kwargs.get('context', {})
        context["user"] = user
        kwargs["context"] = context
        if self.action == self.create_view_name:
            org_id = self.kwargs["id"]
            org = self.get_related_org_data_or_404(org_id)
            context["org"] = org
            kwargs["context"] = context
            return CreateDepartmentSerializer(*args, **kwargs)
        elif self.action in [
            self.update_view_name, 
            self.partial_update_view_name
        ]:
            return UpdateDepartmentSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)
    
    def get_object(self):
        org_id = self.kwargs["id"]
        dep_id = self.kwargs["depart_id"]
        queryset = self.get_queryset()
        depart = get_object_or_404(queryset, id=dep_id, org__id=org_id)
        self.check_object_permissions(self.request, depart)
        return depart
    
    def get_permissions(self):
        if self.action == self.owner_view_name:
            self.permission_classes = [IsAuthenticated, Is_Object_Or_Org_Or_Depart_Creator]
        if self.action in [
            self.update_view_name, 
            self.partial_update_view_name, 
            self.delete_view_name,
            self.bulk_delete_view_name
        ]:
            self.permission_classes = [IsAuthenticated, Can_Access_Org_Depart_Or_Obj]
        return super().get_permissions()
    
    def get_queryset(self):
        org_id = self.kwargs["id"]
        user = self.request.user
        queryset = super().get_queryset().filter(
            Q(org__id=org_id),
            (
                Q(org__created_by=user) |
                Q(org__owner=user) |
                Q(org__can_be_accessed_by__in=[user]) |
                Q(created_by=user) |
                Q(can_be_accessed_by__in=[user]) |
                Q(members=user)
            )
        ).distinct()
        return queryset

    def get_related_org_data(self, org_id):
        user = self.request.user

        org = queryset_helpers.get_org_queryset().filter(
            id=org_id
        )
        if not org:
            return None
        
        org = org[0]
        
        if auth_checker.has_access_to_obj(org, user):
            return org
        
        if auth_checker.has_permission(
            user, org, CAN_CREATE_DEPART
        ):
            return org
        
        return None
    
    def get_related_org_data_or_404(self, org_id):
        org = self.get_related_org_data(org_id)
        if not org:
            self.raise_not_found_error()
        return org

    def get_obj_to_change_owners_for(self):
        obj = super().get_obj_to_change_owners_for()
        # ensure the org exists
        get_object_or_404(Organization, id=self.kwargs["id"])
        return obj

