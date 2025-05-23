from http import HTTPMethod

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from app_lib.views import DefaultModelViewSet
from .serializers import (
    UserDetailSerializer,
    CreateUserSerializer,
    UpdateUserSerializer,
    UpdateUserPasswordSerializer,
    ChangeUserOwnerListSerializer
)
from .models import AppUser as User
from .filters import UserDataFilter
from app_lib.authorization import auth_checker
from app_lib.permissions import IsObjectCreatorOrObj

class UserViewSet(DefaultModelViewSet):
    serializer_class = UserDetailSerializer
    queryset = User.objects.all()
    filterset_class= UserDataFilter

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return UpdateUserSerializer
        return super().get_serializer_class()

    def get_serializer(self, *args, **kwargs):
        if self.action == "create":
            kwargs["context"] = self.get_serializer_context()
            return CreateUserSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        if self.action == "list":
            return self.get_access_allowed_queryset(
                with_self_data=False
            )
        return self.get_access_allowed_queryset()
    
    def get_permissions(self):
        if self.action in ["destroy", 'bulk_delete']:
            self.permission_classes = [IsAuthenticated, IsObjectCreatorOrObj]
        return super().get_permissions()

    @action(
        detail=False, 
        methods=[HTTPMethod.GET],
        permission_classes=[IsAuthenticated],
    )
    def me(self, request, *args, **kwargs):
        """Get the authenticated user data"""
        user = request.user
        return Response(
            UserDetailSerializer(user).data
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
        """Change user password"""
        user = request.user
        target_user = self.get_object()
        context = {"user": user, 'target_user': target_user}
        serializer = self.get_serializer(
            target_user, data=request.data, context=context
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, 
        methods=[HTTPMethod.POST],
        permission_classes=[IsAuthenticated, IsObjectCreatorOrObj],
        url_name="change-owners",
        url_path="change-owners",
        serializer_class=ChangeUserOwnerListSerializer
    )
    def change_owners(self, request, *args, **kwargs):
        """Only creator or user itself can set new owner users. 
        _Owner_ is a list of user that have full acccess over the data but can't 
        add new owner.\n
        **Note**: Specific to the user object, a owner added by the creator or user itself 
        can't delete the user data"""
        user = request.user
        target_user = self.get_object()
        context = {"user": user}
        serializer = self.get_serializer(
            target_user, data=request.data, context=context
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
        