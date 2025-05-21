from app_lib.views import DefaultModelViewSet
from .serializers import (
    UserSerializer,
    CreateUserSerializer,
)
from .models import AppUser as User
from .filters import UserDataFilter

class UserViewSet(DefaultModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    filterset_class= UserDataFilter

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