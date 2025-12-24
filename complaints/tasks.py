import os
from celery import shared_task
from .models import Complaint
from google.api_core.client_options import ClientOptions
from google.api_core.retry import Retry, if_transient_error  # <-- Import the function directly
from google.generativeai import GenerativeModel, configure
import google.api_core.exceptions

# Configure the Gemini API client
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    configure(
        api_key=api_key,
        client_options=ClientOptions(
            api_endpoint=os.environ.get("GEMINI_ENDPOINT", "generativelanguage.googleapis.com"),
        ),
        transport="rest"
    )
    # Configure default retry settings for API calls
    default_retry = Retry(
        initial=1.0,
        maximum=60.0,
        multiplier=2.0,
        deadline=300.0,
        predicate=if_transient_error  # <-- Use the imported function directly
    )
else:
    print("WARNING: GEMINI_API_KEY environment variable not set. AI tasks will fail.")
    default_retry = None


@shared_task(bind=True, default_retry_delay=60)
def process_complaint_ai(self, complaint_id):
    """
    Asynchronous task to process a complaint with the Gemini AI.
    'complaint_id' is now the tracking_id (a UUID).
    """
    if not api_key:
        print(f"AI processing skipped for {complaint_id}: API key not configured.")
        return

    try:
        complaint = Complaint.objects.get(tracking_id=complaint_id)
    except Complaint.DoesNotExist:
        print(f"Complaint {complaint_id} not found. Task aborting.")
        return

    # Define the system prompt for the AI
    system_prompt = """
    You are a grievance analysis bot for a national government portal.
    Analyze the following complaint text.
    Respond ONLY with a valid JSON object (no markdown, no other text).
    The JSON object must have exactly two keys:
    1. "category": A concise category for the complaint (e.g., "Corruption / Bribe", "Service Delay", "Officer Misconduct", "Policy Issue", "Infrastructure Problem", "Public Safety", "Other").
    2. "priority": Your suggested priority ("LOW", "MEDIUM", or "HIGH").
    """

    # Format the user's complaint text
    user_prompt = f"""
    Title: {complaint.title}
    Details: {complaint.description}
    """

    try:
        model = GenerativeModel(
            model_name="gemini-2.5-flash-preview-09-2025",
            system_instruction=system_prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        # Generate content with retry
        # Note: Some older versions of the SDK might not accept 'retry' in request_options
        # If this fails, we can remove request_options entirely.
        response = model.generate_content(
            user_prompt,
            request_options={'retry': default_retry} if default_retry else None
        )

        # Extract and parse the JSON response
        ai_data = response.candidates[0].content.parts[0].text

        import json
        data = json.loads(ai_data)

        # Update the complaint model with AI data
        complaint.ai_suggested_category = data.get('category', 'Uncategorized')
        complaint.ai_suggested_priority = data.get('priority', 'MEDIUM').upper()
        complaint.save()

        print(f"Successfully processed complaint {complaint_id}. Priority: {complaint.ai_suggested_priority}")

    except Exception as e:
        print(f"Error processing complaint {complaint_id}: {e}")
        # Retry the task if it's a transient error
        raise self.retry(exc=e)