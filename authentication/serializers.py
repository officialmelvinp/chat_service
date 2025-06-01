from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from datetime import date

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile display"""
    age = serializers.ReadOnlyField()  # Calculated property
    full_name = serializers.ReadOnlyField(source='get_full_name')
    interests_list = serializers.ReadOnlyField()  # Calculated property
    languages_list = serializers.ReadOnlyField()  # Calculated property
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'bio', 'avatar', 'date_of_birth', 'age', 'gender', 'relationship_status',
            'country', 'city', 'interests', 'interests_list', 'languages', 'languages_list',
            'is_online', 'last_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['is_online', 'last_active', 'created_at', 'updated_at']

class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration - minimal fields"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile - all optional fields"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'bio', 'avatar', 
            'date_of_birth', 'gender', 'relationship_status',
            'country', 'city', 'interests', 'languages'
        ]
    
    def validate_date_of_birth(self, value):
        """Validate that date of birth is not in the future"""
        if value and value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value
    
    def validate_gender(self, value):
        """Validate gender against choices"""
        if value and value not in dict(User.GENDER_CHOICES).keys():
            valid_choices = ', '.join(dict(User.GENDER_CHOICES).keys())
            raise serializers.ValidationError(f"Invalid gender. Choose from: {valid_choices}")
        return value
    
    def validate_relationship_status(self, value):
        """Validate relationship status against choices"""
        if value and value not in dict(User.RELATIONSHIP_STATUS_CHOICES).keys():
            valid_choices = ', '.join(dict(User.RELATIONSHIP_STATUS_CHOICES).keys())
            raise serializers.ValidationError(f"Invalid relationship status. Choose from: {valid_choices}")
        return value

class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for user lists"""
    age = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 
            'avatar', 'bio', 'age', 'gender', 'relationship_status',
            'country', 'city', 'interests', 'languages',
            'is_online', 'last_active'
        ]
