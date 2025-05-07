from django_filters import rest_framework as filters
from django.db.models import Q

from .models import Organization

class OrganizationDataFilter(filters.FilterSet):
    name = filters.CharFilter(
        field_name="name", 
        lookup_expr="exact", 
        label="Name exact match"
    )
    name_contain = filters.CharFilter(
        field_name="name", 
        lookup_expr="contains", 
        label="Name contains"
    )
    name_startswith = filters.CharFilter(
        field_name="name", 
        lookup_expr="startswith", 
        label="Name starts with"
    )
    name_endswith = filters.CharFilter(
        field_name="name", 
        lookup_expr="endswith", 
        label="Name ends with"
    )

    description_contains = filters.CharFilter(
        field_name="description", 
        lookup_expr="contains", 
        label="Description contains"
    )
    description_startswith = filters.CharFilter(
        field_name="description", 
        lookup_expr="startswith", 
        label="Description starts with"
    )
    description_endswith = filters.CharFilter(
        field_name="description", 
        lookup_expr="endswith", 
        label="Description ends with"
    )

    created = filters.DateTimeFromToRangeFilter(
        field_name="created_at",
        label="Date from to",
    )

    search = filters.CharFilter(
        method="search_through",
        label="Search through fields"
    )

    def search_through(self, queryset, name, value):
        return queryset.filter(
            Q(name__contains=value) |
            Q(name__icontains=value) |
            Q(description__contains=value) |
            Q(description__icontains=value) |
            Q(members__in=[value])
        )

    class Meta:
        model = Organization
        fields = [
            "name",
            "description",
            "members",
            "created_at",
        ]