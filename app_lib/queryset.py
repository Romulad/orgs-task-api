from organization.models import Department, Organization


class ModelDefaultQuerysets:

    def get_depart_queryset(self, default=False):
        queryset = Department.objects.all()

        if not default:
            queryset = Department.objects.all().select_related(
                "org", "created_by"
            ).prefetch_related(
                'members', "can_be_accessed_by"
            )
            
        return queryset

    def get_org_queryset(self, default=False):
        queryset = Organization.objects.all()

        if not default:
            queryset = Organization.objects.all().prefetch_related(
                    "members", "can_be_accessed_by"
                ).select_related(
                    "owner", "created_by"
                )
            
        return queryset

queryset_helpers = ModelDefaultQuerysets()
