import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# --- Ministry and Department Models ---

class Ministry(models.Model):
    """
    Represents a government ministry.
    e.g., "Ministry of Finance", "Ministry of Health"
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Department(models.Model):
    """
    Represents a department or wing within a ministry.
    e.g., "Inland Revenue Department" (under Ministry of Finance)
    """
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('ministry', 'name')

    def __str__(self):
        return f"{self.name} ({self.ministry.name})"


# --- User Profile Model ---

class UserProfile(models.Model):
    """
    Extends the built-in User model to add ministry/department
    for Admin-level users.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Staff users (Admins) are tied to a ministry or specific department
    ministry = models.ForeignKey(Ministry, on_delete=models.SET_NULL, blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal to automatically create/update UserProfile when a User is created/updated.
    """
    if created:
        UserProfile.objects.create(user=instance)
    instance.profile.save()


# --- Complaint Models ---

def get_complaint_document_path(instance, filename):
    """
    Generates a unique path for uploaded complaint documents.
    File will be uploaded to MEDIA_ROOT/complaints/<tracking_id>/<filename>
    """
    return os.path.join('complaints', str(instance.tracking_id), filename)


def get_id_document_path(instance, filename):
    """
    Generates a unique path for user ID documents.
    File will be uploaded to MEDIA_ROOT/user_ids/<user_id>/<filename>
    """
    # Note: This 'instance' is the Complaint, not the User.
    return os.path.join('user_ids', str(instance.created_by.id), filename)


class Complaint(models.Model):
    """
    The main model for lodging a grievance.
    """

    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        REJECTED = 'REJECTED', 'Rejected'
        FORWARDED = 'FORWARDED', 'Forwarded'

    class PriorityChoices(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    # --- Tracking & Categorization ---
    tracking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)

    # --- Complainant Info ---
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='complaints')
    # Store the user's ID document with the *first* complaint they file
    government_id_document = models.FileField(
        upload_to=get_id_document_path,
        blank=True,
        null=True
    )

    # --- Complaint Details ---
    ministry = models.ForeignKey(Ministry, on_delete=models.PROTECT, related_name='complaints')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, blank=True, null=True,
                                   related_name='complaints')
    title = models.CharField(max_length=255)
    description = models.TextField()
    supporting_document = models.FileField(
        upload_to=get_complaint_document_path,
        blank=True,
        null=True
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- AI-Powered Fields (set by Celery task) ---
    ai_suggested_category = models.CharField(max_length=255, blank=True, null=True)
    ai_suggested_priority = models.CharField(
        max_length=20,
        choices=PriorityChoices.choices,
        blank=True,
        null=True
    )
    ai_summary = models.TextField(blank=True, null=True)
    ai_corruption_risk = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.tracking_id})"

    class Meta:
        ordering = ['-created_at']


class ComplaintUpdate(models.Model):
    """
    A model to store updates, comments, or status changes
    for a specific complaint. This creates a history log.
    """
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='updates')
    user = models.ForeignKey(User, on_delete=models.PROTECT, help_text="User who made the update (Admin or Citizen)")
    update_text = models.TextField(help_text="The content of the update or comment")
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: Store the old and new status to track changes
    old_status = models.CharField(max_length=20, choices=Complaint.StatusChoices.choices, blank=True, null=True)
    new_status = models.CharField(max_length=20, choices=Complaint.StatusChoices.choices, blank=True, null=True)

    def __str__(self):
        return f"Update for {self.complaint.tracking_id} by {self.user.username}"

    class Meta:
        ordering = ['-created_at']