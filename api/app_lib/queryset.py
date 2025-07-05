from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet
from django.contrib.auth.models import AbstractBaseUser

from organization.models import Department, Organization
from tasks.models import Task
from tags.models import Tag
from perms.models import UserPermissions, Role

class ModelDefaultQuerysets:
    """
    A class that provides default querysets for models in the app.
    This class can be extended to provide custom querysets for specific use case.
    """

    def get_model_queryset(
        self,
        model,
        *,
        default=False,
        only_select_related=False,
        select_related_fields=None,
        include_nested_selected=False,
        nested_select_related_fields=[],
        only_prefetch_related=False,
        prefetch_related_fields=None,
        prefetch_org_can_be_accessed_by=False,
        prefetch_depart_can_be_accessed_by=False
    ) -> QuerySet:
        """
        Returns a queryset for the specified model with optional select and prefetch related fields.
        
        :param model: The model class to get the queryset for.
        :param default: If True, returns the default queryset `.all` without any related fields.
        :param only_select_related: If True, returns only select_related fields.
        :param select_related_fields: List of fields to select_related.
        :param include_nested_selected: whether to select_related `nested_select_related_fields` when
        `only_select_related` or where select_related will be applied to direct relationships.
        :param nested_select_related_fields: List of nested fields to select_related
        :param prefetch_related_fields: List of fields to prefetch_related.
        :param prefetch_org_can_be_accessed_by: if True, also loads the model `org` 
        `can_be_accessed_by` user list, so `org` attr should exists when this option is specified
        :param prefetch_depart_can_be_accessed_by: if True, also loads the model `depart` 
        `can_be_accessed_by` user list, so `depart` attr should exists when this option is specified
        :return: QuerySet for the specified model.
        """
        queryset = model.objects.all()

        if only_select_related and select_related_fields:
            qs = queryset.select_related(*select_related_fields)
            queryset = qs.select_related(*nested_select_related_fields) if include_nested_selected else qs

        elif only_prefetch_related and prefetch_related_fields:
            queryset = queryset.prefetch_related(*prefetch_related_fields)

        elif not default and prefetch_related_fields and select_related_fields:
            qs_with_nested_related = queryset.select_related(
                *select_related_fields
            ).select_related(
                *nested_select_related_fields
            ).prefetch_related(
                *prefetch_related_fields
            )
            qs_without_nested_related = queryset.select_related(
                *select_related_fields
            ).prefetch_related(
                *prefetch_related_fields
            )
            queryset = qs_with_nested_related if include_nested_selected else qs_without_nested_related

        if prefetch_org_can_be_accessed_by:
            queryset = queryset.prefetch_related("org__can_be_accessed_by")

        if prefetch_depart_can_be_accessed_by:
            queryset = queryset.prefetch_related("depart__can_be_accessed_by")

        return queryset

    def get_depart_queryset(
        self,
        *,
        default=False, 
        only_select_related=False,
        only_prefetch_related=False,
        include_nested_selected=False,
        prefetch_org_can_be_accessed_by=False
    ) -> QuerySet[Department]:
        """
        Returns a queryset for the `Department` model with optional select and prefetch related fields.

        :param default: If True, returns the default queryset `.all` without any related fields.
        :param only_select_related: If True, returns only select_related fields.
        :param only_prefetch_related: If True, returns only prefetch_related fields.
        :param include_nested_selected: whether to include nested relationship fields when applying 
        select_related on direct relationships, following foreign or one-to-one relationships.
        :param prefetch_org_can_be_accessed_by: if True, also loads the depart `org` 
        `can_be_accessed_by` user list
        :return: QuerySet for the Department model.
        """
        return self.get_model_queryset(
            Department,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            include_nested_selected=include_nested_selected,
            select_related_fields=["org", "created_by"],
            nested_select_related_fields=["org__owner", "org__created_by"],
            prefetch_related_fields=["members", "can_be_accessed_by"],
            prefetch_org_can_be_accessed_by=prefetch_org_can_be_accessed_by
        )

    def get_org_queryset(
        self,
        *,
        default=False, 
        only_select_related=False,
        only_prefetch_related=False,
        include_nested_selected=False,
    ) -> QuerySet[Organization]:  
        """Returns a queryset for the `Organization` model with optional select and prefetch related fields.

        :param default: If True, returns the default queryset `.all` without any related fields.
        :param only_select_related: If True, returns only select_related fields.
        :param only_prefetch_related: If True, returns only prefetch_related fields.
        :param include_nested_selected: whether to include nested relationship fields when applying
        select_related on direct relationships, following foreign or one-to-one relationships.
        :return: QuerySet for the Organization model.
        """  
        return self.get_model_queryset(
            Organization,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            include_nested_selected=include_nested_selected,
            select_related_fields=["owner", "created_by"],
            prefetch_related_fields=["members", "can_be_accessed_by"]
        )
    
    def get_user_queryset(
        self,
        *,
        default=False,
        only_select_related=False,
        only_prefetch_related=False,
        include_nested_selected=False
    ) -> QuerySet[AbstractBaseUser]:
        """Returns a queryset for the `User` model with optional select and prefetch related fields.

        :param default: If True, returns the default queryset `.all` without any related fields.
        :param only_select_related: If True, returns only select_related fields.
        :param only_prefetch_related: If True, returns only prefetch_related fields.
        :param include_nested_selected: whether to include nested relationship fields when applying
        select_related on direct relationships, following foreign or one-to-one relationships.
        :return: QuerySet for the User model.
        """
        User = get_user_model()
        return self.get_model_queryset(
            User,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            include_nested_selected=include_nested_selected,
            select_related_fields=["created_by"],
            prefetch_related_fields=["can_be_accessed_by"],
        )

    def get_task_queryset(
        self,
        *,
        default=False,
        only_select_related=False,
        only_prefetch_related=False,
        include_nested_selected=False,
        prefetch_org_can_be_accessed_by=False,
        prefetch_depart_can_be_accessed_by=False
    ) -> QuerySet[Task]:
        """Returns a queryset for the `Task` model with optional select and prefetch related fields.

        :param default: If True, returns the default queryset `.all` without any related fields.
        :param only_select_related: If True, returns only select_related fields.
        :param only_prefetch_related: If True, returns only prefetch_related fields.
        :param include_nested_selected: whether to include nested relationship fields when applying
        select_related on direct relationships, following foreign or one-to-one relationships.
        :param prefetch_org_can_be_accessed_by: if True, also loads the task `org` 
        `can_be_accessed_by` user list
        :param prefetch_depart_can_be_accessed_by: if True, loads the task `depart` 
        `can_be_accessed_by` user list
        :return: QuerySet for the Task model.
        """
        return self.get_model_queryset(
            Task,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            include_nested_selected=include_nested_selected,
            select_related_fields=["org", "depart", "created_by"],
            nested_select_related_fields=[
                "org__owner", "org__created_by", "depart__org",
                "depart__created_by", "depart__org__owner", "depart__org__created_by"
            ],
            prefetch_related_fields=["assigned_to", "tags", "can_be_accessed_by"],
            prefetch_org_can_be_accessed_by=prefetch_org_can_be_accessed_by,
            prefetch_depart_can_be_accessed_by=prefetch_depart_can_be_accessed_by
        )
    
    def get_tag_queryset(
        self,
        *,
        default=False,
        only_select_related=False,
        only_prefetch_related=False,
        include_nested_selected=False,
        prefetch_org_can_be_accessed_by=False
    ) -> QuerySet[Tag]:
        """Returns a queryset for the `Tag` model with optional select and prefetch related fields.

        :param default: If True, returns the default queryset `.all` without any related fields.
        :param only_select_related: If True, returns only select_related fields.
        :param only_prefetch_related: If True, returns only prefetch_related fields.
        :param include_nested_selected: whether to include nested relationship fields when applying
        select_related on direct relationships, following foreign or one-to-one relationships.
        :param prefetch_org_can_be_accessed_by: if True, also loads the tag `org` 
        `can_be_accessed_by` user list
        :return: QuerySet for the Tag model.
        """
        return self.get_model_queryset(
            Tag,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            include_nested_selected=include_nested_selected,
            select_related_fields=["org", "created_by"],
            nested_select_related_fields=["org__owner", "org__created_by"],
            prefetch_related_fields=["can_be_accessed_by"],
            prefetch_org_can_be_accessed_by=prefetch_org_can_be_accessed_by
        )

    def get_user_permission_queryset(
        self,
        *,
        default=False,
        only_select_related=False,
        only_prefetch_related=False,
        include_nested_selected=False,
        prefetch_org_can_be_accessed_by=False
    ) -> QuerySet[UserPermissions]:
        """Returns a queryset for the `UserPermissions` model with optional select and prefetch related fields.

        :param default: If True, returns the default queryset `.all` without any related fields.
        :param only_select_related: If True, returns only select_related fields.
        :param only_prefetch_related: If True, returns only prefetch_related fields.
        :param include_nested_selected: whether to include nested relationship fields when applying
        select_related on direct relationships, following foreign or one-to-one relationships.
        :param prefetch_org_can_be_accessed_by: if True, also loads the user permission object `org` 
        `can_be_accessed_by` user list
        :return: QuerySet for the UserPermissions model.
        """
        return self.get_model_queryset(
            UserPermissions,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            include_nested_selected=include_nested_selected,
            select_related_fields=["org", "created_by", "user"],
            nested_select_related_fields=["org__owner", "org__created_by"],
            prefetch_related_fields=["can_be_accessed_by"],
            prefetch_org_can_be_accessed_by=prefetch_org_can_be_accessed_by
        )

    def get_role_queryset(
        self,
        *,
        default=False,
        only_select_related=False,
        only_prefetch_related=False,
        include_nested_selected=False,
        prefetch_org_can_be_accessed_by=False
    ) -> QuerySet[Role]:
        """Returns a queryset for the `Role` model with optional select and prefetch related fields.

        :param default: If True, returns the default queryset `.all` without any related fields.
        :param only_select_related: If True, returns only select_related fields.
        :param only_prefetch_related: If True, returns only prefetch_related fields.
        :param include_nested_selected: whether to include nested relationship fields when applying
        select_related on direct relationships, following foreign or one-to-one relationships.
        :param prefetch_org_can_be_accessed_by: if True, also loads the role `org` 
        `can_be_accessed_by` user list
        :return: QuerySet for the Role model.
        """
        return self.get_model_queryset(
            Role,
            default=default,
            only_select_related=only_select_related,
            only_prefetch_related=only_prefetch_related,
            include_nested_selected=include_nested_selected,
            select_related_fields=["org", "created_by"],
            nested_select_related_fields=["org__owner", "org__created_by"],
            prefetch_related_fields=["can_be_accessed_by", "users"],
            prefetch_org_can_be_accessed_by=prefetch_org_can_be_accessed_by
        )

queryset_helpers = ModelDefaultQuerysets()
