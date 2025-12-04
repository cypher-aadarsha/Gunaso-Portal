import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# --- Ministry and Department Models ---

class Ministry(models.Model):
    """
    Represents a government ministry.
    """
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Department(models.Model):
    """
    Represents a specific department or office within a ministry.
    """
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('ministry', 'name')

    def __str__(self):
        return f"{self.name} ({self.ministry.name})"


# --- User Profile Model (UPDATED) ---

def get_id_document_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{instance.user.id}_{uuid.uuid4()}.{ext}"
    return f"id_documents/{filename}"


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('CITIZEN', 'Citizen'),
        ('ADMIN', 'Admin'),
        ('SUPER', 'Super Admin')
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='CITIZEN')

    # NEW FIELD: Phone Number
    phone_number = models.CharField(max_length=15, null=True, blank=True)

    government_id_document = models.FileField(
        upload_to=get_id_document_upload_path,
        null=True,
        blank=True
    )

    ministry = models.ForeignKey(Ministry, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


# --- Complaint Models ---

class Complaint(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('REJECTED', 'Rejected'),
    )

    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    )

    # Core Info
    title = models.CharField(max_length=255)
    description = models.TextField()
    tracking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # User & Admin Info
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    ministry = models.ForeignKey(Ministry, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)

    # Files
    attachment = models.FileField(upload_to='complaint_attachments/', null=True, blank=True)

    # AI Fields
    ai_suggested_category = models.CharField(max_length=255, blank=True, null=True)
    ai_suggested_priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.tracking_id})"


class ComplaintUpdate(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='updates')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    update_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Update on {self.complaint.tracking_id} by {self.user.username}"