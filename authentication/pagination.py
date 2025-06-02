from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class UserListPagination(PageNumberPagination):
    """
    Pagination for user listings (admin, search, etc.)
    Consistent with friends app pagination
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.page.paginator.per_page),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('has_more', self.page.has_next()),
            ('results', data)
        ]))