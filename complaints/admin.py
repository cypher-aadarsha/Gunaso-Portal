from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Ministry, Department, UserProfile, Complaint, ComplaintUpdate


# --- User Admin Customization ---

class UserProfileInline(admin.StackedInline):
    """
    This creates an "inline" editor for the UserProfile
    It allows you to edit the ministry/department directly on the User's page
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile (Ministry/Department Staff)'
    fk_name = 'user'


class CustomUserAdmin(UserAdmin):
    """
    Defines the custom admin view for the User model.
    It adds the UserProfile inline editor.
    """
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_ministry')
    list_select_related = ('profile',)

    def get_ministry(self, instance):
        """
        A custom method to display the user's ministry in the list view.
        """
        try:
            return instance.profile.ministry
        except UserProfile.DoesNotExist:
            return None

    get_ministry.short_description = 'Ministry'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)


# --- Complaint Admin Customization ---

class ComplaintUpdateInline(admin.TabularInline):
    """
    Allows viewing and adding updates directly on the Complaint's admin page.
    """
    model = ComplaintUpdate
    extra = 1  # Show one extra blank form for adding a new update
    readonly_fields = ('user', 'created_at')

    def has_change_permission(self, request, obj=None):
        # Make updates read-only in the inline view; they should be added, not edited.
        return False


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    """
    Defines the custom admin view for the Complaint model.
    This is where we fix the errors.
    """

    # --- FIX 1: Updated list_display fields ---
    list_display = (
        'tracking_id',
        'title',
        'ministry',
        'department',
        'ai_suggested_priority',  # Changed from 'priority'
        'status',
        'created_at'
        # Removed 'resolved_by'
    )

    # --- FIX 2: Updated list_filter fields ---
    list_filter = (
        'status',
        'ai_suggested_priority',  # Changed from 'priority'
        'ministry',
        'department',
        'created_at'
    )

    search_fields = ('title', 'description', 'tracking_id', 'created_by__username')

    # --- FIX 3: Updated readonly_fields ---
    readonly_fields = (
        'tracking_id',
        'created_by',
        'created_at',
        'updated_at',
        'ai_suggested_category',  # Changed from 'ai_category'
        'ai_suggested_priority',  # Changed from 'ai_priority'
        'ai_summary',
        'ai_corruption_risk'
    )

    # --- FIX 4: Updated fieldsets ---
    fieldsets = (
        (None, {'fields': ('tracking_id', 'title', 'description')}),
        ('Assignment', {'fields': ('ministry', 'department')}),
        ('Status', {'fields': ('status',)}),
        ('Submitter', {'fields': ('created_by', 'government_id_document')}),
        ('Files', {'fields': ('supporting_document',)}),

        # Correctly named AI fields
        ('AI Analysis (Read-Only)', {
            'classes': ('collapse',),
            'fields': (
                'ai_suggested_category',
                'ai_suggested_priority',
                'ai_summary',
                'ai_corruption_risk'
            )
        }),
        ('Dates', {'fields': ('created_at', 'updated_at')}),
    )

    inlines = [ComplaintUpdateInline]  # Add the updates inline

    def save_model(self, request, obj, form, change):
        """
        When an admin saves a Complaint (e.g., changes status),
        also create a ComplaintUpdate record.
        """
        old_obj = None
        if obj.pk:
            old_obj = Complaint.objects.get(pk=obj.pk)

        super().save_model(request, obj, form, change)

        if change and old_obj and form.cleaned_data.get('status') != old_obj.status:
            # The status was changed
            ComplaintUpdate.objects.create(
                complaint=obj,
                user=request.user,
                update_text=f"Status changed from {old_obj.status} to {obj.status}.",
                old_status=old_obj.status,
                new_status=obj.status
            )


# --- Register the Other Models ---

@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'ministry')
    list_filter = ('ministry',)
    search_fields = ('name', 'ministry__name')


@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'user', 'update_text', 'created_at')
    list_filter = ('complaint', 'user', 'created_at')
    search_fields = ('update_text',)
    readonly_fields = ('complaint', 'user', 'created_at', 'old_status', 'new_status')


# --- Re-register the User model with our custom admin ---
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)