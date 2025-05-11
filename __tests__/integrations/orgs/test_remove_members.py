from ..base_classe import BaseTestClass
from organization.models import Organization

class TestRemoveMembersFromOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user need to have access to the org or he is the creator
    - no access allowed user can't delete members
    - members is deleted and deleted member ids is returned
    - user get not found when ressource not found
    """
    url_name = "orgs-remove-members"
    orgs_data = [
        {
            "name": "my org 1", "description": "some descr"
        },
        {
            "name": "my org 2", "description": "some descr"
        },
        {
            "name": "my org 3", "description": "some descr"
        }
    ]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST, ["fake-id"]
        )