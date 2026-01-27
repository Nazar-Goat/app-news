from rest_framework import serializers
from apps.comments.models import Comment
from apps.posts.models import Post


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Comment model"""
    author = serializers.StringRelatedField()
    post = serializers.StringRelatedField()
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'content', 'author', 'author_info', 'parent',
            'is_active', 'replies_count', 'is_reply',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['author', 'is_active']

    def get_author_info(self, obj):
        user = obj.author
        return{
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'avatar': user.avatar.url if user.avatar else None
        }
    

class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Comment model instances"""
    class Meta:
        model = Comment
        fields =[
            'parent', 'content', 'post'
        ]

    def validate_post(self, value):
        if not Post.objects.filter(id=value.id).exists():
            raise serializers.ValidationError(
                "Post does not exist."
            )
        return value
        
    def validate_parent(self, value):
        if value and value.post != self.initial_data.get('post'):
            return serializers.ValidationError(
                "Parent comment must belong to the same post."
            )
        
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
    

class CommentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating Comment model instances"""

    class Meta:
        model = Comment
        fields =['content']

    
