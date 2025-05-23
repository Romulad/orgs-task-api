from http import HTTPMethod

from rest_framework.viewsets import ModelViewSet
from rest_framework.request import Request
from django.db.transaction import atomic
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models.query import Q

from .global_serializers import BulkDeleteResourceSerializer

class DefaultModelViewSet(ModelViewSet):
    permission_classes=[IsAuthenticated]
    permission_classes=[IsAuthenticated]
    serializer_class=None
    filterset_class=None
    ordering_fields=None
    queryset=None


    @action(
        detail=False,
        methods=[HTTPMethod.DELETE],
        url_name="bulk-delete",
        url_path="bulk-delete",
        permission_classes=[IsAuthenticated]
    )
    def bulk_delete(self, request:Request, *args, **kwargs):
        """Deleted specified ressource by ids. Ids are passed in the request body."""
        return self.perform_bulk_delete(request)
    
    def perform_bulk_delete(self, request:Request):
        """Perform bulk delete of ressources. Use data returned by get_queryset"""
        serializer = BulkDeleteResourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ressource_ids = serializer.data.get('ids')
        # get ressources
        to_be_deleted = self.get_queryset().filter(id__in=ressource_ids)
        if not to_be_deleted:
            return Response(
                {"detail": _('Ressource not found')},
                status=status.HTTP_404_NOT_FOUND
            )
        # delete ressources
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
    
    def get_access_allowed_queryset(
            self, 
            with_owner_filter=False,
            with_self_data=True
        ):
        """Return ressources that the user can access"""
        queryset = super().get_queryset()
        user = self.request.user
        filters = Q(created_by=user) | Q(can_be_accessed_by__in=[user])

        if with_owner_filter:
            filters = filters | Q(owner=user)

        if with_self_data:
            filters = filters |  Q(id=user.id)

        return queryset.filter(filters)
    
    def get_forbiden_response(self):
        return Response(
            {"detail": "You don't have enought permission to perform this action"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    def get_no_content_response(self):
        return Response(
            status=status.HTTP_204_NO_CONTENT
        )