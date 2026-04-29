import sys
import os

# Add to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.notification_service import send_test_invite_notification
from dotenv import load_dotenv

load_dotenv()

print("Sending test email...")
res = send_test_invite_notification(
    to_email="test@example.com",
    candidate_name="Test User",
    session_id="test_session_123",
    c_id="c_123",
    job_title="Software Engineer"
)
print("Result:", res)
