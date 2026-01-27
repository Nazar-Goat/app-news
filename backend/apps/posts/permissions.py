
from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Users can modify only their own posts.
    """

    def has_object_permission(self, request, view, obj):
        #permission to read to any request 
        if request.method in permissions.SAFE_METHODS:
            return True
        
        #permission to write only to posts author 
        return obj.author == request.user