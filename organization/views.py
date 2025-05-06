from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from .serializers import OrganizationSerializer

class OrganizationViewset(ModelViewSet):
    permission_classes=[IsAuthenticated]
    serializer_class=OrganizationSerializer
    queryset=OrganizationSerializer.Meta.model.objects.all().order_by("created_at")

