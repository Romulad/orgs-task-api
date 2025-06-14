from django_filters import rest_framework as filters
from django.db.models import Q


class CommonFieldsFilter(filters.FilterSet):
    """
    Common filter set that includes fields for filtering by ID and creation date.
    """
    ids = filters.BaseInFilter(
        field_name="id",
        label="Filter by list of id"
    )

    created = filters.IsoDateTimeFromToRangeFilter(
        field_name="created_at",
        label="Date from to",
    )


class SearchThroughFilter(filters.FilterSet):
    """
    Filter set that allows searching through multiple fields.
    This is a placeholder and `search_through` method should be overridden in subclasses.
    """
    search = filters.CharFilter(
        method="search_through",
        label="Search through fields"
    )

    def search_through(self, queryset, name, value):
        return queryset


class BaseNameDescriptionDateDataFilter(CommonFieldsFilter, SearchThroughFilter):
    """
    Base filter set that includes common fields and allows searching through name and description.
    It provides filters for name and description fields with various lookup expressions.
    """
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

    def get_default_search_queryset(self, value):
        return (
            Q(name__contains=value) | 
            Q(name__icontains=value) |
            Q(description__contains=value) |
            Q(description__icontains=value)
        )

    def search_through(self, queryset, name, value):
        return queryset.filter(
            self.get_default_search_queryset(value)
        )

    class Meta:
        model = None
        fields = [
            "id",
            "name",
            "description",
            "created_at",
        ]