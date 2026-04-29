import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import logging
# from main import handle_document_bulk
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Email configuration from .env
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
# CORRECTED: Use the variable NAMES
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


# def send_email_notification(to_email: str, session_id, c_id, candidate_name: str, job_title: str = "Technical Role"):
#     """
#     Sends a professionally justified HTML shortlist notification.
#     """
#     if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD]):
#         logger.error("Email configuration incomplete. Check .env variables.")
#         return
#     BASE_URL=os.getenv("BASE_URL", "https://edythe-tularaemic-uncourageously.ngrok-free.dev")
#     subject = f"Shortlisted: Your Application for {job_title} - HirePilot"
#
#     test_link = f"{BASE_URL}/take-test/{session_id}/{c_id}"
#     # Fully Justified HTML Body
#     html_body = f"""
#     <html>
#         <body style="font-family: 'Inter', Arial, sans-serif; line-height: 1.8; color: #1e293b; max-width: 600px; margin: auto; padding: 20px; background-color: #f8fafc;">
#             <div style="background-color: #ffffff; padding: 45px; border: 1px solid #e2e8f0; border-radius: 32px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);">
#                 <h3 style="color: #4f46e5; font-size: 26px; font-weight: 800; margin-bottom: 24px; letter-spacing: -0.5px;">Congratulations, {candidate_name}!</h3>
#
#                 <p style="text-align: justify; margin-bottom: 20px;">
#                     We are pleased to inform you that your profile has been <strong>Shortlisted</strong> for the
#                     {job_title} position. After a detailed AI-driven screening of your resume, our team at
#                     <strong>ICEM</strong> has identified you as a high-match candidate.
#                 </p>
#
#                 <div style="background-color: #f1f5f9; padding: 25px; border-radius: 20px; margin: 30px 0;">
#                     <strong style="display: block; color: #0f172a; font-size: 16px; margin-bottom: 15px;">Assessment Details:</strong>
#                     <table style="width: 100%; font-size: 14px; color: #475569;">
#                         <tr><td><strong>Duration:</strong></td><td>60 Minutes</td></tr>
#                         <tr><td><strong>Format:</strong></td><td>90 MCQs (3 Sections)</td></tr>
#                         <tr><td><strong>Sections:</strong></td><td>Aptitude, Technical, Coding</td></tr>
#                         <tr><td><strong>Warnings:</strong></td><td>3 Tab-Switch Limit</td></tr>
#                     </table>
#                 </div>
#
#                 <div style="text-align: center; margin: 40px 0;">
#                     <a href="{test_link}" style="background-color: #4f46e5; color: #ffffff; padding: 18px 35px; border-radius: 14px; text-decoration: none; font-weight: 800; font-size: 16px; display: inline-block; box-shadow: 0 4px 6px rgba(79, 70, 229, 0.3);">
#                         Start Technical Assessment
#                     </a>
#                     <p style="font-size: 11px; color: #94a3b8; margin-top: 15px;">Note: Camera access is mandatory for proctoring.</p>
#                 </div>
#
#                 <p style="text-align: justify; font-size: 13px; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 25px;">
#                     If the button above does not work, copy and paste this link: <br>
#                     <span style="color: #4f46e5; word-break: break-all;">{test_link}</span>
#                 </p>
#
#                 <div style="margin-top: 40px; padding-top: 25px;">
#                     <p style="margin: 0; color: #4f46e5; font-weight: 800; font-size: 18px;">Omkar Bhambe</p>
#                     <p style="margin: 0; font-weight: 700; color: #64748b; font-size: 11px; text-transform: uppercase;">Placement Coordinator | HirePilot</p>
#                 </div>
#             </div>
#         </body>
#     </html>
#     """
#
#     msg = EmailMessage()
#     msg['Subject'] = subject
#     msg['From'] = f"HirePilot Careers <{SMTP_USERNAME}>"
#     msg['To'] = to_email
#
#     # Set the HTML alternative
#     msg.add_alternative(html_body, subtype='html')
#
#     try:
#         with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
#             server.starttls()
#             server.login(SMTP_USERNAME, SMTP_PASSWORD)
#             server.send_message(msg)
#             logger.info(f"Shortlist HTML notification sent to {to_email}")
#     except Exception as e:
#         logger.error(f"Failed to send shortlist email: {e}")

