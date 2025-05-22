from http import HTTPMethod

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from app_lib.views import DefaultModelViewSet
from .serializers import (
    UserDetailSerializer,
    CreateUserSerializer,
    UpdateUserSerializer
)
from .models import AppUser as User
from .filters import UserDataFilter

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