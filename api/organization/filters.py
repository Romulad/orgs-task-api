from django_filters import rest_framework as filters
from django.db.models import Q

from .models import Organization, Department
from app_lib.filter import BaseNameDescriptionDateDataFilter

class OrganizationDataFilter(BaseNameDescriptionDateDataFilter):
    def search_through(self, queryset, name, value):
        return super().search_through(
            queryset, name, value
        ).filter(
            Q(members__in=[value])
        )
    
    class Meta:
        model = Organization
        fields = [
            'id',
            "name",
            "description",
            "members",
            "created_at",
        ]


class DepartmentDataFilter(BaseNameDescriptionDateDataFilter):
    def search_through(self, queryset, name, value):
        return super().search_through(
            queryset, name, value
        ).filter(
            Q(members__in=[value])
        )
    
    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "description",
            "members",
            "created_at",
        ]