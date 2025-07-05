from rest_framework.permissions import BasePermission
from django.utils.translation import gettext_lazy as _

from app_lib.authorization import auth_checker

class DefaultBasePermission(BasePermission):
    message = _("You don't have permission to perform this action")

    def has_objects_permission(self, request, view, objs):
        return True


class Can_Access_ObjectInstance(DefaultBasePermission):
    """ Check if a given user has permission to act on the current object 
    use `created_by`, `owner` or `can_be_accessed_by` on the object
    """

    def has_object_permission(self, request, view, obj):
        return auth_checker.has_access_to_obj(obj, request.user)
    
    def has_objects_permission(self, request, view, objs):
        return auth_checker.has_access_to_objs(objs, request.user)

class Can_Access_Org_Or_Obj(DefaultBasePermission):
    """ Check if a given user has permission to act on the current object 
    use `created_by`, `can_be_accessed_by`, `org.owner`, `org.can_be_accessed_by`, 
    `org.created_by` and `id` on the object.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        is_allowed = auth_checker.has_access_to_obj(obj, user)

        if not is_allowed:
            is_allowed = auth_checker.has_access_to_obj(obj.org, user)

        return is_allowed


class Can_Access_Org_Depart_Or_Obj(DefaultBasePermission):
    """Implement `has_object_permission` and `has_objects_permission`.
    Check if the user has access to the object(s) org or depart or the obj itself. 
    Org attribute must exist on the object or each object for muliple permission check."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        return auth_checker.has_access_to_org_depart_or_obj(obj, user)
    
    def has_objects_permission(self, request, view, objs):
        user = request.user
        return auth_checker.has_access_to_org_depart_or_obj_on_objs(objs, user)


class Is_Object_Or_Org_Or_Depart_Creator(DefaultBasePermission):
    """Passes if one of the following conditions is met:
        - the object `id` and the user `id` are the same (user itself)
        - the object `created_by` is the same as the user
        - the obj has an `org` attribute and the user is the org creator
        - the obj has a `depart` attribute and the user is the depart creator
    This permission is used to only allow the object creator or the org/depart creator to act on
    ressource.
    """

    def permform_check(self, user, obj):
        if auth_checker.has_creator_access_on_obj(obj, user):
            return True
        
        has_org = hasattr(obj, 'org')
        if has_org and auth_checker.has_creator_access_on_obj(obj.org, user):
            return True
        
        if hasattr(obj, 'depart') and auth_checker.has_creator_access_on_obj(obj.depart, user):
            return True
        
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        return self.permform_check(user, obj)
        
    def has_objects_permission(self, request, view, objs):
        for obj in objs:
            if not self.permform_check(request.user, obj):
                return False  
        return True