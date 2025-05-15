import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from user.models import AppUser as User
from app_lib.jwt import get_tokens_for_user


class BaseTestClass(APITestCase):
  """Add common methods needed across test classes"""
  url_name: str
  fake_token = "co43bu-d6272225128184b0b8107dffba6e8564"
  HTTP_POST = "POST"
  HTTP_GET = "GET"
  HTTP_PUT = "PUT"
  HTTP_PATCH = "PATCH"
  HTTP_DELETE = "DELETE"
  HTTP_METHODS = [
    HTTP_POST, HTTP_GET, HTTP_PUT, HTTP_PATCH, HTTP_DELETE
  ]

  def __init__(self, methodName = "runTest"):
    super().__init__(methodName)
    self.client = APIClient()
    self.user_model : User = get_user_model()
    self.status = status
  
  def get_mailbox(self):
    return mail.outbox
  
  def create_user(
      self, 
      email="myemail@gmail.com", 
      password="testpassword",
      **kwargs
  ) -> User :
    created_user = self.user_model.objects.create_user(
      email=email, password=password, is_active=False, **kwargs
    )
    return created_user

  def bulk_create_object(self, model, data):
    created = model.objects.bulk_create([
        model(**data) for data in data
    ])
    return created
  
  def create_and_active_user(
      self, 
      email="myemail@gmail.com", 
      password="testpassword",
      **kwargs
  ) -> User :
    created_user = self.create_user(email, password, **kwargs)
    created_user.is_active = True
    created_user.save()
    return created_user
  
  def loads(self, content):
    return json.loads(content)
  
  def get_ids_from(self, objs):
    return [obj.id for obj in objs]

  def get(
      self, 
      args: list | None = None, 
      headers=None,
      query_params=None
  ) -> Response:
    path = reverse(self.url_name, args=args)
    return self.client.get(
      path, headers=headers, 
      query_params=query_params
    )

  def post(self, data: dict, args: list | None = None, headers=None) -> Response:
    path = reverse(self.url_name, args=args)
    return self.client.post(path, data, headers=headers)

  def put(self, data: dict, args: list | None = None, headers=None) -> Response:
    path = reverse(self.url_name, args=args)
    return self.client.put(path, data, headers=headers)
  
  def patch(self, data: dict, args: list | None = None, headers=None) -> Response:
    path = reverse(self.url_name, args=args)
    return self.client.patch(path, data, headers=headers)

  def delete(self, data: dict={}, args: list | None = None, headers=None) -> Response:
    path = reverse(self.url_name, args=args)
    return self.client.delete(path, data, headers=headers)
  
  def auth_post(self, user: User, data: dict, args: list | None = None) -> Response:
    access, _ = self.get_tokens(user)
    return self.post(
        data, args, headers={"Authorization": f"Bearer {access}"}
    )
  
  def auth_put(self, user: User, data: dict, args: list | None = None) -> Response:
    access, _ = self.get_tokens(user)
    return self.put(
        data, args, headers={"Authorization": f"Bearer {access}"}
    )

  def auth_patch(self, user: User, data: dict, args: list | None = None) -> Response:
    access, _ = self.get_tokens(user)
    return self.patch(
        data, args, headers={"Authorization": f"Bearer {access}"}
    )

  def auth_delete(self, user: User, data: dict={}, args: list | None = None) -> Response:
    access, _ = self.get_tokens(user)
    return self.delete(
        data, args, headers={"Authorization": f"Bearer {access}"}
    )

  def auth_get(
      self, user: User, 
      args: list | None = None,
      query_params=None
    ) -> Response:
    access, _ = self.get_tokens(user)
    return self.get(
        args, headers={"Authorization": f"Bearer {access}"},
        query_params=query_params
    )

  def evaluate_method_unauthenticated_request(self, method: str, args: list | None = None):
    if method in [self.HTTP_POST, self.HTTP_PUT, self.HTTP_PATCH, self.HTTP_DELETE]:
      response = getattr(self, method.lower())({}, args)
    else:
      response = getattr(self, method.lower())(args)
    # evaluate the response
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    error = json.loads(response.content).get('detail', None)
    self.assertIsNotNone(error)
  
  def get_tokens(self, user: User) -> str:
    tokens = get_tokens_for_user(user)
    access, refresh = tokens.get("access", None), tokens.get("refresh", None)
    return access, refresh if isinstance(tokens, dict) else None
  