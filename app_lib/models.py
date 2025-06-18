import uuid
from collections import Counter
from functools import reduce
from operator import or_

from django.db import models, router
from django.db.models import sql
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models.manager import Manager
from django.db.models.deletion import Collector
from django.contrib.auth import get_user_model
from django.db import transaction

from .app_permssions import permissions_exist

class DefaultManager(Manager):
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def delete(self):
        return super().delete()

    def hard_delete(self):
        return super().delete()


class AbstractBaseModel(models.Model):
    """
    Abstract base model that provides common fields and methods.
    """
    id = models.UUIDField(
        primary_key=True, editable=False, default=uuid.uuid4
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(app_label)s_%(class)s_created_by",
        blank=True,
    )
    can_be_accessed_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="%(app_label)s_%(class)s_can_be_accessed_by",
        blank=True,
    )
    is_deleted = models.BooleanField(
        _("deleted"),
        default=False,
        help_text=_(
            "Indicate a deleted ressource."
            "Select this instead of deleting ressource."
        ),
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_('created at'), db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_('modified at')
    )
    deleted_at = models.DateTimeField(
        null=True, blank=True
    )

    default_manager_attr_name = "objects"
    objects = DefaultManager()
    all_objects = Manager()

    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        # implementation inspiration from django.db.models.deletion
        # leave third party or django define model as it, will deleted
        # with hard_delete during full object deletion

        if not self._is_pk_set():
            raise ValueError(
                "%s object can't be deleted because its %s attribute is set "
                "to None." % (self._meta.object_name, self._meta.pk.attname)
            )
        
        using = using or router.db_for_write(self.__class__, instance=self)
        collector = Collector(using=using, origin=self)
        collector.collect([self], keep_parents=keep_parents)
        
        # number of objects soft deleted for each model label
        deleted_counter = Counter()

        # Optimize for the case with a single obj
        if len(collector.data) == 1:
            model, instances = list(collector.data.items())[0]
            instance = list(instances)[0]
            if (
                len(instances) == 1 and 
                collector.can_fast_delete(instance) and
                hasattr(instance, "is_deleted")
            ):
                count = 1
                instance.is_deleted = True
                instance.save()
                return count, {model._meta.label: count}

        with transaction.atomic(using=using, savepoint=False):
            # no pre_soft_delete yet, will be added if needed

            # fast deletes
            for qs in collector.fast_deletes:
                if len(qs) == 0:
                    continue
                object_from_qs = qs[0]
                if hasattr(object_from_qs, "is_deleted"):
                    count = qs.update(is_deleted=True)
                    deleted_counter[qs.model._meta.label] += count if count else 0

            # update fields, leave this as it, no deletion, just needed fields update
            for (field, value), instances_list in collector.field_updates.items():
                updates = []
                objs = []
                for instances in instances_list:
                    if (
                        isinstance(instances, models.QuerySet)
                        and instances._result_cache is None
                    ):
                        updates.append(instances)
                    else:
                        objs.extend(instances)
                if updates:
                    combined_updates = reduce(or_, updates)
                    combined_updates.update(**{field.name: value})
                if objs:
                    model = objs[0].__class__
                    query = sql.UpdateQuery(model)
                    query.update_batch(
                        list({obj.pk for obj in objs}), {field.name: value}, using
                    )

            # delete instances by setting is_deleted to true
            for model, instances in collector.data.items():
                if len(instances) == 0:
                    continue
                example_instance = instances.pop()
                if not hasattr(example_instance, "is_deleted"):
                    continue
                pk_list = [obj.pk for obj in instances]
                pk_list.append(example_instance.pk)
                if hasattr(self, "default_manager_attr_name"):
                    default_manager = getattr(model, self.default_manager_attr_name)
                else:
                    default_manager = self.objects
                count = default_manager.filter(pk__in=pk_list).update(is_deleted=True)
                deleted_counter[model._meta.label] += count if count else 0

                # no post_soft_delete yet, will be added if needed

        return sum(deleted_counter.values()), dict(deleted_counter)
    
    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using, keep_parents)


class AbstractBasePermissionModel(AbstractBaseModel):
    """Provide a permission text field along with how to create and remove
    permissions"""
    perms = models.TextField(
        _("Permissions"),
    )

    class Meta:
        abstract = True

    def __setattr__(self, name, value):
        if name == "perms":
            # ensure after perms manipulation the value is set back as string
            if isinstance(value, list):
                value = self.dump_perms(value)
            elif not isinstance(value, str):
                raise ValueError(
                    f"perms model attribute must be set as a string not {type(value)}"
                )
        object.__setattr__(self, name, value)
    
    @classmethod
    def dump_perms(cls, perms:list) -> str:
        """Dump permissions to a string"""
        if isinstance(perms, str):
            return perms
        
        if len(perms) == 0:
            return ""
        
        return ",".join(perms)

    def save_perms(self, perms:list):
        self.perms = self.dump_perms(perms)
        self.save()

    def get_perms(self) -> list[str]:
        """Get permissions of the user as a list"""
        user_perms = self.perms.split(",")
        while '' in user_perms:
            user_perms.remove('')
        return user_perms
    
    def add_permissions(self, perms:str|list[str]):
        """Add permissions to the user and return a tuple containing in order: 
        - `list` of added permissions
        - `list` of not found permissions
        """
        _, found, not_found = permissions_exist(perms)

        if found:
            added_count = 0
            user_perms = self.get_perms()
            for user_perm in found:
                if user_perm not in user_perms:
                    user_perms.append(user_perm)
                    added_count += 1
            if added_count:
                self.save_perms(user_perms)

        return found, not_found

    def remove_permissions(self, perms:str|list[str]):
        """Remove permissions from the user and return a tuple containing in order: 
        - `list` of removed permissions
        - `list` of not found permissions
        """
        _, found, not_found = permissions_exist(perms)

        if found:
            removed_count = 0
            user_perms = self.get_perms()
            for user_perm in found:
                if user_perm in user_perms:
                    while user_perm in user_perms:
                        user_perms.remove(user_perm)
                    removed_count += 1
            
            if removed_count:
                self.save_perms(user_perms)

        return found, not_found