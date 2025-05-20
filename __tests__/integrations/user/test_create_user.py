from ..base_classe import BaseTestClass
from user.models import AppUser as User

class TestCreateUserView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user need to provide valid data to create a new user:
        - email is required
        - email need to be a valide email
        - email need to be unique among existing users
        - first_name is required
        - first_name should contain at least 3 characters
        - password is optional, but if specified should be validate
        - last_name is optional
    - after data validation, user need to be created and record in the database
    - created_by attr need to be set to the user who created the new user
    - invitation/validation email need to be sent to the new created user
    """
    url_name = "users-list"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST
        )

    def setUp(self):
        self.user = self.create_and_active_user()
    
    def test_account_creation_with_empty_email(self):
        response = self.auth_post(self.user, {"first_name": "myfirstname"})
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("email"), list)
        self.assertEqual(data.get("email")[0], "You need to provide a valid email address")
        # user isn't created
        self.assertEqual(len(User.objects.all()), 1)

    def test_account_creation_with_invalid_email(self):
        response = self.auth_post(self.user, {"email": "invalidemail"})
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("email"), list)
        self.assertEqual(data.get("email")[0], "Your email address is invalid")
        # user isn't created
        self.assertEqual(len(User.objects.all()), 1)

    def test_account_creation_with_existed_email(self):
        self.create_user(email="emailtest@nowhere.com")
        response = self.auth_post(self.user, {"email": "emailtest@nowhere.com"})
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("email"), list)
        self.assertEqual(data.get("email")[0], "A user with that email already exists.")
        # user isn't created
        self.assertEqual(len(User.objects.all()), 2)

    def test_account_creation_empty_first_name(self):
        response = self.auth_post(self.user, {"email": "validemail@gmail.com"})
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("first_name"), list)
        self.assertEqual(data.get("first_name")[0], "You need to provide a valid first name")
        # user isn't created
        self.assertEqual(len(User.objects.all()), 1)
  
    def test_account_creation_with_first_name_less_3(self):
        response = self.auth_post(
            self.user, {"email": "validemail@gmail.com", "first_name": "te"}
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("first_name"), list)
        self.assertEqual(
            data.get("first_name")[0], 
            "Your first name must contain at least 3 characters"
        )
        # user isn't created
        self.assertEqual(len(User.objects.all()), 1)
  
    def test_account_creation_with_password_less_8(self):
        response = self.auth_post(
            self.user,
            {"email": "validemail@gmail.com", "first_name": "testnme", "password": "test"}
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        password_errors = data.get("password")
        self.assertIsInstance(password_errors, list)
        self.assertEqual(
            password_errors[0], 
            "Your password must contain at least 8 characters"
        )
        # user isn't created
        self.assertEqual(len(User.objects.all()), 1)

    def test_account_creation_password_without_special(self):
        response = self.auth_post(
            self.user,
            {"email": "validemail@gmail.com", "first_name": "testnme", "password": "Test1Password"}
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        password_errors = data.get("password")
        self.assertIsInstance(password_errors, list)
        self.assertEqual(
            password_errors[0],
            "Your password must include at least one of these characters : @ . + - / _ "
        )
        # user isn't created
        self.assertEqual(len(User.objects.all()), 1)

    def test_account_creation_success_with_email_sent(self):
        response = self.auth_post(
            self.user, 
            {"email": "validemail@gmail.com", "first_name": "testnme"}
        )
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        mail_sent = self.get_mailbox()[0]
        self.assertEqual(len(self.get_mailbox()), 1)
        self.assertEqual(mail_sent.to[0], "validemail@gmail.com")
        self.assertIn("Invitation to join Platform", mail_sent.subject)
        self.assertRegex(mail_sent.body, "We recommend you to reset your password, please click the link below")
    
    def test_account_creation_with_created_by_set(self):
        response = self.auth_post(
            self.user, 
            {"email": "validemail@gmail.com", "first_name": "testnme", 
             "last_name": "my last name"}
        )
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        self.user_model.objects.get(email="validemail@gmail.com", created_by=self.user)
    
    def test_account_creation_success_with_response(self):
        response = self.auth_post(
            self.user, 
            {"email": "validemail@gmail.com", "first_name": "testnme", 
             "last_name": "my last name"}
        )
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get('id', None))
        self.assertIsNotNone(data.get('created_at', None))
        self.assertEqual(data.get('email'), "validemail@gmail.com")
        self.assertEqual(data.get('first_name'), "testnme")
        self.assertEqual(data.get('last_name'), "my last name")
        # db updated
        user = self.user_model.objects.get(email="validemail@gmail.com")
        self.assertEqual(user.first_name, "testnme")
        self.assertEqual(user.last_name, "my last name")