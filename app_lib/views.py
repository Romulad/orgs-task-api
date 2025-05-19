from rest_framework.viewsets import ModelViewSet
from rest_framework.request import Request
from django.db.transaction import atomic
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext_lazy as _

from .global_serializers import BulkDeleteResourceSerializer

class DefaultModelViewSet(ModelViewSet):
    
    def bulk_delete(self, request:Request, *arg, **kwargs):
        """Deleted specified ressource ids. Ids are passed in the request body."""
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