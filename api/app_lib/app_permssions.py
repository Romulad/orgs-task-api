from django.utils.translation import gettext_lazy as _


CAN_CREATE_DEPART = "can_create_depart"
CAN_CREATE_TASK = "can_create_task"
CAN_CREATE_TAG = "can_create_tag"
APP_PERMISSIONS = {
    CAN_CREATE_DEPART: {
        "name": _("Can create depart"),
        "help_text": _("Any user with this permission can create departments in the given organization"),
        "org_creator_only": False,
    },
    CAN_CREATE_TASK: {
        "name": _("Can create task"),
        "help_text": _("Any user with this permission can create tasks in the given organization"),
        "org_creator_only": False,
    },
    CAN_CREATE_TAG: {
        "name": _("Can create tag"),
        "help_text": _("Any user with this permission can create tags in the given organization"),
        "org_creator_only": False,
    }
}

CAN_CHANGE_RESSOURCES_OWNERS = "can_change_ressources_owners"
CREATOR_ONLY_PERMS = {
    CAN_CHANGE_RESSOURCES_OWNERS: {
        "name": _("Can change ressources owners"),
        "help_text": _(
            "Any user with this permission can change any ressource " \
            "owners in the given organization"
        ),
        "org_creator_only": True,
    }
}

ALL_PERMS = {**APP_PERMISSIONS, **CREATOR_ONLY_PERMS}

def permissions_exist(
        permissions: str | list[str], 
        search_from: dict =None
    ):
    """Check if all perms exist, return a tuple containing in order:
    - `bool` indicating if all permissions exist, 
    - `list` list of found permissions, 
    - `list` list of not found permissions if exist.

    Take care of mapping string to list.

    if `search_from` param is specified the check will be done from it.
    Should be a dict including as key the perm label, see `APP_PERMISSIONS`.
    """
    if isinstance(permissions, str):
        permissions = permissions.split(',')

    all_perms = ALL_PERMS if not search_from else search_from
        
    not_found = []
    found = []
    for perm in permissions:
        perm_lower = perm.lower()
        try:
            all_perms[perm_lower]
            found.append(perm_lower)
        except KeyError:
            not_found.append(perm_lower)
    
    return False if not_found else True, found, not_found


def get_perm_list(
        creator_only=False, 
        default_only=False
    ):
    """
    Return permission label supported by the app. 
    - Use `creator_only` param to get only creator level permission labels
    - Use `default_only` param to default permission labels

    Default to all permission labels
    """
    if creator_only:
        perms = CREATOR_ONLY_PERMS
    elif default_only:
        perms = APP_PERMISSIONS
    else:
        perms = {**APP_PERMISSIONS, **CREATOR_ONLY_PERMS}
    return list(perms.keys())


def get_perm_data(perms:list[str]):
    """
    Retrieves metadata for a list of permission identifiers.
    Args:
        perms (list[str]): A list of permission strings to look up.
    Returns:
        list[dict]: A list of dictionaries, each containing the permission label and its associated metadata.
        Permissions not found in `ALL_PERMS` are skipped. 
    ```
    [
        {
            "name": "string",
            "label": "string",
            "help_text": "string"
        },
        ...
    ]
    ```

    **Note** :
        - If a permission is not found in `ALL_PERMS`, it is ignored.
   
    """
    
    data = []
    for perm in perms:
        perm_meta_data = ALL_PERMS.get(perm, None)
        if not perm_meta_data:
            # probably an unknow or removed perm
            continue
        data.append({
            "label": perm,
            **perm_meta_data
        })
    return data