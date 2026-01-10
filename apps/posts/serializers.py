
from django.utils.text import slugify
from rest_framework import serializers
from apps.posts.models import Category, Post


class CategorySerializer(serializers.ModelSerializer):
    """serializer for Category model"""

    posts_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'posts_count', 'created_at']
        read_only_fields = ['slug','created_at']

    def get_posts_count(self, obj):
        return obj.posts.filter(status='published').count()
    
    def create(self, validated_data):
        validated_data['slug']  = slugify(validated_data['name'])
        return super().create(validated_data)
    

class PostListSerializer(serializers.ModelSerializer):
    """Serializer for listing Post model instances"""

    author = serializers.StringRelatedField()
    category = serializers.StringRelatedField()
    comments_count = serializers.ReadOnlyField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'image', 'category',
            'author', 'status', 'created_at', 'updated_at',
            'view_count', 'comments_count',
        ]
        read_only_fields = ['slug', 'author', 'view_count']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if len(data['content']) > 200:
            data['content'] = data['content'][:200 ]+ '...'
        return data
    

class PostDetailSerializer(serializers.ModelSerializer):
    """serializer for detailed Post model instances"""

    author_info = serializers.SerializerMethodField()
    category_info = serializers.SerializerMethodField()
    comments_count = serializers.ReadOnlyField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'image', 'category',
            'author', 'status', 'created_at', 'updated_at',
            'view_count', 'comments_count', 'author_info', 'category_info'
        ]
        read_only_fields = ['slug', 'author', 'view_count']

    def get_author_info(self, obj):
        author = obj.author
        return {
            'id': author.id,
            'username': author.username,
            'full_name': author.full_name,
            'avatar': author.avatar.url if author.avatar else None
        }
    
    def get_category_info(self, obj):
        category = obj.category
        if category:
            return {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
            }
        return None
    

class PostCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating Post model instances"""
    class Meta:
        model = Post
        fields = [
            'title', 'content', 'image', 'category', 'status'
        ]

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['slug'] = slugify(validated_data['title'])
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        if 'title' in validated_data:
            validated_data['slug'] = slugify(validated_data['title'])
        return super().update(instance, validated_data)
    
