import uuid

from ...base_classe import BaseTestClass
from organization.models import Organization, Department

class TestUpdateDepartmentCanBeAccessByView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not found when obj does not exist, org or depart
    - user without access to org get not found error
    - test user with access allowed on org (owner, can_be_accessed_by) can not change depart owner users, 403
    - test user with access allowed on depart can't change depart owner users, 403
    - validate owner user ids provide:
        - ids should exist
        - user that is making the request should have a full access over owner user specified
    - only creator of org or depart can update depart owners
    - owners are successfully added to obj can_be_accessed_by list after request
    """
    url_name = "departments-change-owners"
    departs_data = [
        {
            "name": "my depart 1", "description": "some descr"
        },
        {
            "name": "my depart 2", "description": "some descr"
        },
        {
            "name": "my depart 3", "description": "some descr"
        }
    ]

    def setUp(self):
        self.owner_user = self.create_and_active_user(email="owner_user@gmail.com")
        self.org = Organization.objects.create(
            name="test", 
            owner=self.owner_user, 
            created_by=self.owner_user
        )
        departs_data = [*self.departs_data]
        for data in departs_data:
            data["org"] = self.org
        self.created_departs = self.bulk_create_object(Department, departs_data)
    
    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST, ['fake-id', 'fake-id']
        )
    
    def test_user_get_not_found_error(self):
        test_data = {
            "org": [uuid.uuid4(), self.created_departs[0].id],
            "dep": [self.org.id, uuid.uuid4()]
        }

        for _, url_arg in test_data.items():
            response = self.auth_post(self.owner_user, {}, url_arg) 
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail", None))

    def test_other_user_cant_update_data(self):
        no_access_allowed = self.create_and_active_user()
        depart = self.created_departs[0]
        req_data = {
            "owner_ids": [],
        }

        response = self.auth_post(
            no_access_allowed, req_data, 
            [self.org.id, depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail", None))

    def test_access_allowed_user_cant_update_owner_users(self):
        target_depart = self.created_departs[0]
        
        owner_only = self.create_and_active_user(email="owner_only@ghdsghd.com")
        self.org.owner = owner_only
        self.org.save()

        access_org_user = self.create_and_active_user(email="access_org_user@gsja.com")
        self.org.can_be_accessed_by.add(access_org_user)

        access_org_depart_user = self.create_and_active_user(email='access_org_depart_user@hsga.com')
        target_depart.can_be_accessed_by.add(access_org_depart_user)
        self.org.can_be_accessed_by.add(access_org_depart_user)

        simple_user = self.create_and_active_user(email="simple_user@gshg.com")
        simple_user.can_be_accessed_by.add(*[owner_only, access_org_depart_user, access_org_user])

        req_data = {
            "owner_ids": [simple_user.id]
        }

        different_users = [
            owner_only, 
            access_org_depart_user, 
            access_org_user
        ]
        for user in different_users:
            response = self.auth_post(user, req_data, [self.org.id, target_depart.id])
            self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
            self.assertIsNotNone(response.data.get("detail", None))
        self.assertEqual(
            len(Department.objects.get(id=target_depart.id).can_be_accessed_by.all()),
            1
        )
    
    def test_req_data_validation_ids(self):
        simple_user = self.create_and_active_user(email="simple_user@gnaiold.com")
        target_depart = self.created_departs[0]

        test_datas = [
            {},
            {"owner_ids": []},
            {"owner_ids": [uuid.uuid4(), uuid.uuid4()]},
            {"owner_ids": [simple_user.id]}
        ]

        for test_data in test_datas:
            response = self.auth_post(self.owner_user, test_data, [self.org.id, target_depart.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            self.assertIsNotNone(response.data.get("owner_ids", None))
            self.assertIsInstance(response.data.get("owner_ids"), list)
        self.assertEqual(
            len(Department.objects.get(id=target_depart.id).can_be_accessed_by.all()),
            0
        )
    
    def test_creator_can_change_obj_access_user(self):
        target_depart = self.created_departs[0]

        # for org creator, he has access to this user
        simple_user = self.create_and_active_user(email="simple_user@gnaiold.com")
        simple_user.can_be_accessed_by.add(self.owner_user)

        # this user has full access to the org and is the depart creator 
        # and has access to simple_user2
        access_org_create_depart_user = self.create_and_active_user(
            email='access_org_create_depart_user@hsga.com'
        )
        self.org.can_be_accessed_by.add(access_org_create_depart_user)
        target_depart.created_by = access_org_create_depart_user
        target_depart.save()
        simple_user2 = self.create_and_active_user(email="simple_user2@ghgahsg.com")
        simple_user2.can_be_accessed_by.add(access_org_create_depart_user)

        test_datas = [
            {
                "user": self.owner_user,
                "req_data": {
                    "owner_ids": [simple_user.id]
                }
            },
            {
                "user": access_org_create_depart_user,
                "req_data": {
                    "owner_ids": [simple_user2.id]
                }
            }
        ]

        for data in test_datas:
            current_user = data["user"]
            req_data = data["req_data"]
            response = self.auth_post(current_user, req_data, [self.org.id, target_depart.id])
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            access_allowed = Department.objects.get(id=target_depart.id).can_be_accessed_by.all()
            self.assertEqual(len(access_allowed), 1)