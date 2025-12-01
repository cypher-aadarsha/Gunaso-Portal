from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Ministry, Department, Complaint, ComplaintUpdate, UserProfile


# --- User Admin ---

class UserProfileInline(admin.StackedInline):
    """
    This allows us to edit the UserProfile (role, ministry)
    directly inside the User's admin page.
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile (Role & Ministry)'
    fk_name = 'user'


class CustomUserAdmin(BaseUserAdmin):
    """
    A custom User admin that includes the UserProfile inline.
    """
    inlines = (UserProfileInline,)

    # Add 'get_role' to the list display
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_select_related = ('profile',)

    def get_role(self, instance):
        """Fetches the role from the user's profile."""
        try:
            return instance.profile.get_role_display()
        except UserProfile.DoesNotExist:
            return 'No Profile'

    get_role.short_description = 'Role'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# --- Ministry & Department Admins ---

@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    """
    Admin view for Ministries.
    (Fix: Removed 'description' which doesn't exist)
    """
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """
    Admin view for Departments.
    """
    list_display = ('name', 'ministry', 'created_at')
    search_fields = ('name', 'ministry__name')
    list_filter = ('ministry',)


# --- Complaint Admins ---

class ComplaintUpdateInline(admin.TabularInline):
    """
    Allows viewing (but not adding) complaint updates
    directly from the Complaint admin page.
    """
    model = ComplaintUpdate
    extra = 0  # Don't show any extra 'add' forms
    readonly_fields = ('user', 'update_text', 'created_at')
    can_delete = False


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    """
    The main admin view for managing Complaints.
    (Fix: Removed fields that don't exist like 'ai_summary')
    """
    list_display = (
        'tracking_id',
        'title',
        'status',
        'created_by',
        'ministry',
        'department',
        'created_at',
        'ai_suggested_priority'  # Added the correct field
    )
    search_fields = ('title', 'tracking_id', 'created_by__username', 'ministry__name')
    list_filter = ('status', 'ministry', 'ai_suggested_priority')

    # Make fields read-only
    readonly_fields = (
        'tracking_id',
        'created_by',
        'created_at',
        'updated_at',
        'ai_suggested_category',  # Added the correct field
        'ai_suggested_priority'  # Added the correct field
    )

    # Add the updates inline
    inlines = [ComplaintUpdateInline]


@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    """
    A separate admin view for just looking at Complaint Updates.
    (Fix: Removed 'old_status' and 'new_status')
    """
    list_display = ('complaint', 'user', 'created_at')
    search_fields = ('complaint__tracking_id', 'user__username')
    readonly_fields = ('complaint', 'user', 'update_text', 'created_at')