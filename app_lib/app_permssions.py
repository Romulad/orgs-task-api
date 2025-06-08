from django.utils.translation import gettext_lazy as _

CAN_CREATE_TASK = "can_create_task"

APP_PERMISSIONS = {
    CAN_CREATE_TASK: {
        "name": _("Can create task"),
        "help_text": _("Any user with this permission can create task in the given organization")
    }
}

def permissions_exist(permissions: str | list[str]):
    """Check if all perms exist, return a tuple containing in order:
    - `bool` indicating if all permissions exist, 
    - `list` list of found permissions, 
    - `list` list of not found permissions if exist.
    Take care of mapping string to list.
    """
    if isinstance(permissions, str):
        permissions = [permissions]
        
    not_found = []
    found = []
    for perm in permissions:
        perm_lower = perm.lower()
        try:
            APP_PERMISSIONS[perm_lower]
            found.append(perm_lower)
        except KeyError:
            not_found.append(perm_lower)
    
    return False if not_found else True, found, not_found

def get_perm_list():
    return list(
        APP_PERMISSIONS.keys()
    )