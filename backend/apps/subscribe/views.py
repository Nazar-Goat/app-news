from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from .models import SubscriptionPlan, Subscription, PinnedPost
from .serializers import (
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
    SubscriptionCreateSerializer,
    PinnedPostSerializer,
    UserSubscriptionStatusSerializer,
    PinPostSerializer,
    UnpinPostSerializer
)
from apps.posts.models import Post


class SubscriptionPlanListView(generics.ListAPIView):
    """List of active subscription plans."""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]


class SubscriptionPlanDetailView(generics.RetrieveAPIView):
    """Detail information about specific subscription plan."""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]


class UserSubscriptionView(generics.RetrieveAPIView):
    """User subscription info"""
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        try:
            return self.request.user.subsctiprion
        except Subscription.DoesNotExist:
            return None
        
    def retrieve(self, request, *args, **kwargs):
        subscription = self.get_object()
        if subscription:
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        else:
            return Response({
                'message': 'Subscription not found'
            }, status=status.HTTP_404_NOT_FOUND)


class PinnedPostView(generics.RetrieveUpdateDestroyAPIView):
    """View for users pinned post 
    Operations: get, update, patch, destroy
    """
    serializer_class = PinnedPostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """returns users pinned post"""
        try: 
            return self.request.user.pinned_post
        except PinnedPost.DoesNotExist:
            return None
        
    def retrieve(self, request, *args, **kwargs):
        """returns information about pinned post"""
        pinned_post = self.get_object()
        if pinned_post:
            serializer = self.get_serializer(pinned_post)
            return Response(serializer.data)
        else:
            return Response({
                'message': 'Pinned post not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
    def update(self, request, *args, **kwargs):
        """updates pinned post"""
        if not hasattr(request.user, 'subscription') or not  request.user.subscription.is_active:
            return  Response({
                'error': 'User should have an active subscription to update pinned post'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)
        
    def destroy(self, request, *args, **kwargs):
        """delete pinned post if exist"""
        pinned_post = self.get_object()
        if pinned_post:
            pinned_post.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({
                'error': 'Post not found'
            }, status=status.HTTP_404_NOT_FOUND)        


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def pin_post(request):
    """Pins users post"""
    serializer = PinPostSerializer(data=request.data, context={'request':request})

    if serializer.is_valid():
        post_id = serializer.validated_data.get('post_id')

        try:
            with transaction.atomic():
                post = get_object_or_404(Post, id=post_id, status='published')

                if post.author != request.user:
                    return Response({
                        "error": "You can pin onlu your own posts."
                        }, status=status.HTTP_403_FORBIDDEN)
                
                if not hasattr(request.user, 'subscription') or not request.user.subscription.is_active:
                    return Response({
                        "error": "To pin your posts you should have an active subscription."
                    }, status=status.HTTP_403_FORBIDDEN)
                
                if hasattr(request.user, 'pinned_post'):
                    request.user.pinned_post.delete()

                pinned_post = PinnedPost.objects.create(
                    user=request.user,
                    post=post
                )

                response_serializer = PinnedPostSerializer(pinned_post)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unpin_post(request):
    serializer = UnpinPostSerializer(data=request.data, context={'request':request})

    if serializer.is_valid():
        try:
            post = request.user.pinned_post
            post.delete()

            return Response({
                'message': 'Post unpinned successfully.'
            }, status=status.HTTP_200_OK)
        
        except PinnedPost.DoesNotExist:
            return Response({
                'error': 'Pinned post not found'
            }, status=status.HTTP_404_NOT_FOUND)
        

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_subscription(request):
    """Cancels users subscriptions"""
    try:    
        subscription = request.user.subscription
    except Subscription.DoesNotExist:
        return Response({
            'error': 'Subscription not found.'
        }, status=status.HTTP_404_NOT_FOUND)

    if not subscription.is_active():
                return Response({
                    'error': 'To cancel subscription it has to be active.'
                }, status=status.HTTP_403_FORBIDDEN)       

    with transaction.atomic():
        subscription.cancel_subscription()
        
        if hasattr(request.user, 'pinned_post'):
            request.user.pinned_post.delete()

    return Response({
        'message': 'Subscription cancelled successfully.'
    }, status=status.HTTP_200_OK)
        
    
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def subscription_status(request):
    """Returns users subscription status"""

    serializer = UserSubscriptionStatusSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def pinned_posts_list(request):
    """Returns list of pinned posts"""
    #recieve pinned posts by users with active subscription
    pinned_posts= PinnedPost.objects.select_related(
        'post', 'post__author', 'post__category', 'user__subscription'
    ).filter(
        user__subscription__status='active',
        user__subscription__end_date__gt=timezone.now(),
        post__status='published'
    ).order_by('pinned_at')

    #add objects from queryset into list and redact them 
    pinned_posts_data = []
    for pinned_post in pinned_posts:
        post = pinned_post.post
        pinned_posts_data.append({
            'id': post.id,
            'title': post.title,
            'content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
            'image': post.image.url if post.image  else None,
            'category': post.category.name if post.category else None,
            'author': {
                'id': post.author.id,
                'username': post.author.username,
                'full_name': post.author.full_name
            },
            'views_count': post.views_count,
            'comments_count': post.comments_count,
            'created_at': post.created_at,
            'pinned_at': pinned_post.pinned_at,
            'is_pinned': True
        })

    #return list with data
    return Response({
        'count': len(pinned_posts_data),
        'result': pinned_posts_data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def can_pin_post(request, post_id):
    #get post by id or throw exception
    try:
        post = get_object_or_404(Post, id=post_id, status='published')

        #post cheks
        checks= {
            'post_exist': True,
            'its_own_post': request.user == post.author,
            'has_subscription': hasattr(request.user, 'subscription'),
            'is_active_subscription': False,
            'can_pin': False
        }

        if checks['has_subscription']:
            checks['is_active_subscription'] = request.user.subscription.is_active

        checks['can_pin'] = (
            checks['its_own_post'] and
            checks['has_subscription'] and
            checks['is_active_subscription']
        )

        return Response({
            'post_id': post_id,
            'can_pin': checks['can_pin'],
            'checks': checks,
            'message': 'You can pin post' if checks['can_pin'] else "You can't pin post"
        })

    except Post.DoesNotExist:
        return Response({
            'post_id': post_id,
            'can_pin': False,
            'checks': {'post_exist': False},
            'message': 'Post not found'
        }, status=status.HTTP_404_NOT_FOUND)