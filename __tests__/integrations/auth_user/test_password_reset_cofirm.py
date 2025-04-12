import json

from rest_framework import status
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import get_object_or_404

from ..base_classe import BaseTestClass

class TestPasswordResetConfirmView(BaseTestClass):
  url_name = "password_reset_confirm"

  def test_password_reset_confirm_with_invalid_uuid(self):
    uuid = urlsafe_base64_encode(force_bytes("fake_udi"))
    response = self.post({}, [uuid, self.fake_token])
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response.data.get('message'), "Invalid or expired link")
  
  def test_passwod_reset_confirm_with_invalid_token(self):
    self.create_and_active_user(email="valid@gmail.com")
    uuid = urlsafe_base64_encode(force_bytes("valid@gmail.com"))
    response = self.post({}, [uuid, self.fake_token])
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response.data.get('message'), "Invalid or expired link")

  def test_password_reset_confirm_with_empty_password(self):
    user = self.create_and_active_user(email="valid@gmail.com")
    uuid = urlsafe_base64_encode(force_bytes("valid@gmail.com"))
    token = default_token_generator.make_token(user)
    response = self.post({}, [uuid, token])
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    # check response data
    password_errors = json.loads(response.content).get('password')
    self.assertIsInstance(password_errors, list)
    self.assertEqual(password_errors[0], "The password field is required")

  def test_passwod_reset_confirm_with_password_less_8(self):
    user = self.create_and_active_user(email="valid@gmail.com")
    uuid = urlsafe_base64_encode(force_bytes("valid@gmail.com"))
    token = default_token_generator.make_token(user)
    response = self.post({"password": "teste"}, [uuid, token])
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    # check response data
    password_errors = json.loads(response.content).get('password')
    self.assertIsInstance(password_errors, list)
    self.assertEqual(password_errors[0], "Your password must contain at least 8 characters")

  def test_passwod_reset_confirm_with_password_without_special(self):
    user = self.create_and_active_user(email="valid@gmail.com")
    uuid = urlsafe_base64_encode(force_bytes("valid@gmail.com"))
    token = default_token_generator.make_token(user)
    response = self.post({"password": "Test1Makeitcount"}, [uuid, token])
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    # check response data
    password_errors = json.loads(response.content).get('password')
    self.assertIsInstance(password_errors, list)
    self.assertEqual(
      password_errors[0], 
      "Your password must include at least one of these characters : @ . + - / _ "
    )

  def test_passwod_reset_confirm_with_invalid_password2(self):
    user = self.create_and_active_user(email="valid@gmail.com")
    uuid = urlsafe_base64_encode(force_bytes("valid@gmail.com"))
    token = default_token_generator.make_token(user)
    response = self.post(
      {"password": "Test1Make@tcount", "password2": "Test1Makeitcount"}, 
      [uuid, token]
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    # check response data
    password_errors = json.loads(response.content).get('password2')
    self.assertIsInstance(password_errors, list)
    self.assertEqual(
      password_errors[0], 
      "Passwords must match."
    )

  def test_passwod_reset_confirm_with_old_password(self):
    user = self.create_and_active_user(email="valid@gmail.com", password="Test1Make@tcount")
    uuid = urlsafe_base64_encode(force_bytes("valid@gmail.com"))
    token = default_token_generator.make_token(user)
    response = self.post(
      {"password": "Test1Make@tcount", "password2": "Test1Make@tcount"}, 
      [uuid, token]
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    # check response data
    password_errors = json.loads(response.content).get('password')
    self.assertIsInstance(password_errors, list)
    self.assertEqual(
      password_errors[0],
      "You can not use your old password"
    )

  def test_passwod_reset_confirm_with_success_password_change(self):
    user = self.create_and_active_user(email="valid@gmail.com", password="Test1Make@tcount")
    uuid = urlsafe_base64_encode(force_bytes("valid@gmail.com"))
    token = default_token_generator.make_token(user)
    response = self.post(
      {"password": "Mytes1Make@tcount", "password2": "Mytes1Make@tcount"}, 
      [uuid, token]
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    # check response data
    self.assertEqual(
      response.data.get('message'), 
      "You password has been changed successfully"
    )
    # check user password has been changed
    user = get_object_or_404(self.user_model, email="valid@gmail.com")
    self.assertTrue(
      user.check_password("Mytes1Make@tcount")
    )
    # check user receive password change email
    mailbox = self.get_mailbox()[0]
    self.assertEqual(len(self.get_mailbox()), 1)
    self.assertIn("valid@gmail.com", mailbox.to)
    self.assertEqual("Password reset successfully", mailbox.subject)
    self.assertRegex(mailbox.body, "Your password for has been successfully changed.")