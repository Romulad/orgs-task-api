from collections import Counter
from functools import reduce
from operator import or_

from django.db.models.deletion import Collector
from django.db import transaction
from django.db.models import sql
from django.db import models


class SoftDeleteCollector(Collector):
    """Subclasse the default django `collector` to get its power and to allow complete sof delete
    mechanisme and being able to update our approach as django changes. 
    
    We override the `delete` method so objects are softdeleted intead of 
    completly deleted.

    `collect` method should be called before the `delete` method.
    
    This is only use within our own model object and manager"""

    def delete(self):
        """Soft delete objects"""
        # number of objects soft deleted for each model label
        deleted_counter = Counter()

        # Optimize for the case with a single obj
        if len(self.data) == 1:
            model, instances = list(self.data.items())[0]
            instance = list(instances)[0]
            if (
                len(instances) == 1 and 
                self.can_fast_delete(instance) and
                hasattr(instance, "is_deleted")
            ):
                count = 1
                instance.is_deleted = True
                instance.save()
                return count, {model._meta.label: count}

        with transaction.atomic(using=self.using, savepoint=False):
            # no pre_soft_delete yet, will be added if needed

            # fast deletes
            for qs in self.fast_deletes:
                if len(qs) == 0:
                    continue
                object_from_qs = qs[0]
                if hasattr(object_from_qs, "is_deleted"):
                    count = qs.update(is_deleted=True)
                    deleted_counter[qs.model._meta.label] += count if count else 0

            # update fields, leave this as it, no deletion, just needed fields updated
            for (field, value), instances_list in self.field_updates.items():
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
                        list({obj.pk for obj in objs}), {field.name: value}, self.using
                    )

            # delete instances by setting is_deleted to true
            for model, instances in self.data.items():
                if len(instances) == 0:
                    continue
                example_instance = instances.pop()
                if not hasattr(example_instance, "is_deleted"):
                    continue
                pk_list = [obj.pk for obj in instances]
                pk_list.append(example_instance.pk)
                count = model._default_manager.filter(pk__in=pk_list).update(is_deleted=True)
                deleted_counter[model._meta.label] += count if count else 0

                # no post_soft_delete yet, will be added if needed

        return sum(deleted_counter.values()), dict(deleted_counter)
    