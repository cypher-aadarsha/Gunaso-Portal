from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Ministry, Department, Complaint, ComplaintUpdate, UserProfile


# --- User Admin ---
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile (Role & Ministry)'
    fk_name = 'user'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_select_related = ('profile',)

    def get_role(self, instance):
        try:
            return instance.profile.get_role_display()
        except UserProfile.DoesNotExist:
            return 'No Profile'

    get_role.short_description = 'Role'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# --- Ministry & Department Admins ---
@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'ministry', 'created_at')
    search_fields = ('name', 'ministry__name')
    list_filter = ('ministry',)


# --- Complaint Admins ---
class ComplaintUpdateInline(admin.TabularInline):
    model = ComplaintUpdate
    extra = 0
    readonly_fields = ('user', 'update_text', 'created_at')
    can_delete = False


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        'tracking_id',
        'title',
        'status',
        'created_by',
        'get_ministries',  # Display M2M
        'created_at',
        'ai_suggested_priority'
    )
    search_fields = ('title', 'tracking_id', 'created_by__username', 'ministries__name')
    list_filter = ('status', 'ministries', 'ai_suggested_priority')
    readonly_fields = (
        'tracking_id', 'created_by', 'created_at', 'updated_at',
        'ai_suggested_category', 'ai_suggested_priority'
    )
    inlines = [ComplaintUpdateInline]

    # Custom method to display M2M field in list
    def get_ministries(self, obj):
        return ", ".join([m.name for m in obj.ministries.all()])

    get_ministries.short_description = 'Ministries'


@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'user', 'created_at')
    search_fields = ('complaint__tracking_id', 'user__username')
    readonly_fields = ('complaint', 'user', 'update_text', 'created_at')