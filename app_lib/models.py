import uuid

from django.db import models, router
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models.manager import Manager

from .app_permssions import permissions_exist
from .soft_deletion import SoftDeleteCollector
from .manager import DefaultManager


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
        db_index=True
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

    objects = DefaultManager()
    all_objects = Manager()

    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        # implementation inspiration from django.db.models.deletion
        # leave third party or django define model as it, will be deleted
        # with hard_delete during full object deletion

        if not self._is_pk_set():
            raise ValueError(
                "%s object can't be deleted because its %s attribute is set "
                "to None." % (self._meta.object_name, self._meta.pk.attname)
            )
        
        using = using or router.db_for_write(self.__class__, instance=self)
        collector = SoftDeleteCollector(using=using, origin=self)
        collector.collect([self], keep_parents=keep_parents)
        return collector.delete()
    
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