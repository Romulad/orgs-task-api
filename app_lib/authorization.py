

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

auth_checker = AuthorizationChecker()