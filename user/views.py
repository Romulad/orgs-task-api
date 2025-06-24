from http import HTTPMethod

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from app_lib.views import FullModelViewSet
from .serializers import (
    UserDetailSerializer,
    CreateUserSerializer,
    UpdateUserSerializer,
    UpdateUserPasswordSerializer,
)
from .models import AppUser as User
from .filters import UserDataFilter
from app_lib.permissions import Is_Object_Or_Org_Or_Depart_Creator


class UserViewSet(FullModelViewSet):
    serializer_class = UserDetailSerializer
    queryset = User.objects.all()
    filterset_class= UserDataFilter

    def get_serializer_class(self):
        if self.action in [
            self.update_view_name, self.partial_update_view_name
        ]:
            return UpdateUserSerializer
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
        if self.action in [self.delete_view_name, self.bulk_delete_view_name]:
            self.permission_classes = [IsAuthenticated, Is_Object_Or_Org_Or_Depart_Creator]
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