from rest_framework.permissions import BasePermission
from django.utils.translation import gettext_lazy as _

from app_lib.authorization import auth_checker


class DefaultBasePermission(BasePermission):
    def has_objects_permission(self, request, view, objs):
        return True


class CanAccessedObjectInstance(DefaultBasePermission):
    """ Check if a given user has permission to act on the current object 
    use `created_by`, `owner` or `can_be_accessed_by` on the object
    """
    message = _("You don't have permission to perform this action")

    def has_object_permission(self, request, view, obj):
        return auth_checker.has_access_to_obj(obj, request.user)


class IsObjectCreatorOrObj(DefaultBasePermission):
    """ Check if a given user has permission to act on the current object 
    use `created_by`, and `id` on the object
    """
    message = _("You don't have permission to perform this action")

    def has_object_permission(self, request, view, obj):
        return auth_checker.has_creator_access_on_obj(obj, request.user)
    
    def has_objects_permission(self, request, view, objs):
        return auth_checker.has_creator_access_on_objs(objs, request.user)