from rest_framework import generics, permissions, filters
from .models import Comment 
from .serializers import (
    CommentSerializer,
    CommentCreateSerializer,
    CommentUpdateSerializer,
)

from .permissions import IsAuthorOrReadOnly

class CommentListCreateView(generics.ListCreateAPIView):
    """View for listing and creating comments for a specific post."""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        post_id = self.kwargs.get('post_id')
        return Comment.objects.filter(post__id=post_id, is_active=True, parent=None).select_related('post', 'author')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentSerializer


class CommentDetailsView(generics.RetrieveUpdateDestroyAPIView):
    """View for retrieving and updating a specific comment."""
    queryset = Comment.objects.select_related('post', 'author').all()
    serializer_class =CommentUpdateSerializer
    permission_classes = [IsAuthorOrReadOnly]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class MyCommentsListView(generics.ListAPIView):
    """View for listing comments made by the authenticated user."""
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Comment.objects.filter(author=self.request.user, is_active=True).select_related('post', 'author')
    

    
    



