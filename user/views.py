from http import HTTPMethod

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from app_lib.views import FullModelViewSet
from app_lib.queryset import queryset_helpers
from app_lib.decorators import schema_wrapper
from app_lib.read_only_serializers import (
    UserSerializer,
    UserDetailSerializer,
)
from .serializers import (
    CreateUserSerializer,
    UpdateUserSerializer,
    UpdateUserPasswordSerializer,
)
from .filters import UserDataFilter
from app_lib.permissions import Is_Object_Or_Org_Or_Depart_Creator


class UserViewSet(FullModelViewSet):
    serializer_class = UserSerializer
    queryset = queryset_helpers.get_user_queryset().order_by('created_at')
    filterset_class= UserDataFilter

    def get_serializer_class(self):
        if self.action in [
            self.update_view_name, self.partial_update_view_name
        ]:
            return UpdateUserSerializer
        elif self.action == self.retrieve_view_name:
            return UserDetailSerializer
        return super().get_serializer_class()

    def get_serializer(self, *args, **kwargs):
        if self.action == self.create_view_name:
            kwargs["context"] = self.get_serializer_context()
            return CreateUserSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        if self.action == self.list_view_name:
            return self.get_access_allowed_queryset(
                with_self_data=False
            )
        return self.get_access_allowed_queryset()
    
    def get_permissions(self):
        if self.action in [self.delete_view_name]:
            self.permission_classes = [IsAuthenticated, Is_Object_Or_Org_Or_Depart_Creator]
        return super().get_permissions()

    @schema_wrapper(
        CreateUserSerializer,
        CreateUserSerializer,
        status.HTTP_201_CREATED
    )
    def create(self, request, *args, **kwargs):
        """# Creates an user.
        This endpoint allows an authenticated user to create a new user account.
        On success, the user is created and a notification email is sent to the newly created user.
        """
        return super().create(request, *args, **kwargs)
    
    @schema_wrapper(response_serializer=UserSerializer)
    def list(self, request, *args, **kwargs):
        """
        # Get users
        Retrieves a paginated list of user data accessible to the authenticated user.
        """
        return super().list(request, *args, **kwargs)

    @schema_wrapper(response_serializer=UserDetailSerializer)
    def retrieve(self, request, *args, **kwargs):
        """
        # Retrieve a user's data.
        Returns the details of a user specified by the request.
        Allows users to retrieve their own data or other user's data.
        """
        return super().retrieve(request, *args, **kwargs)
    
    @schema_wrapper(
        UpdateUserSerializer,
        UpdateUserSerializer
    )
    def update(self, request, *args, **kwargs):
        """
        # Update an user data.
        All fields should be present.
        """
        return super().update(request, *args, **kwargs)
    
    @schema_wrapper(
        UpdateUserSerializer,
        UpdateUserSerializer
    )
    def partial_update(self, request, *args, **kwargs):
        """
        # Update field(s) on the user data.
        """
        return super().partial_update(request, *args, **kwargs)
    
    @schema_wrapper()
    def destroy(self, request, *args, **kwargs):
        """
        # Deletes a user instance. 
        The deletion is performed by marking the user as deleted by default.
        """
        return super().destroy(request, *args, **kwargs)

    @schema_wrapper()
    @action(
        detail=False,
        methods=[HTTPMethod.DELETE],
        url_name="bulk-delete",
        url_path="bulk-delete",
        permission_classes=[IsAuthenticated, Is_Object_Or_Org_Or_Depart_Creator]
    )
    def bulk_delete(self, request, *args, **kwargs):
        """
        # Handles bulk deletion of user resources.

        **Note** : Only user itself or his creator can perform this action

        This endpoint allows authenticated user to request the deletion of multiple user 
        resources by providing their IDs using an `ids` field in the request data. 

        If the request contains user IDs that the authenticated user does not have permission to delete, 
        an error response is returned.
        
        Resources are not physically deleted but are marked as deleted. On successful deletion, 
        a 204 No Content response is returned.

        If the request includes a mix of accessible and non-existent user IDs, a success response is 
        returned detailing which resources were deleted and which IDs were not found.
        
        If all provided IDs are not found, a 404 error response is returned with an 
        appropriate error message.
        """
        return super().bulk_delete(request, *args, **kwargs)
    
    @schema_wrapper(
        response_serializer=UserDetailSerializer
    )
    @action(
        detail=False, 
        methods=[HTTPMethod.GET],
        permission_classes=[IsAuthenticated],
    )
    def me(self, request, *args, **kwargs):
        """# Get the authenticated user data"""
        user = request.user
        return Response(
            UserDetailSerializer(user).data
        )

    @schema_wrapper(
        request_serializer=UpdateUserPasswordSerializer,
        response_status_code=status.HTTP_204_NO_CONTENT
    )
    @action(
        detail=True, 
        methods=[HTTPMethod.POST],
        permission_classes=[IsAuthenticated],
        url_name="change-password",
        url_path="change-password",
        serializer_class=UpdateUserPasswordSerializer
    )
    def change_password(self, request, *args, **kwargs):
        """# Change user password"""
        user = request.user
        target_user = self.get_object()
        context = {"user": user, 'target_user': target_user}
        serializer = self.get_serializer(
            target_user, data=request.data, context=context
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT) 