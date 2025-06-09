from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    AddPermissionsSerializer,
    RemovePermissionsSerializer
)


class AddPermissionView(GenericAPIView):
    queryset=None
    serializer_class=AddPermissionsSerializer
    permission_classes=[IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        added, not_found = serializer.save()
        return Response({
            "added": added,
            "not_found": not_found
        })


class RemovePermissionView(GenericAPIView):
    queryset=None
    serializer_class=RemovePermissionsSerializer
    permission_classes=[IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        removed, not_found = serializer.save()
        return Response({
            "removed": removed,
            "not_found": not_found
        })