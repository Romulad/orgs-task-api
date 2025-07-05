from django.db.models import Q

from app_lib.filter import BaseNameDescriptionDateDataFilter
from .models import Role

class RoleDataFilter(BaseNameDescriptionDateDataFilter):
    """
    Filter for Role data, inheriting from BaseNameDescriptionDateDataFilter.
    It allows filtering roles by name and description.
    """
    class Meta:
        model = Role
        fields = [
            *BaseNameDescriptionDateDataFilter.Meta.fields,
            "org",
        ]
    
    def search_through(self, queryset, name, value):
        return queryset.filter(
            self.get_default_search_queryset(value) |
            Q(perms__contains=value) |
            Q(perms__icontains=value)
        )