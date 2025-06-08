from django.db.transaction import atomic

from perms.models import UserPermissions
from .queryset import queryset_helpers
from .app_permssions import permissions_exist

class AuthorizationChecker:

    def has_access_to_obj(self, obj, want_access_obj) -> bool:
        """Check `want_access_obj` can have access to the object by checking
        `owner`, `created_by`, `can_be_accessed_by` and `id` attrs on the `obj`"""
        want_access_obj_id = want_access_obj.id
        is_allowed = obj.id == want_access_obj_id

        if hasattr(obj, 'owner') and not is_allowed:
            is_allowed = getattr(obj.owner, 'id', None) == want_access_obj_id
            
        if hasattr(obj, 'created_by') and not is_allowed:
            is_allowed = getattr(obj.created_by, 'id', None) == want_access_obj_id
         
        if hasattr(obj, 'can_be_accessed_by') and not is_allowed:         
            is_allowed = want_access_obj_id in [
                have_access.id for have_access in obj.can_be_accessed_by.all()
            ]
  
        return is_allowed
    
    def has_access_to_objs(self, objs:list, want_access_obj) -> bool:
        for obj in objs:
            is_allowed = self.has_access_to_obj(obj, want_access_obj)
            if not is_allowed:
                return is_allowed
        return True
    
    def has_creator_access_on_obj(self, obj, want_access_obj) -> bool:
        want_access_obj_id = want_access_obj.id
        is_allowed = obj.id == want_access_obj_id

        if hasattr(obj, 'created_by') and not is_allowed:
            is_allowed = getattr(obj.created_by, 'id', None) == want_access_obj_id
  
        return is_allowed
    
    def has_creator_access_on_objs(self, objs:list, want_access_obj) -> bool:
        for obj in objs:
            is_allowed = self.has_creator_access_on_obj(obj, want_access_obj)
            if not is_allowed:
                return is_allowed
        return True
    
    def has_access_to_org_depart_or_obj(self, obj, want_access_obj):
        """Check if the `want_access_obj` obj has access to the obj
        org or depart or the obj itself. Org attribute must exist on the obj"""

        is_allowed = self.has_access_to_obj(obj, want_access_obj)

        if not is_allowed:
            is_allowed = self.has_access_to_obj(obj.org, want_access_obj)

        if not is_allowed and getattr(obj, "depart", None):
            is_allowed = self.has_access_to_obj(obj.depart, want_access_obj)

        return is_allowed

    def has_access_to_org_depart_or_obj_on_objs(self, objs, want_access_obj):
        """Check if the `want_access_obj` obj has access to all obj in objs
        org or depart or the obj itself. Org attribute must exist on the obj"""

        for obj in objs:
            is_allowed = self.has_access_to_org_depart_or_obj(obj, want_access_obj)
            if not is_allowed:
                return is_allowed
        return True

    def add_permissions_to_users(self, users, org, perms: str | list[str]):
        """Add `perms` to `users` in `org`. User can be a single value
        it will be map to a list internally. Return added and not found perms"""
        _, found, not_found = permissions_exist(perms)
        if not found:
            return found, not_found

        if not isinstance(users, list):
            users = [users]

        # get all existed perm obj at once and avoid a get_or_create call on each user
        # where its no needed
        perm_objs = queryset_helpers.get_user_permission_queryset(
            only_select_related=True
        ).filter(user__in=users, org=org)
        found_user_perms = {perm_obj.user:perm_obj for perm_obj in perm_objs}
        
        # permissions are added to everyone or no one
        with atomic():
            for user in users:
                if user in found_user_perms:
                    user_perm_obj = found_user_perms[user]
                else:
                    user_perm_obj, _ = UserPermissions.objects.get_or_create(
                        org=org,
                        user=user
                    )
                user_perm_obj.add_permissions(perms)
                
        return found, not_found


auth_checker = AuthorizationChecker()