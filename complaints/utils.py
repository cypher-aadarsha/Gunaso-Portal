import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms_notification(phone_number, message):
    """
    Sends an SMS notification to the given phone number.

    NOTE: Since no specific SMS gateway (like Twilio, Sparrow SMS, etc.)
    was provided, this function simulates the SMS sending by logging it
    to the console.
    """
    if not phone_number:
        return

    try:
        # --- SMS GATEWAY INTEGRATION WOULD GO HERE ---
        # Example (Pseudo-code):
        # response = requests.post("https://sms-gateway.com/send", data={
        #     "to": phone_number,
        #     "text": message,
        #     "api_key": settings.SMS_API_KEY
        # })

        # Simulating success for development
        print(f"\n[SMS SIMULATION] To: {phone_number} | Message: {message}\n")
        logger.info(f"SMS sent to {phone_number}: {message}")

    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")


def send_email_notification(subject, message, recipient_list):
    """
    Sends an email notification.
    """
    if not recipient_list:
        return

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        print(f"\n[EMAIL SENT] To: {recipient_list} | Subject: {subject}\n")
        logger.info(f"Email sent to {recipient_list}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_list}: {str(e)}")