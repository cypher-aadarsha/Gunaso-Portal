from rest_framework import permissions
from .models import UserProfile


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the complaint or a superuser.
        # FIXED: Changed 'submitted_by' to 'created_by' to match the Model
        return obj.created_by == request.user or request.user.is_superuser


class IsMinistryAdmin(permissions.BasePermission):
    """
    Custom permission to allow access only to admins of a specific ministry.
    """

    def has_permission(self, request, view):
        # Must be authenticated and have a profile
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return False

        # User must be an Admin and assigned to a ministry
        profile = request.user.profile
        # Check if role is ADMIN or SUPER (PMO)
        is_admin = profile.role == UserProfile.ROLE_CHOICES[1][0]  # ADMIN
        is_super = profile.role == UserProfile.ROLE_CHOICES[2][0]  # SUPER

        return (is_admin and profile.ministry is not None) or is_super

    def has_object_permission(self, request, view, obj):
        # Allow read access for safe methods
        if request.method in permissions.SAFE_METHODS:
            if not hasattr(request.user, 'profile'):
                return False

            # Super Admin (PMO) can see everything
            if request.user.profile.role == 'SUPER' or request.user.is_superuser:
                return True

            # Ministry Admin checks
            return obj.ministry == request.user.profile.ministry

        # Allow write access (e.g., updating status)
        if not hasattr(request.user, 'profile'):
            return False

        # Super Admin can edit everything
        if request.user.profile.role == 'SUPER' or request.user.is_superuser:
            return True

        # Ministry Admin can only edit their ministry's complaints
        return obj.ministry == request.user.profile.ministry


class IsCitizen(permissions.BasePermission):
    """
    Custom permission to allow access only to users with the 'CITIZEN' role.
    """

    def has_permission(self, request, view):
        # Must be authenticated and have a profile
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return False

        # User's role must be 'CITIZEN'
        return request.user.profile.role == 'CITIZEN'