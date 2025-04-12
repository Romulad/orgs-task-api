from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.shortcuts import get_object_or_404
from rest_framework import status

from ..base_classe import BaseTestClass
from auth_user.lib import validate_account_token_generator

class TestValidationAccountView(BaseTestClass):
  url_name = "validate_account"

  def test_validation_with_invalid_user_id(self):
    uuid = urlsafe_base64_encode(force_bytes("fake_udi"))
    path = reverse(self.url_name, args=[uuid, self.fake_token])
    response = self.client.get(path)
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = response.data
    self.assertEqual(data.get("message"), "Invalid or expired url")

  def test_validation_with_invalid_token(self):
    user = self.create_and_active_user(email="valid@gmail.com")
    uuid = urlsafe_base64_encode(force_bytes(user.email))
    path = reverse(self.url_name, args=[uuid, self.fake_token])
    response = self.client.get(path)
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    data = response.data
    self.assertEqual(data.get("message"), "Invalid or expired url")

  def test_validation_with_invalid_token_and_inative_account(self):
    user = self.create_user(email="valid@gmail.com", first_name="testnme")
    uuid = urlsafe_base64_encode(force_bytes(user.email))
    path = reverse(self.url_name, args=[uuid, self.fake_token])
    # make request
    response = self.client.get(path)
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    # check mail was send
    mail_sent = self.get_mailbox()[0]
    self.assertEqual(len(self.get_mailbox()), 1)
    self.assertEqual(mail_sent.to[0], "valid@gmail.com")
    self.assertIn("Welcome testnme", mail_sent.subject)
    self.assertRegex(mail_sent.body, "Please verify your email address by clicking the button below")
    # check response data
    data = response.data
    self.assertEqual(
      data.get("message"), 
      "Your account is still inactive. New mail has been sent to validate your account"
    )

  def test_validation_with_success(self):
    user = self.create_user(email="valid@gmail.com")
    uuid = urlsafe_base64_encode(force_bytes(user.email))
    token = validate_account_token_generator.make_token(user)
    path = reverse(self.url_name, args=[uuid, token])
    self.assertFalse(getattr(user, "is_active"))
    # make request and check status
    response = self.client.get(path)
    user = get_object_or_404(self.user_model, email="valid@gmail.com")
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertTrue(getattr(user, "is_active"))
    # check response data
    data = response.data
    self.assertEqual(data.get("message"), "Your account has been successfully activate")
    # check token invalidation
    self.assertEqual(
      self.client.get(path).status_code,
      status.HTTP_400_BAD_REQUEST
    )
