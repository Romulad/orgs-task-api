from ...base_classe import BaseTestClass
from app_lib.app_permssions import get_perm_list

class TestMeView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user can get data with needed fields
    - Include a field called `authorizations` that contains list of user permissions
    in an organization along with their roles if any. Something like:
        ```
        "authorizations" : [
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
                    ...
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
    `perms` should include all user permissions in the org include perms from his roles.
    - for `authorizations` field, for an org owner:
        - owner
        - creator
        - can_be_accessed_by
    all perms should be returned by default without explicitly giving them. Except creator only
    perms that should need to be explicitly given.
    - test `authorizations` field when user does not have neither perm obj nor role, but is
    within an organization 
    """
    url_name = "users-me"

    def setUp(self):
        self.org_owner, self.org_creator, self.org = self.create_new_org()
        self.target_user = self.create_and_activate_random_user()

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET
        )
    
    def test_user_get_needed_data(self):
        response = self.auth_get(self.target_user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        self.assertEqual(response.data.get("id", None), self.target_user.id)
        self.assertEqual(response.data.get("email", None), self.target_user.email)
        self.assertEqual(response.data.get("first_name", None), self.target_user.first_name)
        self.assertEqual(response.data.get("last_name", None), self.target_user.last_name)
        auth = response.data.get("authorizations", None)
        self.assertIsInstance(auth, list)
        self.assertEqual(len(auth), 0)
    
    def test_authorizations_field(self):
        # all perms
        all_perms = get_perm_list()

        # create and add user as member to orgs
        orgs = [self.create_new_org()[-1] for _ in range(10)]
        [org.members.add(self.target_user) for org in orgs]

        # create permission objects with perms for the user in the created orgs
        user_perms_in_orgs = [
            self.create_new_permission(org, self.target_user)[-1] 
            for org in orgs
        ]
        perms = all_perms[:2]
        for user_perm_in_org in user_perms_in_orgs:
            # use two perms here, then we will add more perms when creating roles.
            # the goals is to make sure all perms are include in the response even when spread out
            user_perm_in_org.perms = perms
            user_perm_in_org.save()

        # create role in each org with perms and add the user to the 
        # role within each org
        roles = [self.create_new_role(org)[-1] for org in orgs]
        role_ids = []
        role_perm = all_perms[2:]
        for role in roles:
            role.add_permissions(role_perm)
            role.users.add(self.target_user)
            role.save()
            role_ids.append(str(role.id))

        # request time
        response = self.auth_get(self.target_user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        
        # assess response data for the authorizations field
        data = self.loads(response.content).get("authorizations")
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), len(orgs))
        target_org_ids = [str(org.id) for org in orgs]
        for org_auth in data:
            self.assertIsInstance(org_auth, dict)

            # assessment for org
            org_from_response = org_auth.get("org")
            self.assertIn(org_from_response['id'], target_org_ids)
            self.assertIsNotNone(org_from_response['name'])
            self.assertIsNotNone(org_from_response['description'])
            # to make sure all org was included
            target_org_ids.remove(org_from_response['id'])

            # assessment for perms, perms field should include perm from 
            # user permission objec and roles
            perms_from_response = org_auth.get("perms")
            self.assertIsInstance(perms_from_response, list)
            self.assertEqual(len(perms_from_response), len(all_perms))
            for perm_from_resp in perms_from_response:
                self.assertIn(perm_from_resp["label"], all_perms)
                self.assertIsNotNone(perm_from_resp['name'])
                self.assertIsNotNone(perm_from_resp['help_text'])

            # assessment for roles
            roles_from_response = org_auth.get("roles")
            self.assertIsInstance(roles_from_response, list)
            self.assertEqual(len(roles_from_response), 1)
            self.assertIn(roles_from_response[0]['id'], role_ids)
            # each org has a role for the user
            role_ids.remove(roles_from_response[0]['id'])
            self.assertIsNotNone(roles_from_response[0]['name'])
            self.assertIsNotNone(roles_from_response[0]['description'])
            role_from_resp_perms = roles_from_response[0]['perms']
            self.assertIsInstance(role_from_resp_perms, list)
            self.assertEqual(len(role_from_resp_perms), len(role_perm))
            [
                self.assertIn(role_from_resp_perm, role_perm) 
                for role_from_resp_perm in role_from_resp_perms
            ]

    def test_authorizations_field_for_owners(self):
        """No explicit permission assignment needed"""
        self.org.can_be_accessed_by.add(self.target_user)

        users = [
            (self.org_owner, get_perm_list(default_only=True)),
            (self.target_user, get_perm_list(default_only=True)),
            (self.org_creator, get_perm_list())
        ]

        for user, perms in users:
            response = self.auth_get(user)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("authorizations")
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            # perms
            resp_perms = data[0].get("perms")
            self.assertIsInstance(resp_perms, list)
            self.assertEqual(len(resp_perms), len(perms))
            resp_perm_labels = [resp_perm["label"] for resp_perm in resp_perms]
            [self.assertIn(perm, resp_perm_labels) for perm in perms]
    
    def test_user_authorizations_field_with_no_role_no_perm(self):
        self.org.members.add(self.target_user)
        response = self.auth_get(self.target_user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        # data assessment
        data = self.loads(response.content).get('authorizations')
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        target_data = data[0]
        self.assertIsInstance(target_data['perms'], list)
        self.assertEqual(len(target_data['perms']), 0)
        self.assertIsInstance(target_data['roles'], list)
        self.assertEqual(len(target_data['roles']), 0)
        self.assertIsInstance(target_data['org'], dict)
    
    def test_authorization_field_with_mutiple_roles(self):
        self.org.members.add(self.target_user)
        roles = [self.create_new_role(self.org)[-1] for _ in range(5)]
        [role.users.add(self.target_user) for role in roles]
        response = self.auth_get(self.target_user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get('authorizations')
        target_data = data[0]
        self.assertIsInstance(target_data['roles'], list)
        self.assertEqual(
            len(
                target_data['roles']
            ), len(roles)
        )
