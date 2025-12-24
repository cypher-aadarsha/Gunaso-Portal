from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Complaint, ComplaintUpdate
from .tasks import process_complaint_ai
from .utils import send_sms_notification, send_email_notification


@receiver(post_save, sender=Complaint)
def trigger_ai_processing(sender, instance, created, **kwargs):
    """
    Trigger AI when a complaint is first created.
    """
    if created:
        print(f"New complaint {instance.tracking_id} detected. Sending to AI task queue.")
        process_complaint_ai.delay(instance.tracking_id)


@receiver(pre_save, sender=Complaint)
def store_old_status(sender, instance, **kwargs):
    """
    Store the old status before saving to detect changes.
    """
    if instance.pk:
        try:
            old_instance = Complaint.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Complaint.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Complaint)
def notify_citizen_on_status_change(sender, instance, created, **kwargs):
    """
    Triggers Email/SMS when status changes.
    """
    # Check if this is an update (not creation) and if status has changed
    if not created and hasattr(instance, '_old_status') and instance._old_status != instance.status:

        citizen_user = instance.created_by
        citizen_profile = getattr(citizen_user, 'profile', None)

        # Try to get the latest admin remark, if any
        latest_update = instance.updates.order_by('-created_at').first()
        admin_remark = latest_update.update_text if latest_update else "Status updated by administration."

        # Prepare Message
        status_display = instance.get_status_display()

        email_subject = f"Update on your Grievance (ID: {str(instance.tracking_id)[:8]})"

        message_body = f"""
Dear {citizen_user.first_name},

The status of your grievance regarding "{instance.title}" has been updated.

New Status: {status_display}
Admin Remarks: {admin_remark}

You can login to the portal for more details.

Thank you,
Gunaso Portal Team
Government of Nepal
        """

        # 1. Send SMS (Placeholder)
        if citizen_profile and citizen_profile.phone_number:
            send_sms_notification(citizen_profile.phone_number,
                                  f"Gunaso Portal: Your grievance status is now {status_display}. Remark: {admin_remark}")

        # 2. Send Real Email
        if citizen_user.email:
            print(f"Sending email to {citizen_user.email}...")  # Debug log
            send_email_notification(email_subject, message_body, [citizen_user.email])


@receiver(post_save, sender=ComplaintUpdate)
def notify_citizen_on_new_remark(sender, instance, created, **kwargs):
    """
    Triggers Email/SMS when a new remark (ComplaintUpdate) is added,
    even if the status didn't change.
    """
    if created:
        complaint = instance.complaint
        citizen_user = complaint.created_by

        # If the update was made by the citizen themselves, don't notify them
        if instance.user == citizen_user:
            return

        citizen_profile = getattr(citizen_user, 'profile', None)

        email_subject = f"New Message on your Grievance (ID: {str(complaint.tracking_id)[:8]})"

        message_body = f"""
Dear {citizen_user.first_name},

A new remark has been added to your grievance "{complaint.title}".

Official Remark:
{instance.update_text}

Log in to the portal to view full history.

Thank you,
Gunaso Portal Team
Ministry of Education,Science and Technology
        """

        if citizen_user.email:
            send_email_notification(email_subject, message_body, [citizen_user.email])