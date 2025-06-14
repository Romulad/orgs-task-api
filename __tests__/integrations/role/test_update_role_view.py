import uuid

from ..base_classe import BaseTestClass
from django.forms.models import model_to_dict

from app_lib.app_permssions import get_perm_list

class TestUPdateRoleView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource does not exist
    - test not access allowed user:
        - other user or org user - 404 not found
        - org member only without permission - 403 forbidden
        - any other user existing in the org but without explicit permission - 404 not found
    should not be able to update data
    - test all fields should be present in the request data
    - test data validation: (instance already exists)
        - name:
            - field is required
            - should not be empty
            - if name in request data different from instance namme it should be validated 
            to be unique for the role within the org
        - description:
            - field is required
        - org:
            - field is required
            - org id should be a valid id
            - if org id differnt from instance org id user making the request should have permission 
            to act on the new specified org
        - perms:
            - field is required
    - test user with access:
        - org owner
        - org creator and creator of the role
        - user with `can_be_accessed_by` permission on both org and role
    can update role data successfully with permission list containing invalid or valid permissions
    - test response data is valid and perms set
    """
    url_name = "roles-detail"

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        self.role_creator, self.target_role = self.create_new_role(self.org)
        self.roles = [self.create_new_role(self.org)[-1] for _ in range(10)]
        self.req_data = model_to_dict(
            self.target_role, 
            fields=["name", "description", "org", "perms"]
        )

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PUT, ["fake-role-id"]
        )
    
    def test_not_found_when_role_does_not_exist(self):
        response = self.auth_put(self.owner_user, self.req_data, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
    
    def test_not_access_allowed_user_cant_update_role(self):
        simple_user = self.create_and_activate_random_user()
        another_owner, another_creator, _ = self.create_new_org()

        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        self.req_data["name"] = "new_role_name"

        for user in [
            simple_user,
            another_owner,
            another_creator,
            depart_creator,
            can_access_depart_user
        ]:
            response = self.auth_put(user, self.req_data, [self.target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail"))
        with self.assertRaises(self.target_role.__class__.DoesNotExist):
            self.target_role.__class__.objects.get(name=self.req_data["name"])
    
    def test_org_member_without_permission_cant_update_role(self):
        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)

        self.req_data["name"] = "new_role_name"

        response = self.auth_put(org_member, self.req_data, [self.target_role.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
        with self.assertRaises(self.target_role.__class__.DoesNotExist):
            self.target_role.__class__.objects.get(name=self.req_data["name"])
    
    def test_name_validation(self):
        del self.req_data["name"]

        test_data = [
            {
                **self.req_data,
            },
            {
                **self.req_data,
                "name": "",
            },
            {
                **self.req_data,
                "name": self.roles[0].name,
            }
        ]
        for req_data in test_data:
            response = self.auth_put(self.owner_user, req_data, [self.target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("name")
            self.assertIsInstance(errors, list)
    
    def test_same_name_validation(self):
        self.req_data["perms"] = []
        response = self.auth_put(self.owner_user, self.req_data, [self.target_role.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("org"), str(self.org.id))
    
    def test_description_validation(self):
        del self.req_data["description"]
        response = self.auth_put(self.owner_user, self.req_data, [self.target_role.id])
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get("description")
        self.assertIsInstance(errors, list)
    
    def test_org_validation(self):
        del self.req_data["org"]
        _, _, new_org = self.create_new_org()

        test_data = [
            self.req_data,
            {
                **self.req_data,
                "org": uuid.uuid4()
            },
            {
                **self.req_data,
                "org": new_org.id,
            }
        ]
        for req_data in test_data:
            response = self.auth_put(self.owner_user, req_data, [self.target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("org")
            self.assertIsInstance(errors, list)
        with self.assertRaises(self.target_role.__class__.DoesNotExist):
            self.target_role.__class__.objects.get(org__id=new_org.id)

    def test_only_new_org_specified_is_validated_against_user(self):
        self.req_data["perms"] = []
        response = self.auth_put(self.role_creator, self.req_data, [self.target_role.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("org"), str(self.org.id))
    
    def test_perms_validation(self):
        del self.req_data["perms"]
        self.req_data["org"] = self.org.id
        self.req_data["name"] = "new_role_name"

        response = self.auth_put(self.owner_user, self.req_data, [self.target_role.id])
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get("perms")
        self.assertIsInstance(errors, list)
        with self.assertRaises(self.target_role.__class__.DoesNotExist):
            self.target_role.__class__.objects.get(name=self.req_data["name"])
    
    def test_user_with_access_can_update_role(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)
 
        role_creator = self.create_and_activate_random_user()
        can_access_role_user = self.create_and_activate_random_user()

        for role in self.roles:
            role.created_by = role_creator
            role.save()
            role.can_be_accessed_by.add(can_access_role_user)

        users = [
            self.owner_user,
            self.org_creator,
            can_access_org_user,
            role_creator,
            can_access_role_user
        ]

        self.req_data["name"] = "new_role_name"
        self.req_data["org"] = self.org.id
        real_perms = get_perm_list()[:5]
        self.req_data["perms"] = real_perms + ["fake_perm_", "random_PERM"]

        for index, user in enumerate(users):
            target_role = self.roles[index]
            self.req_data["name"] = f"{self.req_data['name']}_{index}"
            response = self.auth_put(user, self.req_data, [target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get("id"), str(target_role.id))
            self.assertEqual(data.get("name"), self.req_data["name"])
            self.assertEqual(data.get("org"), str(self.org.id))
            self.assertEqual(data.get("description"), self.req_data["description"])
            self.assertIsInstance(data.get("perms"), list)
            self.assertEqual(len(real_perms), len(data.get("perms")))
            self.assertIsNotNone(data.get("created_at"))
            self.assertIsInstance(data.get("can_be_accessed_by"), list)
            # role has been updated with created_by set
            updated = target_role.__class__.objects.get(
                id=target_role.id, name=self.req_data["name"], org=self.org
            )

            role_perms = updated.get_perms()
            self.assertEqual(len(role_perms), len(real_perms))
            for perm in real_perms:
                self.assertIn(perm, role_perms)