from app_lib.views import DefaultModelViewSet
from .serializers import (
    UserSerializer,
    CreateUserSerializer,
)
from .models import AppUser as User

class UserViewSet(DefaultModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def get_serializer(self, *args, **kwargs):
        if self.action == "create":
            kwargs["context"] = self.get_serializer_context()
            return CreateUserSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        return self.get_user_access_allowed_queryset()