from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """Users can modify only their own comments."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user