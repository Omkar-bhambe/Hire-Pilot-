import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv
import logging

# from services.notification_service import SMTP_SERVER

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SMTP_SERVER = os.getenv("SMTP_SERVER")
# SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# connect the username and password
SMTP_ADMIN_USERNAME = os.getenv("SMTP_ADMIN_USERNAME")
SMTP_ADMIN_PASSWORD = os.getenv("SMTP_ADMIN_PASSWORD")

def _execute_send(msg):
    """The core helper function that connects to Gmail's SMTP server"""
    try:
        # Port 465 is for SSL
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SMTP_ADMIN_USERNAME, SMTP_ADMIN_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Email System Error: {e}")
        return False


def send_admin_approval_email(user_name, user_email, token):
    msg = EmailMessage()
    msg['Subject'] = f"🚀 Action Required: HirePilot Access Request ({user_name})"
    msg['From'] = SMTP_ADMIN_USERNAME
    msg['To'] = "bhambeomkar@gmail.com"  # Your primary email

    BASE_URL = os.getenv("BASE_URL", "https://edythe-tularaemic-uncourageously.ngrok-free.dev")
    # Change this to your deployed URL when you go live
    approve_url = f"{BASE_URL}/approve_admin/{token}"

    # --- HTML EMAIL TEMPLATE ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; padding: 40px; margin: 0;">
        <div style="max-width: 600px; margin: auto; background: white; border-radius: 24px; padding: 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">
            <h1 style="color: #0f172a; font-size: 24px; font-weight: 800; margin-bottom: 8px;">HirePilot<span style="color: #4f46e5;">.</span></h1>
            <p style="color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 32px;">Access Request Gateway</p>

            <p style="color: #334155; font-size: 16px; line-height: 1.6;">Hi Omkar,</p>
            <p style="color: #334155; font-size: 16px; line-height: 1.6;">A new staff member has requested access to the <strong>Batch 2026</strong> Recruitment Dashboard.</p>

            <div style="background: #f1f5f9; border-radius: 16px; padding: 20px; margin: 24px 0;">
                <p style="margin: 0; font-size: 14px; color: #64748b;"><strong>User:</strong> {user_name}</p>
                <p style="margin: 4px 0 0 0; font-size: 14px; color: #64748b;"><strong>Email:</strong> {user_email}</p>
            </div>

            <p style="color: #334155; font-size: 16px; line-height: 1.6; margin-bottom: 32px;">If you recognize this person, click the button below to approve their credentials and move them to the Cloud database.</p>

            <div style="text-align: center;">
                <a href="{approve_url}" style="display: inline-block; background-color: #0f172a; color: #ffffff; padding: 18px 36px; border-radius: 14px; text-decoration: none; font-weight: 800; font-size: 14px; box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.2);">
                    Approve & Grant Access 🚀
                </a>
            </div>

            <p style="color: #94a3b8; font-size: 12px; text-align: center; margin-top: 40px;">
                If you did not expect this request, simply delete this email. No access will be granted without your click.
            </p>
        </div>
    </body>
    </html>
    """

    msg.add_alternative(html_content, subtype='html')

    # Standard Gmail SMTP Setup
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            # Use environment variables or App Password for security
            smtp.login(SMTP_ADMIN_USERNAME, SMTP_ADMIN_PASSWORD)
            smtp.send_message(msg)
            return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False


def send_reset_password_email(user_email, token):
    msg = EmailMessage()
    msg['Subject'] = "🔐 HirePilot Password Reset Request"
    msg['From'] = SMTP_ADMIN_USERNAME
    msg['To'] = user_email

    BASE_URL = os.getenv("BASE_URL", "https://edythe-tularaemic-uncourageously.ngrok-free.dev")
    # Use your specific port (5001) or ngrok tunnel
    reset_url = f"{BASE_URL}/reset_password/{token}"

    msg.set_content(f"""
    Hello,

    We received a request to reset your password for the HirePilot Dashboard.

    Click the link below to set a new password:
    {reset_url}

    If you did not request this, please ignore this email.
    """)

    return _execute_send(msg)

