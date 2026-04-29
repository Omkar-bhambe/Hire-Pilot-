import smtplib
from email.mime.text import MIMEText
from utils.gemini_client import GeminiClient

# ================= CONFIG =================
EMAIL = "11anurag04@gmail.com"
PASSWORD = "nycj vumj ppgi xhbc"

gemini = GeminiClient(api_key="YOUR_GEMINI_API_KEY")


# ================= EMAIL CONTENT =================
def generate_email_content(name, job_description, schedule_time, link):

    # ✅ BASE TEMPLATE (NEVER BREAK THIS)
    base_email = f"""
Hello {name},

We are pleased to invite you for an interview.

📌 Position: {job_description}

📅 Date & Time: {schedule_time}

🔗 Interview Link:
{link}

📢 Instructions:
- Join the interview on time
- Ensure a stable internet connection
- Keep your camera ON during the interview
- Avoid switching tabs

We look forward to your participation.

Best regards,  
HR Team
"""

    # ================= GEMINI POLISH =================
    try:
        prompt = f"""
You are a professional HR assistant.

Improve the email below:
- Keep SAME structure
- DO NOT remove any line
- DO NOT remove link
- DO NOT shorten
- Only improve wording and tone

Return ONLY improved email.

Email:
{base_email}
"""

        improved = gemini.generate(prompt)

        # ✅ SAFETY CHECK (VERY IMPORTANT)
        if (
            improved
            and len(improved) > 50
            and "http" in improved
            and name in improved
        ):
            return improved.strip()

        # fallback
        return base_email.strip()

    except Exception as e:
        print("Gemini Error:", e)
        return base_email.strip()


# ================= SEND EMAIL =================
def send_interview_email(to_email, name, job_description, link, schedule_time):

    subject = "Interview Invitation"

    body = generate_email_content(
        name,
        job_description,
        schedule_time,
        link
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)
        server.quit()

        print("✅ Email sent successfully to", to_email)
        return True

    except Exception as e:
        print("❌ Email Error:", e)
        return False