def send_shortlist_notification(to_email, candidate_name, job_title):
    """PHASE 1: Sent immediately after screening. No link included."""
    msg = EmailMessage()
    msg['Subject'] = f"Update on your application: {job_title}"
    msg['From'] = f"HirePilot Talent Team <{SMTP_USERNAME}>"
    msg['To'] = to_email

    html_content = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; max-width: 600px; margin: auto; border: 1px solid #f1f5f9; border-radius: 24px; padding: 40px; background-color: #ffffff;">
        <h2 style="color: #4f46e5; margin-bottom: 20px;">Great news, {candidate_name}!</h2>
        <p style="font-size: 16px; line-height: 1.6;">Our AI screening agent has reviewed your profile for the <strong>{job_title}</strong> role at ICEM, and we are impressed with your background.</p>
        <p style="font-size: 16px; line-height: 1.6;"><strong>What's next?</strong></p>
        <p style="font-size: 14px; color: #64748b;">Our HR team is currently setting up the technical assessment environment. You will receive a separate email containing your unique <strong>secure test link</strong> within the next few hours.</p>
        <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 30px 0;">
        <p style="font-size: 12px; color: #94a3b8; text-align: center;">This is an automated notification from HirePilot.ai</p>
    </div>
    """
    msg.add_alternative(html_content, subtype='html')
    return _dispatch_mail(msg)


def send_test_invite_notification(to_email, candidate_name, session_id, c_id, job_title):
    """PHASE 2: Sent when HR clicks 'Send Invites'. Includes the proctored link."""
    msg = EmailMessage()
    msg['Subject'] = f"ACTION REQUIRED: Assessment Link for {job_title}"
    msg['From'] = f"HirePilot Assessment <{SMTP_USERNAME}>"
    msg['To'] = to_email

    BASE_URL = os.getenv("BASE_URL", "https://edythe-tularaemic-uncourageously.ngrok-free.dev")
    test_link = f"{BASE_URL}/take-test/{session_id}/{c_id}"

    html_content = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; max-width: 600px; margin: auto; border: 1px solid #eef2ff; border-radius: 24px; padding: 40px; background-color: #ffffff; border-top: 8px solid #4f46e5;">
        <h2 style="color: #1e293b;">Your Assessment is Ready</h2>
        <p style="font-size: 16px; line-height: 1.6;">Hello {candidate_name}, the environment for your <strong>{job_title}</strong> technical test is now live.</p>

        <div style="background-color: #f8fafc; padding: 20px; border-radius: 16px; margin: 25px 0;">
            <p style="margin: 0; font-size: 13px; color: #475569;"><strong>Proctoring Rules:</strong></p>
            <ul style="font-size: 13px; color: #64748b; padding-left: 20px;">
                <li>Full-screen mode is mandatory.</li>
                <li>3 Tab-switches will result in auto-submission.</li>
                <li>Camera monitoring must remain active.</li>
            </ul>
        </div>

        <div style="text-align: center; margin-top: 35px;">
            <a href="{test_link}" style="background-color: #4f46e5; color: white; padding: 18px 32px; text-decoration: none; border-radius: 12px; font-weight: 800; font-size: 14px; display: inline-block; box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.3);">START ASSESSMENT NOW</a>
        </div>
        <p style="text-align: center; font-size: 12px; color: #94a3b8; margin-top: 20px;">Link expires once the drive concludes.</p>
    </div>
    """
    msg.add_alternative(html_content, subtype='html')
    return _dispatch_mail(msg)

def send_virtual_interview_link(to_email, candidate_name, interview_id):
    """PHASE 4: Sent to auto-provision virtual interviews."""
    msg = EmailMessage()
    msg['Subject'] = "🎤 Next Steps: Scheduled for HirePilot Virtual Interview"
    msg['From'] = f"HirePilot Video Assessment <{SMTP_USERNAME}>"
    msg['To'] = to_email

    BASE_URL = os.getenv("BASE_URL", "https://edythe-tularaemic-uncourageously.ngrok-free.dev")
    interview_url = f"{BASE_URL}/virtual-interview/{interview_id}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; padding: 40px; margin: 0;">
        <div style="max-width: 600px; margin: auto; background: white; border-radius: 24px; padding: 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">
            <h1 style="color: #0f172a; font-size: 24px; font-weight: 800; margin-bottom: 8px;">HirePilot<span style="color: #4f46e5;">.</span></h1>
            <p style="color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 32px;">Virtual AI Interview</p>

            <p style="color: #334155; font-size: 16px; line-height: 1.6;">Hi {candidate_name},</p>
            <p style="color: #334155; font-size: 16px; line-height: 1.6;">Congratulations on passing the initial screening test! You have been shortlisted for our autonomous Virtual AI Interview.</p>

            <p style="color: #334155; font-size: 16px; line-height: 1.6; margin-bottom: 32px;">Please click the button below to start your face-to-face AI interview. Ensure you are in a quiet environment and have access to a working microphone and camera.</p>

            <div style="text-align: center;">
                <a href="{interview_url}" style="display: inline-block; background-color: #0f172a; color: #ffffff; padding: 18px 36px; border-radius: 14px; text-decoration: none; font-weight: 800; font-size: 14px; box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.2);">
                    Start Virtual Interview 🎤
                </a>
            </div>

            <p style="color: #94a3b8; font-size: 12px; text-align: center; margin-top: 40px;">
                Good luck!<br>The HirePilot Team
            </p>
        </div>
    </body>
    </html>
    """

    msg.add_alternative(html_content, subtype='html')
    return _dispatch_mail(msg)

import smtplib


def _dispatch_mail(msg):
    """
    Robust dispatcher that handles protocol differences between
    Port 465 (Implicit SSL) and Port 587 (Explicit STARTTLS).
    """
    try:
        # Check if we are using the direct SSL port (465)
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
                return True
        else:
            # For Port 587 or others, use STARTTLS
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()  # This is the magic line that fixes the version error
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
                return True

    except Exception as e:
        # This will now give you a clearer error if something else is wrong
        print(f"❌ Mail Dispatch Error: {e}")
        return False