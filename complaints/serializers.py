from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from .models import Complaint, Ministry, Department, ComplaintUpdate, UserProfile


# --- User & Registration Serializers ---

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserProfile model.
    Now supports updating User details (email, names).
    """
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)

    class Meta:
        model = UserProfile
        fields = ['user', 'role', 'ministry', 'department', 'government_id_document', 'first_name', 'last_name',
                  'email']
        read_only_fields = ['user', 'role', 'ministry', 'department', 'government_id_document']

    def update(self, instance, validated_data):
        # Extract the user data (email, first_name, etc.)
        user_data = validated_data.pop('user', {})

        user = instance.user

        # Update User fields if provided
        if 'email' in user_data:
            user.email = user_data['email']
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']

        user.save()

        # Update any remaining Profile fields
        return super().update(instance, validated_data)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    government_id_document = serializers.FileField(required=True, write_only=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name', 'government_id_document')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        attrs.pop('password2')
        return attrs

    def create(self, validated_data):
        government_id_document = validated_data.pop('government_id_document')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')

        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=first_name,
                last_name=last_name
            )
            UserProfile.objects.create(
                user=user,
                government_id_document=government_id_document,
                role='CITIZEN'
            )
        return user


# --- Main App Serializers ---

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class MinistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ministry
        fields = ['id', 'name']


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'ministry']


class ComplaintUpdateSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    # FIX: Added complaint_id field so the serializer accepts it from the frontend
    # This maps the incoming 'complaint_id' to the model's 'complaint' relationship
    complaint_id = serializers.PrimaryKeyRelatedField(
        queryset=Complaint.objects.all(),
        source='complaint',
        write_only=True
    )

    class Meta:
        model = ComplaintUpdate
        fields = ['id', 'user', 'update_text', 'created_at', 'complaint_id']


class ComplaintSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    updates = ComplaintUpdateSerializer(many=True, read_only=True)
    ministry = serializers.StringRelatedField(read_only=True)
    department = serializers.StringRelatedField(read_only=True)
    ministry_id = serializers.PrimaryKeyRelatedField(queryset=Ministry.objects.all(), source='ministry',
                                                     write_only=True)
    department_id = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), source='department',
                                                       write_only=True)

    class Meta:
        model = Complaint
        fields = [
            'tracking_id', 'title', 'description', 'status', 'created_at', 'updated_at',
            'created_by', 'ministry', 'department', 'ministry_id', 'department_id',
            'attachment', 'updates', 'ai_suggested_category', 'ai_suggested_priority',
        ]
        read_only_fields = ('tracking_id', 'created_at', 'updated_at', 'created_by',
                            'updates', 'status', 'ai_suggested_category', 'ai_suggested_priority')