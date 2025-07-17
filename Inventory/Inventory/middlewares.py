# Inventory/middlewares.py - Enhanced with admin security
import logging
from django.db import DatabaseError
from django.shortcuts import render
from django.http import Http404
from django.urls import resolve
from django.contrib.auth.models import Group

logger = logging.getLogger('server')


class AjaxMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        def is_ajax(self):
            return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        
        request.is_ajax = is_ajax.__get__(request)
        response = self.get_response(request)
        return response


class HandleDatabaseErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except DatabaseError as e:
            logger.error(f"Database error occurred: {e}")
            return render(request, 'error/500.html', status=500)


class AdminSecurityMiddleware:
    """
    Middleware to enforce admin security restrictions:
    - Block access to Groups admin
    - Block direct access to user permissions
    - Prevent URL manipulation to bypass restrictions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs to block completely
        self.blocked_patterns = [
            '/admin/auth/group/',           # Groups list
            '/admin/auth/group/add/',       # Add group
        ]
        
        # URL patterns that contain restricted access
        self.restricted_patterns = [
            '/admin/auth/group/',           # Any group-related URL
        ]

    def __call__(self, request):
        # Only apply security to admin URLs
        if request.path.startswith('/admin/'):
            
            # Block direct access to groups
            for pattern in self.blocked_patterns:
                if request.path.startswith(pattern):
                    logger.warning(f"Blocked admin access attempt to {request.path} by user {request.user}")
                    raise Http404("Page not found")
            
            # Block any group-related URLs (including individual group edits)
            for pattern in self.restricted_patterns:
                if pattern in request.path and '/group/' in request.path:
                    logger.warning(f"Blocked group admin access attempt to {request.path} by user {request.user}")
                    raise Http404("Page not found")
            
            # Log admin access for security monitoring
            if request.user.is_authenticated and request.user.is_staff:
                logger.info(f"Admin access: {request.user.username} accessed {request.path}")

        response = self.get_response(request)
        return response