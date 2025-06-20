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
from django.http.response import Http404

from .global_serializers import (
    BulkDeleteResourceSerializer,
    ChangeUserOwnerListSerializer
)
from .permissions import Is_Object_Creator_Or_Obj


class BulkDeleteResourceMixin:
    bulk_delete_view_name = "bulk_delete"

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

    def get_ressources_queryset(self, ressource_ids):
        return self.get_queryset().filter(id__in=ressource_ids)
    
    def perform_bulk_delete(self, request:Request):
        """Perform bulk delete of ressources. Use data returned by get_queryset"""
        serializer = BulkDeleteResourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ressource_ids = serializer.data.get('ids')

        # get ressources
        to_be_deleted = self.get_ressources_queryset(ressource_ids)
        if not to_be_deleted:
            return self.get_not_found_error()
        
        # check for user permission over objects, potentially return a forbiden response
        self.check_objects_permissions(request, to_be_deleted)

        # delete ressources
        deleted = [str(deleted.id) for deleted in to_be_deleted]
        not_found = [n_id for n_id in ressource_ids if n_id not in deleted]
        with atomic():
            to_be_deleted.delete()

        if not_found:
            return Response(
                {
                    "deleted": deleted,
                    "not_found": not_found
                }
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangeObjectOwnersMixin:
    owner_view_name = "change_owners"
    
    @action(
        detail=True, 
        methods=[HTTPMethod.POST],
        permission_classes=[IsAuthenticated, Is_Object_Creator_Or_Obj],
        url_name="change-owners",
        url_path="change-owners",
        serializer_class=ChangeUserOwnerListSerializer
    )
    def change_owners(self, request, *args, **kwargs):
        """Only creator can set owner users. _Owner_ is a list of user that 
        have full acccess over the data but can't add new owner user.\n
        **Only for user data**: User itself can set owner users, owner added by the creator or user itself 
        can't delete user data"""
        user = request.user
        target_obj = self.get_object()
        context = {"user": user}
        serializer = self.get_serializer(
            target_obj, data=request.data, context=context
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class DefaultModelViewSet(ModelViewSet):
    """Extends `ModelViewSet` to add common methods needed in the system"""
    permission_classes=[IsAuthenticated]
    serializer_class=None
    filterset_class=None
    ordering_fields=None
    queryset=None

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

    def check_objects_permissions(self, request, objs):
        """
        Check if the request should be permitted for a set of objects.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in self.get_permissions():
            checker = getattr(permission, "has_objects_permission", None)
            if checker and not checker(request, self, objs):
                self.permission_denied(
                    request,
                    message=getattr(permission, 'message', None),
                    code=getattr(permission, 'code', None)
                )
    
    def get_forbiden_response(self):
        return Response(
            {"detail": "You don't have enought permission to perform this action"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    def get_no_content_response(self):
        return Response(
            status=status.HTTP_204_NO_CONTENT
        )
    
    def get_not_found_error(self):
        return Response(
            {"detail": _('Ressource not found')},
            status=status.HTTP_404_NOT_FOUND
        )
    
    def raise_not_found_error(self):
        raise Http404("Ressource can't be found")


class FullModelViewSet(
    DefaultModelViewSet, 
    BulkDeleteResourceMixin, 
    ChangeObjectOwnersMixin
):
    """Add common behavior needed by a typical model in the system"""
    pass