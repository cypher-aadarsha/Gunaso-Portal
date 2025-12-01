from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Complaint
from .tasks import process_complaint_ai


@receiver(post_save, sender=Complaint)
def trigger_ai_processing(sender, instance, created, **kwargs):
    """
    This signal triggers when a new Complaint is CREATED.
    """
    if created:
        # This is a new complaint, send it to the Celery queue
        # for AI processing in the background.
        print(f"New complaint {instance.tracking_id} detected. Sending to AI task queue.")

        # --- THIS IS THE FIX ---
        # We must pass the 'tracking_id' (which is the primary key)
        # instead of 'id', which does not exist.
        process_complaint_ai.delay(instance.tracking_id)