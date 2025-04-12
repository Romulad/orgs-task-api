import json

from rest_framework import status

from ..base_classe import BaseTestClass

class TestResetPasswordView(BaseTestClass):
  url_name = "password_reset"

  def test_reset_password_with_empty_email(self):
    response = self.post({})
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    email_errors = json.loads(response.content).get('email')
    self.assertIsInstance(email_errors, list)
    self.assertEqual(email_errors[0], "The email field is required")

  def test_reset_password_with_invalid_email(self):
    response = self.post({"email": "invalidemail"})
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    email_errors = json.loads(response.content).get('email')
    self.assertIsInstance(email_errors, list)
    self.assertEqual(email_errors[0], "Please provide a valid email address")

  def test_reset_password_with_no_existed_email(self):
    response = self.post({"email": "validemail@gmail.com"})
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(response.data.get('message'), "Reset password email has been sent successfully")
    # check email box is empty, any email has been sent
    self.assertEqual(len(self.get_mailbox()), 0)
  
  def test_reset_password_with_existed_but_inactive_user(self):
    self.create_user(email="validemail@gmail.com")
    response = self.post({"email": "validemail@gmail.com"})
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(response.data.get('message'), "Reset password email has been sent successfully")
    # check email box is empty, any email has been sent
    self.assertEqual(len(self.get_mailbox()), 0)
  
  def test_reset_password_with_valid_and_active_email(self):
    self.create_and_active_user(email="validemail@gmail.com")
    response = self.post({"email": "validemail@gmail.com"})
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(response.data.get('message'), "Reset password email has been sent successfully")
    # reset password email should be sent
    mailbox = self.get_mailbox()[0]
    self.assertEqual(len(self.get_mailbox()), 1)
    self.assertEqual(mailbox.to[0], "validemail@gmail.com")
    self.assertEqual(mailbox.subject, "Reset your password")
    self.assertRegex(mailbox.body, "Click the button below to reset your password")
    self.assertRegex(mailbox.body, "http://testserver/auth/reset-password/")