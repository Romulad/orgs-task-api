from django_filters import rest_framework as filters
from django.db.models.query import Q

from app_lib.filter import BaseNameDescriptionDateDataFilter as BaseFilter
from .models import Task

class  TaskDataFilter(BaseFilter):
    assigned_to_ids = filters.BaseInFilter(
        label="Filter by assigned user ids",
        lookup_expr="id__in",
        field_name="assigned_to"
    )
    assigned_to_emails = filters.BaseInFilter(
        label="Filter by assigned user emails",
        lookup_expr="email__in",
        field_name="assigned_to"
    )
    assigned_to_first_names = filters.BaseInFilter(
        label="Filter by assigned user first_names",
        lookup_expr="first_name__in",
        field_name="assigned_to"
    )

    due_date = filters.IsoDateTimeFromToRangeFilter()

    tag_ids = filters.BaseInFilter(
        label="Filter by tag ids",
        lookup_expr="id__in",
        field_name="tags"
    )
    tag_names = filters.BaseInFilter(
        label="Filter by tag name",
        lookup_expr="name__in",
        field_name="tags"
    )

    def search_through(self, queryset, name, value):
        return queryset.filter(
            self.get_default_search_queryset(value) |
            Q(priority__iexact=value) |
            Q(status__iexact=value) |
            Q(tags__name__in=[value])
        )
    
    class Meta(BaseFilter.Meta):
        model = Task
        fields = [
            *BaseFilter.Meta.fields,
            "due_date",
            'priority',
            'status',
            'parent_task',
            'estimated_duration',
            'actual_duration',
            'allow_auto_status_update',
            'org',
            "depart"
        ]