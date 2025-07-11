from django.db.transaction import atomic
from django.contrib.auth import get_user_model

from perms.models import UserPermissions
from .queryset import queryset_helpers, Organization
from .app_permssions import permissions_exist, get_perm_list

User = get_user_model()

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
        """
        Checks if access is granted to all objects in the provided list.
        Iterates over each object in the `objs` list and checks if access is allowed
        using the `has_access_to_obj` method. If access is denied for any object,
        the function returns False immediately. If access is granted for all objects,
        returns True.
        Args:
            objs (list): A list of objects to check access for.
            want_access_obj: The object or permission criteria to check access against.
        Returns:
            bool: True if access is granted to all objects, False otherwise.
        """
        for obj in objs:
            is_allowed = self.has_access_to_obj(obj, want_access_obj)
            if not is_allowed:
                return is_allowed
        return True
    
    def has_creator_access_on_obj(self, obj, want_access_obj) -> bool:
        """
        Passes when one of the condition below is met:
            - the object `id` and `want_access_obj` `id` are the same (obj itself)
            - the object `created_by` is the same as the `want_access_obj` obj
        """
        want_access_obj_id = want_access_obj.id
        is_allowed = obj.id == want_access_obj_id

        if hasattr(obj, 'created_by') and not is_allowed:
            is_allowed = getattr(obj.created_by, 'id', None) == want_access_obj_id
  
        return is_allowed
    
    def has_creator_access_on_objs(self, objs:list, want_access_obj) -> bool:
        """
        Passes when one of the condition below is met:
            - the objects `id` and `want_access_obj` `id` are the same (obj itself)
            - the objects `created_by` is the same as the `want_access_obj` obj
        """
        for obj in objs:
            is_allowed = self.has_creator_access_on_obj(obj, want_access_obj)
            if not is_allowed:
                return is_allowed
        return True
    
    def has_access_to_org_depart_or_obj(self, obj, want_access_obj):
        """Check if the `want_access_obj` obj has access to the obj
        `org` or `depart` or the `obj` itself. `Org` attribute must exist on the obj"""

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
                user_perm_obj.add_permissions(found)
                
        return found, not_found

    def remove_permissions_from_users(self, users, org, perms: str | list):
        """Remove `perms` from each user in `users` in `org`. `users` can be a single
        obj and it will be map to a list internally. Return in order:
        - `list` of `removed` or found perms. Perms are removed only when exist on user
        - `list` of `not_found` perms
        """
        _, to_remove, not_found = permissions_exist(perms)
        if not to_remove:
            return to_remove, not_found
        
        if not isinstance(users, list):
            users = [users]

        perm_objs = queryset_helpers.get_user_permission_queryset(
            default=True
        ).filter(org=org, user__in=users)

        for perm_obj in perm_objs:
            perm_obj.remove_permissions(to_remove)
        
        return to_remove, not_found
    
    def has_permission(
        self,
        user:User,
        org:Organization, 
        perm:str
    ):
        """
        Check wether the user has a perm in the organization.
        Args:
            user: the user object
            org: the target org object
            perm: string representing the permission
        Returns:
            bool: wether or not the user has the permission
        """
        exist, found, _, = permissions_exist(perm)
        if not exist or not found:
            return False

        # creator has all perms by default
        creator_id = getattr(org.created_by, 'id', None) 
        if creator_id == user.id:
            return True
        
        target_perm = found[0]

        # owners have default perms by default
        is_default_perm = target_perm in get_perm_list(default_only=True)
        owner_id = getattr(org.owner, 'id', None)
        if (
            owner_id == user.id or 
            user in org.can_be_accessed_by.all()
        ) and is_default_perm:
            return True

        if queryset_helpers.get_user_permission_queryset(default=True).filter(
            user=user, 
            org=org, 
            perms__icontains=target_perm
        ).exists():
            return True

        if queryset_helpers.get_role_queryset(default=True).filter(
            org=org, 
            users=user, 
            perms__icontains=target_perm
        ).exists():
            return True
        
        return False
    
    def can_add_creator_level_perms(
        self, 
        perms: str|list[str], 
        org: Organization,
        user: User
    ):
        """
        If `perms` contains creator level permission, check if `user` can add it to someone 
        in `org`.
        - Currently only org creator can add creator level permission to someone in an org
        Args:
            user: The user object
            org: The organization in which the permission will be added to someone
            perms: `str` or `list[str]` that will be added to someone in `org`
        Returns:
            bool: Indicating if the user has the necessary permission to add creator level permission 
            to someone in `org` if `perms` contains such perms.
        """
        
        # Creator has permission to add any permission to anyone in his org
        creator_id = getattr(org.created_by, "id", None)
        if creator_id == user.id:
            return True
        
        _, found, _ = permissions_exist(perms)

        creator_level_perms = get_perm_list(creator_only=True)
        for perm_str in found:
            if perm_str in creator_level_perms:
                return False
            
        return True

auth_checker = AuthorizationChecker()