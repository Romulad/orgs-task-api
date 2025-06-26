from django.db.models import Q
from rest_framework.permissions import IsAuthenticated

from app_lib.views import FullModelViewSet
from app_lib.queryset import queryset_helpers
from app_lib.permissions import (
    Can_Access_Org_Depart_Or_Obj
)
from .filters import TagDataFilter
from .serializers import (
    TagSerializer,
    TagDetailSerializer,
    CreateTagSerializer,
    UpdateTagSerializer
)

class TagViewSet(FullModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = queryset_helpers.get_tag_queryset(
        include_nested_selected=True, prefetch_org_can_be_accessed_by=True
    ).order_by('created_at')
    serializer_class = TagSerializer
    filterset_class = TagDataFilter
    ordering_fields = ['name', 'description', 'created_at']

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(
            Q(created_by=user) |
            Q(can_be_accessed_by=user) |
            Q(org__created_by=user) |
            Q(org__owner=user) |
            Q(org__can_be_accessed_by=user) |
            Q(org__members=user)
        ).distinct()
    
    def get_serializer_class(self):
        if self.action == self.retrieve_view_name:
            return TagDetailSerializer
        elif self.action in [
            self.update_view_name, self.partial_update_view_name
        ]:
            return UpdateTagSerializer
        elif self.action == self.create_view_name:
            return CreateTagSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        if self.action in [
            self.update_view_name,
            self.partial_update_view_name, 
            self.delete_view_name,
            self.bulk_delete_view_name
        ]:
            self.permission_classes = [IsAuthenticated, Can_Access_Org_Depart_Or_Obj]
        return super().get_permissions()
