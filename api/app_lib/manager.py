from django.contrib.auth.models import BaseUserManager
from django.db.models.manager import Manager
from django.db.models import QuerySet

from .soft_deletion import SoftDeleteCollector

class DefaultQueryset(QuerySet):
    def delete(self):
        """Soft Delete the records in the current QuerySet."""
        # From django.db.models.query
        self._not_support_combined_queries("delete")
        if self.query.is_sliced:
            raise TypeError("Cannot use 'limit' or 'offset' with delete().")
        if self.query.distinct_fields:
            raise TypeError("Cannot call delete() after .distinct(*fields).")
        if self._fields is not None:
            raise TypeError("Cannot call delete() after .values() or .values_list()")

        del_query = self._chain()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._for_write = True

        # Disable non-supported fields.
        del_query.query.select_for_update = False
        del_query.query.select_related = False
        del_query.query.clear_ordering(force=True)

        collector = SoftDeleteCollector(using=del_query.db, origin=self)
        collector.collect(del_query)
        num_deleted, num_deleted_per_model = collector.delete()

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None
        return num_deleted, num_deleted_per_model

    delete.alters_data = True
    delete.queryset_only = True

    def hard_delete(self):
        """Completly delete the records in the current queryset"""
        return super().delete()
    
    hard_delete.alters_data = True
    hard_delete.queryset_only = True

    

class _DefaultManager(Manager):
    """Base manager, defines how object colletions should behave by default 
    in the app."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
DefaultManager = _DefaultManager.from_queryset(DefaultQueryset)


class DefaultUserManager(BaseUserManager, DefaultManager):
    """
    Default user manager
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)
