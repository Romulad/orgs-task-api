import json

from django.urls import reverse
from django.shortcuts import get_object_or_404
from rest_framework import status

from ..base_classe import BaseTestClass
from auth_user.serializers import RegistrationResponseSerializer

class TestRegisterView(BaseTestClass):
  url_name = "register"

  def test_account_creation_with_empty_email(self):
    response = self.client.post(
      reverse(self.url_name), {"first_name": "myfirstname"}
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = json.loads(response.content)
    self.assertIsInstance(data.get("email"), list)
    self.assertEqual(data.get("email")[0], "You need to provide a valid email address")

  def test_account_creation_with_invalid_email(self):
    response = self.client.post(
      reverse(self.url_name), {"email": "invalidemail"}
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = json.loads(response.content)
    self.assertIsInstance(data.get("email"), list)
    self.assertEqual(data.get("email")[0], "Your email address is invalid")

  def test_account_creation_with_existed_email(self):
    self.create_user(email="email@gmail.com")

    response = self.client.post(
      reverse(self.url_name), {"email": "email@gmail.com"}
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = json.loads(response.content)
    self.assertIsInstance(data.get("email"), list)
    self.assertEqual(data.get("email")[0], "A user with that email already exists.")

  def test_account_creation_empty_first_name(self):
    response = self.client.post(
      reverse(self.url_name), {"email": "validemail@gmail.com"}
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = json.loads(response.content)
    self.assertIsInstance(data.get("first_name"), list)
    self.assertEqual(data.get("first_name")[0], "You need to provide a valid first name")
  
  def test_account_creation_with_first_name_less_3(self):
    response = self.client.post(
      reverse(self.url_name), {"email": "validemail@gmail.com", "first_name": "te"}
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = json.loads(response.content)
    self.assertIsInstance(data.get("first_name"), list)
    self.assertEqual(
      data.get("first_name")[0], 
      "Your first name must contain at least 3 characters"
    )
  
  def test_account_creation_with_password_less_8(self):
    response = self.client.post(
      reverse(self.url_name), 
      {"email": "validemail@gmail.com", "first_name": "testnme", "password": "test"}
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = json.loads(response.content)
    password_errors = data.get("password")
    self.assertIsInstance(password_errors, list)
    self.assertEqual(
      password_errors[0], 
      "Your password must contain at least 8 characters"
    )

  def test_account_creation_password_without_special(self):
    response = self.client.post(
      reverse(self.url_name), 
      {"email": "validemail@gmail.com", "first_name": "testnme", "password": "Test1Password"}
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = json.loads(response.content)
    password_errors = data.get("password")
    self.assertIsInstance(password_errors, list)
    self.assertEqual(
      password_errors[0],
      "Your password must include at least one of these characters : @ . + - / _ "
    )

  def test_account_creation_password_without_number(self):
    response = self.client.post(
      reverse(self.url_name), 
      {"email": "validemail@gmail.com", "first_name": "testnme", "password": "Test@Password"}
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = json.loads(response.content)
    password_errors = data.get("password")
    self.assertIsInstance(password_errors, list)
    self.assertEqual(
      password_errors[0], 
      "Your password must include at least one digit"
    )

  def test_account_creation_password_mismatch(self):
    response = self.client.post(
      reverse(self.url_name), 
      {"email": "validemail@gmail.com", "first_name": "testnme", 
      "password": "Test1@Password", "password2": "Test@Password"}
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = json.loads(response.content)
    password2_errors = data.get("password2")
    self.assertIsInstance(password2_errors, list)
    self.assertEqual(
      password2_errors[0], 
      "Password mismatch"
    )
  
  def test_account_creation_success_with_inactive_status(self):
    response = self.client.post(
      reverse(self.url_name), 
      {"email": "validemail@gmail.com", "first_name": "testnme", 
      "password": "Test1@Password", "password2": "Test1@Password"}
    )
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    user = get_object_or_404(self.user_model, email="validemail@gmail.com")
    self.assertFalse(user.is_active)
  
  def test_account_creation_success_with_email_sent(self):
    response = self.client.post(
      reverse(self.url_name), 
      {"email": "validemail@gmail.com", "first_name": "testnme", 
      "password": "Test1@Password", "password2": "Test1@Password"}
    )
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    mail_sent = self.get_mailbox()[0]
    self.assertEqual(len(self.get_mailbox()), 1)
    self.assertEqual(mail_sent.to[0], "validemail@gmail.com")
    self.assertIn("Welcome testnme", mail_sent.subject)
    self.assertRegex(mail_sent.body, "please verify your email address by clicking the button below")

  def test_account_creation_success_with_response(self):
    response = self.client.post(
      reverse(self.url_name), 
      {"email": "validemail@gmail.com", "first_name": "testnme", 
      "password": "Test1@Password", "password2": "Test1@Password"}
    )
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    user = self.user_model.objects.get(email="validemail@gmail.com")
    data = json.loads(response.content)
    self.assertDictEqual(
      data, RegistrationResponseSerializer(user).data
    )