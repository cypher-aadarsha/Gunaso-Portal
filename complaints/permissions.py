from rest_framework import permissions
from .models import UserProfile


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.created_by == request.user or request.user.is_superuser


class IsMinistryAdmin(permissions.BasePermission):
    """
    Custom permission to allow access only to admins of a specific ministry.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return False

        profile = request.user.profile
        is_admin = profile.role == 'ADMIN'
        is_super = profile.role == 'SUPER'
        return (is_admin and profile.ministry is not None) or is_super

    def has_object_permission(self, request, view, obj):
        # Allow read access for safe methods
        if request.method in permissions.SAFE_METHODS:
            if not hasattr(request.user, 'profile'):
                return False

            if request.user.profile.role == 'SUPER' or request.user.is_superuser:
                return True

            # UPDATED: Check if admin's ministry is IN the complaint's list of ministries
            admin_ministry = request.user.profile.ministry
            return admin_ministry in obj.ministries.all()

        # Allow write access
        if not hasattr(request.user, 'profile'):
            return False

        if request.user.profile.role == 'SUPER' or request.user.is_superuser:
            return True

        # UPDATED: Admin can only edit if their ministry is involved
        admin_ministry = request.user.profile.ministry
        return admin_ministry in obj.ministries.all()


class IsCitizen(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.role == 'CITIZEN'