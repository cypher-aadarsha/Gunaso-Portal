import os
from celery import shared_task
from .models import Complaint
from google.api_core.client_options import ClientOptions
from google.api_core.retry import Retry
from google.generativeai import GenerativeModel, configure

# Configure the Gemini API client
# It's best practice to set the API key from environment variables
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
        initial=1.0,  # Initial delay in seconds
        maximum=60.0,  # Maximum delay
        multiplier=2.0,  # Factor to increase delay
        deadline=300.0,  # Total time for all retries
        predicate=Retry.if_transient_error
    )
else:
    print("WARNING: GEMINI_API_KEY environment variable not set. AI tasks will fail.")
    default_retry = None


@shared_task(bind=True, default_retry_delay=60)  # Retry task on failure after 60s
def process_complaint_ai(self, complaint_id):
    """
    Asynchronous task to process a complaint with the Gemini AI.
    'complaint_id' is now the tracking_id (a UUID).
    """
    if not api_key or not default_retry:
        print(f"AI processing skipped for {complaint_id}: API key not configured.")
        return

    try:
        # --- THIS IS THE FIX ---
        # Look up the complaint by 'tracking_id' instead of 'id'
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
    1. "category": A concise category for the complaint (e..g., "Corruption / Bribe", "Service Delay", "Officer Misconduct", "Policy Issue", "Infrastructure Problem", "Public Safety", "Other").
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
        response = model.generate_content(
            user_prompt,
            request_options={'retry': default_retry}
        )

        # Extract and parse the JSON response
        ai_data = response.candidates[0].content.parts[0].text

        # The AI should return a JSON string, e.g.,
        # '{"category": "Service Delay", "priority": "MEDIUM"}'
        import json
        data = json.loads(ai_data)

        # Update the complaint model with AI data
        complaint.ai_category = data.get('category', 'Uncategorized')
        complaint.ai_priority = data.get('priority', 'MEDIUM').upper()
        complaint.save()

        print(f"Successfully processed complaint {complaint_id}. Priority: {complaint.ai_priority}")

    except Exception as e:
        # If the API call or processing fails, retry the task
        print(f"Error processing complaint {complaint_id}: {e}")
        # Raise an exception to trigger Celery's retry mechanism
        raise self.retry(exc=e)