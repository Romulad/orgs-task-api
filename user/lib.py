from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q

from app_lib.email import send_html_email
from app_lib.urls import get_app_base_url, generate_url_safe_uuid
from app_lib.queryset import queryset_helpers
from app_lib.app_permssions import get_perm_data, get_perm_list


def send_account_created_notification(user, request):
    """Send an email to the user to notify that his account has been created"""
    template = 'emails/account_created_notif.html'
    context = {
        "first_name": user.first_name,
        "uuid": generate_url_safe_uuid(user.email),
        "token": default_token_generator.make_token(user),
        "base_url": get_app_base_url(request),
    }
    send_html_email(
        title="Invitation to join Platform",
        template_name=template,
        email=user.email,
        context=context
    )


def get_user_authorizations_per_org(user):
    """Get user authorizations including permissions and roles in organizations.
    This function retrieves the organizations the user is associated with,
    their permissions, and roles, and formats the data for easy access.
    Args:
        user (AppUser): The user for whom to retrieve authorizations.
    Returns:
        list: A list of dictionaries containing organization data, permissions,
              and roles for the user.

    ```
    [
        {
            "org": {
                "id": "uuid",
                "name": "string",
                "description": "string"
            },
            "perms": [
                {
                    "name": "string",
                    "label": "string",
                    "help_text": "string"
                },
            ],
            "roles": [
                {
                    "id": "uuid",
                    "name": "string",
                    "description": "string",
                    "perms": ["perm_name", ...],
                },
                ...
            ]
        },
        ...
    ]
    ```
    """
    # To avoid circular imports error
    from organization.serializers import OrganizationSerializer
    from perms.serializers import SimpleUserPermissionSerializer, SimpleRoleSerializer
    
    # db queries
    user_orgs = list(
        queryset_helpers.get_org_queryset().filter(
            Q(created_by=user) |
            Q(owner=user) |
            Q(can_be_accessed_by=user) |
            Q(members=user)
        ).distinct()
    )

    if not user_orgs:
        return []
        
    user_perm_objs = list(
        queryset_helpers.get_user_permission_queryset(
            only_select_related=True
        ).filter(
            org__in=user_orgs, user=user
        )
    )
    user_roles = list(
        queryset_helpers.get_role_queryset(
            only_select_related=True
        ).filter(
            org__in=user_orgs, users=user
        )
    )

    # perm per org for easy reference later.
    # By design we should only have one userpermission obj for an user 
    # per org if exist
    user_perms_per_org = {}
    for user_perm_obj in user_perm_objs:
        perm_data = SimpleUserPermissionSerializer(
            user_perm_obj
        ).data
        user_perms_per_org[user_perm_obj.org.id] = {
            **perm_data, "labels": user_perm_obj.get_perms()
        }

    # roles per org for easy reference later
    user_roles_per_org = {}
    for user_role in user_roles:
        user_role_data = SimpleRoleSerializer(user_role).data
        if user_roles_data := user_roles_per_org.get(user_role.org.id, None):
            user_roles_data.append(user_role_data)
        else:
            user_roles_per_org[user_role.org.id] = [user_role_data]

    data = []

    for org in user_orgs:
        user_org_auth = {}
        user_org_auth["org"] = OrganizationSerializer(org).data

        # perms
        existing_perms = []
        if perm_data := user_perms_per_org.get(org.id, None):
            user_org_auth["perms"] = perm_data['perms']
            existing_perms = perm_data['labels']
        else:
            user_org_auth["perms"] = []

        not_in_existing_perms = set()

        # roles
        if user_org_roles := user_roles_per_org.get(org.id, None):
            user_org_auth["roles"] = user_org_roles
            # check for perms in role but no in user perm list
            not_in_existing_perms.update([
                perm
                for user_org_role in user_org_roles
                for perm in user_org_role['perms']
                if not perm in existing_perms
            ])
        else:
            user_org_auth["roles"] = []

        # check if the user is an owner and update perms as needed
        owner_id = getattr(org.owner, 'id', "")
        creator_id = getattr(org.created_by, 'id', "")
        if creator_id == user.id:
            not_in_existing_perms.update([
                perm
                for perm in get_perm_list()
                if perm not in existing_perms
            ])
        elif (
            owner_id == user.id or
            user in org.can_be_accessed_by.all()
        ):
            not_in_existing_perms.update([
                perm
                for perm in get_perm_list(default_only=True)
                if perm not in existing_perms
            ])

        # extend existing perms to include role and owner perms
        if not_in_existing_perms:
            user_org_auth["perms"].extend(
                get_perm_data(not_in_existing_perms)
            )
        
        data.append(user_org_auth)

    return data


