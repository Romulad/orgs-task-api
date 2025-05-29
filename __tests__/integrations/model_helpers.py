import uuid

from django.contrib.auth import get_user_model

from organization.models import Department, Organization
from user.models import AppUser as User


class TestModelHelpers:

    def __init__(self):
        self.user_model : User = get_user_model()    
   
    def bulk_create_object(self, model, data):
        created = model.objects.bulk_create([
            model(**data) for data in data
        ])
        return created
    
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
    
    def create_and_activate_random_user(self):
        return self.create_and_active_user(
            email="%s@exampletest.co" % (str(uuid.uuid4()))
        )
    
    def create_new_org(
        self,
        name=None,
        owner=None,
        creator=None
    ):
        """Create a new org, return owner_user, org_creator and org"""
        new_owner = self.create_and_activate_random_user() if not owner else owner
        new_org_creator = self.create_and_activate_random_user() if not creator else creator

        new_org = Organization.objects.create(
            name = str(uuid.uuid4()) if not name else name,
            owner = new_owner, 
            created_by = new_org_creator
        )
        return new_owner, new_org_creator, new_org

    def create_new_depart(self, org, name=None, creator=None):
        """Create a new depart in `org`, return creator and depart objects"""
        new_creator = self.create_and_activate_random_user() if not creator else creator
        depart = Department.objects.create(
            name = str(uuid.uuid4()) if not name else name,
            org = org,
            created_by = new_creator
        )
        return new_creator, depart