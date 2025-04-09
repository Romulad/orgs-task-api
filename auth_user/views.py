from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

from .serializers import (
  RegistrationSerializer,
  RegistrationResponseSerializer
)

class RegistrationView(APIView):
  serializer_class = RegistrationSerializer

  @extend_schema(
      request=RegistrationSerializer,
      responses={201: RegistrationResponseSerializer},
  )
  def post(self, request:Request):
    """
    # Create a new user
    Use this endpoint to create a **new** account
    """
    req_data = request.data
    serializer = self.serializer_class(data=req_data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(
        RegistrationResponseSerializer(user).data,
        status=status.HTTP_201_CREATED
    )
