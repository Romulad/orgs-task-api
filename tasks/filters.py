from django_filters import rest_framework as filters

from app_lib.filter import BaseNameDescriptionDateDataFilter as BaseFilter
from .models import Task

class  TaskDataFilter(BaseFilter):
    assigned_to = filters.BaseInFilter(
        label="Filter by assigned user ids",
        lookup_expr="id__in"
    )

    due_date = filters.IsoDateTimeFromToRangeFilter()

    tag_ids = filters.BaseInFilter(
        label="Filter by tag ids",
        lookup_expr="id__in",
        field_name="tags"
    )
    tag_names = filters.BaseInFilter(
        label="Filter by tag name",
        lookup_expr="name__contains__in",
        field_name="tags"
    )

    def search_through(self, queryset, name, value):
        new_queryset = super().search_through(queryset, name, value)
        return new_queryset
    
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