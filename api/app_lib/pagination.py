from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

class DefaultCursorPagination(CursorPagination):
    ordering = '-created_at'
    page_size = 50
    max_page_size = 500

    def paginate_queryset(self, queryset, request, view=None):
        self.total_count = len(queryset)
        return super().paginate_queryset(queryset, request, view)
    
    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'total_count': self.total_count,
            'results': data
        })