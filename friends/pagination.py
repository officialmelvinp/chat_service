from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class FriendsPagination(PageNumberPagination):
    """
    Custom pagination for friends-related endpoints
    Optimized for large datasets (celebrities, influencers)
    """
    page_size = 20
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
            ('results', data)
        ]))


class SearchPagination(PageNumberPagination):
    """
    Pagination specifically for user search
    Allows larger page sizes for better UX
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 50
    
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


class RequestsPagination(PageNumberPagination):
    """
    Pagination for friend requests
    Smaller page size for better mobile UX
    """
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.page.paginator.per_page),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))