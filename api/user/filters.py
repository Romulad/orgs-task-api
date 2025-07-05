from django.db.models.query import Q
from django_filters import filters

from .models import AppUser as User
from app_lib.filter import SearchThroughFilter, CommonFieldsFilter


class UserDataFilter(CommonFieldsFilter, SearchThroughFilter):
    email = filters.CharFilter(
        field_name="email", 
        lookup_expr="exact", 
        label="Exact match"
    )
    email_contains = filters.CharFilter(
        field_name="email", 
        lookup_expr="contains", 
        label="Contains"
    )
    email_startswith = filters.CharFilter(
        field_name="email", 
        lookup_expr="startswith", 
        label="Starts with"
    )
    email_endswith = filters.CharFilter(
        field_name="email", 
        lookup_expr="endswith", 
        label="Ends with"
    )

    first_name = filters.CharFilter(
        field_name="first_name", 
        lookup_expr="exact", 
        label="Exact match"
    )
    first_name_contain = filters.CharFilter(
        field_name="first_name", 
        lookup_expr="contains", 
        label="Contains"
    )
    first_name_startswith = filters.CharFilter(
        field_name="first_name", 
        lookup_expr="startswith", 
        label="Starts with"
    )
    first_name_endswith = filters.CharFilter(
        field_name="first_name", 
        lookup_expr="endswith", 
        label="Ends with"
    )

    last_name = filters.CharFilter(
        field_name="last_name", 
        lookup_expr="exact", 
        label="Exact match"
    )
    last_name_contain = filters.CharFilter(
        field_name="last_name", 
        lookup_expr="contains", 
        label="Contains"
    )
    last_name_startswith = filters.CharFilter(
        field_name="last_name", 
        lookup_expr="startswith", 
        label="Starts with"
    )
    last_name_endswith = filters.CharFilter(
        field_name="last_name", 
        lookup_expr="endswith", 
        label="Ends with"
    )

    def search_through(self, queryset, name, value):
        return queryset.filter(
            Q(email=value) |
            Q(email__contains=value) |
            Q(email__icontains=value) |
            Q(first_name=value) |
            Q(first_name__contains=value) |
            Q(first_name__icontains=value) |
            Q(last_name=value) |
            Q(last_name__contains=value) |
            Q(last_name__icontains=value)
        )
    
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "created_at"
        ]