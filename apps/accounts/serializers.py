from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    password_confirmation = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'password_confirmation']  

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirmation')
        user = User.objects.create(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        user.set_password(validated_data['password'])
        user.save()
        return user 
    

class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)

            if not user:
                raise serializers.ValidationError("User not found with provided credentials.")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            
            attrs['user'] = user
            return attrs 
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")
        

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    full_name = serializers.ReadOnlyField()
    posts_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'avatar', 'bio', 'created_at', 'updated_at',
            'posts_count', 'comments_count'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_posts_count(self, obj):
        try:
            return obj.posts.count()
        except  AttributeError:
            return 0
        
    def get_comments_count(self, obj):
        try:
            return obj.comments.count()
        except  AttributeError:
            return 0

class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'bio', 'avatar']

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance 
    
class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password"""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    new_password_confirmation = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirmation']:
            raise serializers.ValidationError({"new_password": "New password fields didn't match."})
        return attrs
    
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user 
