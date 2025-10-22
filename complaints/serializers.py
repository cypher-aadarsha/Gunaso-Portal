from rest_framework import serializers
from .models import Complaint, Ministry, Department, ComplaintUpdate, UserProfile
from django.contrib.auth.models import User


class MinistrySerializer(serializers.ModelSerializer):
    """
    Serializer for the Ministry model.
    """

    class Meta:
        model = Ministry
        fields = ['id', 'name', 'description']


class DepartmentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Department model.
    """

    class Meta:
        model = Department
        fields = ['id', 'name', 'ministry']


# --- User & Profile Serializers ---

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserProfile model (for staff).
    """

    class Meta:
        model = UserProfile
        fields = ['ministry', 'department']


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the built-in User model.
    """
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile', 'is_staff']


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for new user registration.
    """

    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        # We don't create a UserProfile here, as that's for staff admins.
        return user


# --- Complaint & Update Serializers ---

class ComplaintUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing complaint updates.
    """
    user = serializers.StringRelatedField()  # Show username, not ID

    class Meta:
        model = ComplaintUpdate
        fields = ['id', 'user', 'update_text', 'created_at', 'old_status', 'new_status']


class ComplaintSerializer(serializers.ModelSerializer):
    """
    The main serializer for creating and viewing complaints.
    """
    # Use StringRelatedField to show names instead of just IDs on read
    created_by = serializers.StringRelatedField(read_only=True)
    ministry_name = serializers.CharField(source='ministry.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    # Show the full history of updates when reading a single complaint
    updates = ComplaintUpdateSerializer(many=True, read_only=True)

    class Meta:
        model = Complaint
        fields = [
            'tracking_id', 'status', 'created_by', 'ministry', 'ministry_name',
            'department', 'department_name', 'title', 'description',
            'supporting_document', 'government_id_document',
            'created_at', 'updated_at', 'updates',
            'ai_suggested_category', 'ai_suggested_priority', 'ai_summary', 'ai_corruption_risk'
        ]

        # These fields are read-only (set by server or AI)
        read_only_fields = [
            'tracking_id', 'status', 'created_by', 'updates', 'created_at', 'updated_at',
            'ai_suggested_category', 'ai_suggested_priority', 'ai_summary', 'ai_corruption_risk',
            'ministry_name', 'department_name'
        ]

        # These fields are for *writing* (creating a complaint)
        # We make them 'write_only' so they don't clutter the read response
        extra_kwargs = {
            'ministry': {'write_only': True, 'required': True},
            'department': {'write_only': True, 'required': False, 'allow_null': True},
            'title': {'write_only': True, 'required': True},
            'description': {'write_only': True, 'required': True},
            'supporting_document': {'write_only': True, 'required': False},
            'government_id_document': {'write_only': True, 'required': True},  # Make ID required
        }