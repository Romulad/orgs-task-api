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

from .serializers import (
    OrganizationSerializer,
    CreateOrganizationSerializer,
    UpdateOrganizationSerializer,
    CreateDepartmentSerializer,
    DepartmentSerializer
)
from .filters import (
    OrganizationDataFilter,
    DepartmentDataFilter
)
from .models import Organization
from app_lib.permissions import CanAccessedObjectInstance
from app_lib.global_serializers import BulkDeleteResourceSerializer


class OrganizationViewset(ModelViewSet):
    permission_classes=[IsAuthenticated]
    serializer_class=OrganizationSerializer
    filterset_class=OrganizationDataFilter
    ordering_fields=["name", "description", "created_at"]
    queryset=Organization.objects.prefetch_related(
        "members", "can_be_accessed_by", "departments"
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
            Q(owner=user) | Q(can_be_accessed_by__in=[user])
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

    def get_queryset_list_response(self, all_queryset, filter_class=None):
        if filter_class is not None:
            setattr(self, "filterset_class", filter_class)
        queryset = self.filter_queryset(all_queryset)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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

    @action(
        methods=[HTTPMethod.POST],
        detail=True,
        url_name='create-department',
        url_path='create-department',
        serializer_class=CreateDepartmentSerializer,
        permission_classes=[
            IsAuthenticated, CanAccessedObjectInstance
        ]
    )
    def create_department(self, request:Request, pk=None):
        user = request.user
        org = self.get_object()
        serializer = self.get_serializer(
            data=request.data, context={"user":user, 'org': org}
        )
        serializer.is_valid(raise_exception=True)
        created = serializer.save()
        return Response(
            self.get_serializer_class()(created).data,
            status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        url_name='list-department',
        url_path='list-department',
        methods=[HTTPMethod.GET],
        serializer_class=DepartmentSerializer,
        permission_classes=[
            IsAuthenticated, CanAccessedObjectInstance
        ],
        filterset_class=None,
        ordering_fields=['name', "description", "created_at"]
    )
    def list_department(self, request:Request, pk=None):
        org = self.get_object()
        queryset = org.departments.all()
        return self.get_queryset_list_response(queryset, DepartmentDataFilter)

    @action(
        detail=True,
        url_name='update-department',
        url_path='update-department',
        methods=[HTTPMethod.PUT],
        serializer_class=UpdateDepartmentSerializer,
        permission_classes=[
            IsAuthenticated, CanAccessedObjectInstance
        ],
    )
    def update_department(self, request:Request, pk=None):
        org = self.get_object()