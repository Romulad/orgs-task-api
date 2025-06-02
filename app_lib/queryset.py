from django.contrib.auth import get_user_model

from organization.models import Department, Organization
from tasks.models import Task
from tags.models import Tag

class ModelDefaultQuerysets:
    """
    A class to provide default querysets for models in the app.
    This class can be extended to provide custom querysets for specific use cases.
    """

    def get_model_queryset(
            self,
            model,
            default=False,
            only_select_related=False,
            only_prefetch_related=False,
            select_related_fields=None,
            prefetch_related_fields=None
    ):
        """
        Returns a queryset for the specified model with optional select and prefetch related fields.
        
        :param model: The model class to get the queryset for.
        :param default: If True, returns the default queryset without any related fields.
        :param only_select_related: If True, returns only select_related fields.
        :param select_related_fields: List of fields to select_related.
        :param prefetch_related_fields: List of fields to prefetch_related.
        :return: QuerySet for the specified model.
        """
        queryset = model.objects.all()

        if only_select_related and select_related_fields:
            queryset = queryset.select_related(*select_related_fields)

        elif only_prefetch_related and prefetch_related_fields:
            queryset = queryset.prefetch_related(*prefetch_related_fields)

        elif not default and prefetch_related_fields and select_related_fields:
            queryset = queryset.prefetch_related(
                *prefetch_related_fields
            ).select_related(
                *select_related_fields
            )

        return queryset

    def get_depart_queryset(
            self, 
            default=False, 
            only_select_related=False,
            only_prefetch_related=False,
    ):
        return self.get_model_queryset(
            Department,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            select_related_fields=["org", "created_by"],
            prefetch_related_fields=["members", "can_be_accessed_by"]
        )

    def get_org_queryset(
        self,
        default=False, 
        only_select_related=False,
        only_prefetch_related=False
    ):      
        return self.get_model_queryset(
            Organization,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            select_related_fields=["owner", "created_by"],
            prefetch_related_fields=["members", "can_be_accessed_by"]
        )
    
    def get_user_queryset(
            self,
            default=False,
            only_select_related=False,
            only_prefetch_related=False
    ):
        User = get_user_model()
        return self.get_model_queryset(
            User,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            select_related_fields=["created_by"],
            prefetch_related_fields=["can_be_accessed_by"],
        )

    def get_task_queryset(
        self,
        default=False,
        only_select_related=False,
        only_prefetch_related=False
    ):
        return self.get_model_queryset(
            Task,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            select_related_fields=["org", "depart", "created_by"],
            prefetch_related_fields=["assigned_to", "tags", "can_be_accessed_by"]
        )
    
    def get_tag_queryset(
        self,
        default=False,
        only_select_related=False,
            only_prefetch_related=False
    ):
        return self.get_model_queryset(
            Tag,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            select_related_fields=["org", "created_by"],
            prefetch_related_fields=["can_be_accessed_by"]
        )

queryset_helpers = ModelDefaultQuerysets()
