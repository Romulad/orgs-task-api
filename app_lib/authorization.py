


class AuthorizationChecker:

    def has_access_to_obj(self, obj, want_access_obj) -> bool:
        want_access_obj_id = want_access_obj.id
        can_have_access = want_access_obj_id in [
            have_access.id for have_access in obj.can_be_accessed_by.all()
        ]
        is_allowed = True
        if obj.created_by:
            is_allowed = (
                can_have_access or
                obj.created_by.id == want_access_obj_id or
                obj.id == want_access_obj_id
            )
        else:
            is_allowed = (
                can_have_access or
                obj.id == want_access_obj_id
            )
        return is_allowed
    
    def has_access_to_objs(self, objs:list, want_access_obj) -> bool:
        for obj in objs:
            is_allowed = self.has_access_to_obj(obj, want_access_obj)
            if not is_allowed:
                return is_allowed
        return True

auth_checker = AuthorizationChecker()