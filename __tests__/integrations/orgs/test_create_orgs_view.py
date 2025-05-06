
from ..base_classe import BaseTestClass


class TestCreateOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user can create an org with required field:
        - name (should be unique for that user among his orgs)
    - name field should be validate when not specified or not unique together with the owner
    - members field if specified should be validate for not found user or invlid user_id
    - org is created and has the proper owner, name, descr if specied and created_by attr set
    - view return proper response after creation
    """
    url_name = "orgs-list"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST
        )