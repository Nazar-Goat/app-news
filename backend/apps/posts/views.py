from genericpath import exists
from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Exists, OuterRef
from django.shortcuts import get_object_or_404

from .models import Category, Post
from .serializers import (
    CategorySerializer,
    PostListSerializer,
    PostDetailSerializer,
    PostCreateUpdateSerializer
)
from .permissions import IsAuthorOrReadOnly


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class CategoryDetailsView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'


class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'author', 'status']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'updated_at', 'view_count', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        from apps.subscribe.models import PinnedPost
        
        queryset = Post.objects.select_related('author', 'category')
        
        # filtering based on user authentication
        if not self.request.user.is_authenticated:
            # non-authenticated users see only published posts
            queryset = queryset.filter(status='published')
        else:
            # authorized users see published and their own drafts
            queryset = queryset.filter(
                Q(status='published') | Q(author=self.request.user)
            )
        
        # check if ordering is by created_at to show pinned posts first
        ordering = self.request.query_params.get('ordering', '')
        show_pinned_first = not ordering or ordering in ['-created_at', 'created_at']
        
        if show_pinned_first:
            # adding annotation to indicate if post is pinned
            queryset = queryset.annotate(
                has_pin=Exists(
                    PinnedPost.objects.filter(post_id=OuterRef('pk'))
                )
            )
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateUpdateSerializer
        return PostListSerializer
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # pinned posts statistics
        if hasattr(response, 'data') and 'results' in response.data:
            pinned_count = sum(1 for post in response.data['results'] if post.get('is_pinned', False))
            response.data['pinned_posts_count'] = pinned_count
        
        return response


class PostDetailsView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.select_related('author', 'category').all()
    serializer_class = PostDetailSerializer
    permission_classes = [IsAuthorOrReadOnly]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PostCreateUpdateSerializer
        return PostDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if request.method == 'GET':
            instance.increment_view_count()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    

class MyPostsView(generics.ListAPIView):
    serializer_class = PostListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'status']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'updated_at', 'views_count', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        return Post.objects.filter(
            author=self.request.user
        ).select_related('author', 'category')
    
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def pinned_posts_only(request):
    """Only pinned posts"""
    posts = Post.objects.pinned_posts()
    serializer = PostListSerializer(
        posts,
        many=True,
        context={'request': request}
    )
    return Response({
        'count': posts.count(),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def featured_posts(request):
    """
    Posts for main page:
    - Pinned posts (max 3)
    - Popular posts for last week
    """
    from django.utils import timezone
    from datetime import timedelta
    
    # get last 3 pinned posts
    pinned_posts = Post.objects.pinned_posts()[:3]
    
    # Get popular posts in a week (pinned posts not included)
    week_ago = timezone.now() - timedelta(days=7)
    popular_posts = Post.objects.with_subscription_info().filter(
        status='published',
        created_at__gte=week_ago
    ).exclude(
        id__in=[post.id for post in pinned_posts]
    ).order_by('-view_count')[:6]
    
    # Serializing data
    pinned_serializer = PostListSerializer(
        pinned_posts, 
        many=True, 
        context={'request': request}
    )
    popular_serializer = PostListSerializer(
        popular_posts, 
        many=True, 
        context={'request': request}
    )
    
    return Response({
        'pinned_posts': pinned_serializer.data,
        'popular_posts': popular_serializer.data,
        'total_pinned': Post.objects.pinned_posts().count()
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_post_pin_status(request, slug):
    """
    Changes pinned post status.
    If pinned - unpin. If not pinned - pin post
    """
    post = get_object_or_404(Post, slug=slug, author=request.user, status='published')
    
    # Check subscription
    if not hasattr(request.user, 'subscription') or not request.user.subscription.is_active:
        return Response({
            'error': 'Active subscription required to pin posts'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from apps.subscribe.models import PinnedPost
        
        # checking if post is pinned
        if post.is_pinned:
            # Открепляем
            post.pinned_info.delete()
            message = 'Post unpinned successfully'
            is_pinned = False
        else:
            # delete existing users pinned post 
            if hasattr(request.user, 'pinned_post'):
                request.user.pinned_post.delete()
            
            # pin new post
            PinnedPost.objects.create(user=request.user, post=post)
            message = 'Post pinned successfully'
            is_pinned = True
        
        return Response({
            'message': message,
            'is_pinned': is_pinned,
            'post': PostDetailSerializer(post, context={'request': request}).data
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
