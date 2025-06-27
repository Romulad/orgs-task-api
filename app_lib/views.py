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
from django.shortcuts import get_object_or_404

from .global_serializers import (
    BulkDeleteResourceSerializer,
    ChangeUserOwnerListSerializer
)
from .authorization import auth_checker
from .decorators import schema_wrapper
from .app_permssions import CAN_CHANGE_RESSOURCES_OWNERS
from .permissions import Is_Object_Or_Org_Or_Depart_Creator
from organization.models import Organization


class BulkDeleteResourceMixin:
    bulk_delete_view_name = "bulk_delete"

    @schema_wrapper(
        request_serializer=BulkDeleteResourceSerializer
    )
    @action(
        detail=False,
        methods=[HTTPMethod.DELETE],
        url_name="bulk-delete",
        url_path="bulk-delete",
        permission_classes=[IsAuthenticated]
    )
    def bulk_delete(self, request:Request, *args, **kwargs):
        """
        # Handles bulk deletion of resources.

        This endpoint allows authenticated users to request the deletion of multiple 
        resources by providing their IDs using an `ids` field in the request data. 

        If the request contains ressource IDs that the authenticated user does not have permission to delete, 
        an error response is returned.
        
        Resources are not physically deleted but are marked as deleted. On successful deletion, 
        a 204 No Content response is returned.

        If the request includes a mix of accessible and non-existent ressource IDs, a success 200 
        response is returned detailing which resources were deleted and which IDs were not found.
        
        If all provided IDs are not found, a 404 error response is returned with an 
        appropriate error message.
        """
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
    
    @schema_wrapper(
        request_serializer=ChangeUserOwnerListSerializer,
        response_status_code=status.HTTP_204_NO_CONTENT
    )
    @action(
        detail=True, 
        methods=[HTTPMethod.POST],
        permission_classes=[IsAuthenticated, Is_Object_Or_Org_Or_Depart_Creator],
        url_name="change-owners",
        url_path="change-owners",
        serializer_class=ChangeUserOwnerListSerializer
    )
    def change_owners(self, request, *args, **kwargs):
        """
        # Change the owners of a target object.
        This endpoint allows an authenticated user to update the list of owners for a specific object.
        """
        user = request.user
        target_obj = self.get_obj_to_change_owners_for()
        context = {"user": user}
        serializer = self.get_serializer(
            target_obj, data=request.data, context=context
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def get_obj_to_change_owners_for(self):
        """
        Get the target object and check if user has permission to change 
        owners, may raise a permission error.
        """
        user = self.request.user
        obj = self.get_raw_object()

        # check if the user has CAN_CHANGE_RESSOURCES_OWNERS perm in the org otherwise 
        # apply the default permission checking
        has_org = hasattr(obj, 'org') and getattr(obj.org, 'id', None)
        if (
            isinstance(obj, Organization) and
            auth_checker.has_permission(user, obj, CAN_CHANGE_RESSOURCES_OWNERS)
        ):
            return obj
        elif (
            has_org and 
            auth_checker.has_permission(user, obj.org, CAN_CHANGE_RESSOURCES_OWNERS)
        ):
            return obj

        return self.get_object()   

class DefaultModelViewSet(ModelViewSet):
    """Extends `ModelViewSet` to add common methods needed in the system"""
    permission_classes=[IsAuthenticated]
    serializer_class=None
    filterset_class=None
    ordering_fields=None
    queryset=None
    # actions name
    create_view_name = "create"
    update_view_name = "update"
    partial_update_view_name = "partial_update"
    retrieve_view_name = "retrieve"
    list_view_name = "list"
    delete_view_name = "destroy"

    def get_raw_object(self):
        """
        Returns the object to use in a detail view without filtering.
        Raise not found error if needed.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        return get_object_or_404(self.get_raw_queryset(), **filter_kwargs)

    def get_raw_queryset(self):
        """
        Returns the queryset without any filtering as provided in
        `.queryset` attribute. 
        """
        return super().get_queryset()

    def get_access_allowed_queryset(
            self, 
            with_owner_filter=False,
            with_self_data=True,
            filters=None
        ):
        """Return ressources that the user can access"""
        queryset = super().get_queryset()

        if filters:
            return queryset.filter(filters)
        
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
    ChangeObjectOwnersMixin,
):
    """Add common behavior needed by a typical model in the system"""
    pass