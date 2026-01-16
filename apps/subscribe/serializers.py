from datetime import timedelta
from rest_framework import serializers
from django.utils import timezone
from .models import SubscriptionPlan, Subscription, PinnedPost
from django.core.exceptions import ObjectDoesNotExist


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plan model."""
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "duration_days",
            "features",
            "price",
        ]

    def to_representation(self, instance):
        """Check if the features field is empty and return an empty list instead of None."""
        
        data = super().to_representation(instance)

        if not data.get("features"):
            data['features'] = {}
        
        return data
    

class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscription"""
    plan_info = SubscriptionPlanSerializer(source='plan', read_only=True)
    user_info = serializers.SerializerMethodField()
    is_active = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user', 'user_info', 'plan', 'plan_info', 'status',
            'start_date', 'end_date', 'auto_renew', 'is_active',
            'days_remaining', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'start_date', 'end_date',
            'created_at', 'updated_at'
        ]

    def get_user_info(self, obj):
        """Возвращает информацию о пользователе"""
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'full_name': obj.user.full_name,
            'email': obj.user.email,
        }
    

class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for subscription model."""

    class Meta:
        model = Subscription
        fields =[
            "plan"
        ]

    def validate_plan(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "The selected subscription plan is inactive."
            )
        return value

    def validate(self, attrs):
        """Ensure user does not already have an active subscription."""
        user = self.context['request'].user
        try:
            subscription = user.subscription
        except ObjectDoesNotExist:
            subscription = None

        if subscription and subscription.is_active:
            raise serializers.ValidationError({
                'non_field_errors': ['User already has an active subscription.']
            })
        return attrs

    def create(self, validated_data):
        """Create a new subscription."""
        user = self.context['request'].user
        plan = validated_data['plan']

        start_date = timezone.now()
        end_date = start_date + timedelta(days=plan.duration_days)

        return Subscription.objects.create(
            user=user,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            status=Subscription.STATUS_ACTIVE
        )
    
    
class PinnedPostSerializer(serializers.ModelSerializer):
    """Сериализатор для закрепленного поста"""
    post_info = serializers.SerializerMethodField()
    
    class Meta:
        model = PinnedPost
        fields = ['id', 'post', 'post_info', 'pinned_at']
        read_only_fields = ['id', 'pinned_at']

    def get_post_info(self, obj):
        """Retun post validation"""
        return {
            'id': obj.post.id,
            'title': obj.post.title,
            'slug': obj.post.slug,
            'content': obj.post.content,
            'image': obj.post.image,
            'views_count': obj.post.views_count,
            'created_at': obj.post.created_at,
        }
    
    def validate_post(self, value):
        user = self.context['request'].user

        if value.author != user:
            raise serializers.ValidationError('You can ony pinned your posts.')
        
        if value.status != 'published':
            raise serializers.ValidationError('Only published posts can be pinned.')
        return value
    
    def validate(self, attrs):
        user = self.context['request'].user

        
        if not hasattr(user, 'subscription') or not user.subscription.is_active:
            raise serializers.ValidationError({
                'non_field_errors': ['Active subscription required to pin posts.']
            })
        
        return attrs
    
    def create(self, validated_data):
        """creates pinned post"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    

class UserSubscriptionStatusSerializer(serializers.Serializer):
    """User subscription serializer"""
    has_subscription = serializers.BooleanField()
    is_active = serializers.BooleanField()
    subscription = SubscriptionSerializer(allow_null=True)
    pinned_post = PinnedPostSerializer(allow_null=True)
    can_pin_posts = serializers.BooleanField()

    def to_representation(self, instance):
        """forms response with user subscription information"""
        user = instance
        has_subscription = hasattr(user, 'subscription')
        subscription = user.subscription if has_subscription else None
        is_active = subscription.is_active if subscription else False
        pinned_post = getattr(user, 'pinned_post', None) if is_active else None

        return {
            'has_subscription': has_subscription,
            'is_active': is_active,
            'subscription': SubscriptionSerializer(subscription).data if subscription else None,
            'pinned_post': PinnedPostSerializer(pinned_post).data if pinned_post else None,
            'can_pin_posts': is_active,
        }
    

class PinPostSerializer(serializers.Serializer):
    """Serializer class to pin a post ."""

    post_id = serializers.IntegerField()

    def validate_post_id(self, value):
        from apps.posts.models import Post

        try:
            post = Post.objects.get(id=value, is_active=True)
        except Post.DoesNotExist:
            raise serializers.ValidationError("Post not found or not published.")
        
        user = self.context['request'].user

        if post.author != user :
            raise serializers.ValidationError("You can pin only your own posts.")
        
    def validate(self, attrs):
        user = self.context['request'].user
        
        #check subscription
        if not hasattr(user, 'subscription') or not user.subscription.is_active:
            raise serializers.ValidationError({
                'non_field_errors': ['Active subscription required to pin posts.']
            })
        
        return attrs
    

class UnpinPostSerializer(serializers.Serializer):
    """Serializer to unpin post."""

    def validate(self, attrs):
        user = self.context['request'].user

        if not hasattr(user, 'pinned_post'):
            raise serializers.ValidationError({
                'non_field_errors': ['No pinned post found']
            })

        return attrs