from rest_framework.permissions import BasePermission
from django.utils.translation import gettext_lazy as _

class CanAccessedObjectInstance(BasePermission):
    """ Check if a given user has permission to act on the current object 
    use `created_by`, `owner` or `can_be_accessed_by` on the object
    """
    message = _("You don't have permission to perform this action")

    def has_object_permission(self, request, view, obj):
        user = request.user
        created_by = getattr(obj, "created_by", None)
        owner = getattr(obj, "owner", None)
        can_be_accessed_by = getattr(obj, "can_be_accessed_by", None)

        if (
            not created_by and 
            not can_be_accessed_by and 
            not owner
        ):
            return True
        
        can_have_access = False

        if owner:
            can_have_access = owner.id == user.id

        if created_by and not can_have_access:
            can_have_access = created_by.id == user.id

        if can_be_accessed_by and not can_have_access:
            can_have_access = can_be_accessed_by.filter(id=user.id).exists()
        
        return can_have_access