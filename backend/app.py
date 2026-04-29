import os
import json
import uuid
import zipfile
import io
import time
import unicodedata
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from fpdf import FPDF
import datetime
from services.database_service import db
from services.email_service import send_admin_approval_email
# from werkzeug.security import generate_password_hash

from services.database_service import save_test_results,get_session_data, create_recruitment_session, save_screening_result

from services.gemini_client import get_gemini_response
from services.resume_parser import extract_text_from_file
from services.notification_service import send_shortlist_notification, send_test_invite_notification
from services.agent_service import OnlineTestAgent

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

app = Flask(__name__)
from flask_cors import CORS
CORS(app)

from backend.routes.interview_routes import interview_bp
app.register_blueprint(interview_bp, url_prefix="/api/interview")
from backend.routes.voice_routes import voice_bp
app.register_blueprint(voice_bp, url_prefix="/api/voice")

@app.route("/virtual-interview/<interview_id>")
def virtual_interview_page(interview_id):
    return render_template("backend_interview.html", interview_id=interview_id)

@app.route("/virtual-interview/finish")
def virtual_interview_finish():
    return render_template("backend_finish.html")

# --- STORAGE SETUP ---
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "storage" / "resumes"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

# Store results in memory for the session to enable ZIP download
session_results = {}


# ----------------- PDF GENERATOR (STRICT ASCII VERSION) -----------------

class RecruitmentReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'HirePilot - AI Recruitment Analysis', 0, 1, 'L')
        self.set_draw_color(79, 70, 229)
        self.line(10, 22, 200, 22)
        self.ln(10)


def strict_clean(text):
    """Forcefully removes any character that would crash the PDF engine."""
    if not text: return "N/A"
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '*', '\u00a0': ' '
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return unicodedata.normalize('NFKD', text).encode('latin-1', 'ignore').decode('latin-1')


def create_pdf_report(data):
    pdf = RecruitmentReport()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Candidate: {strict_clean(data.get('name'))}", 0, 1)
    pdf.set_text_color(37, 99, 235)
    pdf.set_font("Arial", 'B', 24)
    pdf.cell(0, 15, f"Match Score: {data.get('match_score', 0)}%", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 10, "AI Justification:", 0, 1)
    pdf.set_font("Arial", '', 11);
    pdf.multi_cell(0, 7, strict_clean(data.get('justification')))
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Status: {strict_clean(data.get('status'))}", 0, 1)
    return pdf.output()


# ----------------- ROUTES -----------------

@app.route('/')
def home_page():
    # You can see the home page through
    return render_template('home.html')


# @app.route('/login')
# def admin_login():
#     # You can login through this page
#     return render_template('login.html')


@app.route('/admin')
def admin_dashboard():
    """
        Dashboard Home: Now pulls the last active session
        so 'Total Screened' and 'Shortlisted' stats actually work.
        """
    # 1. Get the session HR is currently working on
    session_id = session.get('last_session_id', "no_active_session")

    # 2. Fetch real stats for the Dashboard
    stats = {"total": "--", "shortlisted": "--"}
    if session_id != "no_active_session":
        cand_ref = db.collection('recruitment_sessions').document(session_id).collection('candidates')
        stats['total'] = cand_ref.count().get()[0][0].value
        stats['shortlisted'] = \
        cand_ref.where("status", "in", ["Shortlisted", "Shortlisted & Notified"]).count().get()[0][0].value

    return render_template('admin.html', session_id=session_id, stats=stats)


@app.route('/index')
def home(): return render_template('index.html')


@app.route('/init/prompt')
def init_prompt(): return render_template('init_prompt.html')

from services.database_service import create_recruitment_session, save_extracted_resume_to_cloud, update_candidate_results


@app.route('/api/process-bulk', methods=['POST'])
def handle_bulk_processing():
    """
    Migrated Batch Processor: Stores data in Cloud Sessions instead of memory.
    """
    # 1. Initialize Cloud Session Identity
    session_name = request.form.get('session_name', 'Unnamed_Drive')
    jd_text = request.form.get('job_description')
    threshold = int(request.form.get('threshold', 75))
    hr_email = session.get('admin_email', 'system@hirepilot.ai')

    # Create the recruitment session and capture the ID
    session_id = request.form.get('session_id')
    jd_text = request.form.get('job_description')

    if not session_id or session_id == 'None':
        session_id = create_recruitment_session(
            session_name=session_name,
            hr_email=hr_email,
            jd_text=jd_text
        )

    session['last_session_id'] = session_id

    # 2. Extraction Logic
    files = request.files.getlist('resumes')
    cloud_candidates = []

    for file in files:
        if file.filename.endswith('.zip'):
            zip_path = app.config['UPLOAD_FOLDER'] / f"{uuid.uuid4()}.zip"
            file.save(zip_path)
            with zipfile.ZipFile(zip_path, 'r') as z:
                ext_dir = app.config['UPLOAD_FOLDER'] / str(uuid.uuid4())
                z.extractall(ext_dir)
                for r, _, fs in os.walk(ext_dir):
                    for f in fs:
                        if f.lower().endswith(('.pdf', '.docx')):
                            file_path = Path(r) / f
                            text = extract_text_from_file(file_path)
                            c_id = save_extracted_resume_to_cloud(session_id, f, text)
                            cloud_candidates.append({"name": f, "text": text, "cloud_id": c_id})
        else:
            path = app.config['UPLOAD_FOLDER'] / f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            file.save(path)
            text = extract_text_from_file(path)
            c_id = save_extracted_resume_to_cloud(session_id, file.filename, text)
            cloud_candidates.append({"name": file.filename, "text": text, "cloud_id": c_id})

    # 3. Agentic Batch Processing
    final_results = []
    chunk_size = 10
    for i in range(0, len(cloud_candidates), chunk_size):
        chunk = cloud_candidates[i:i + chunk_size]

        batch_prompt = f"""
        You are an expert AI Recruitment Agent. Analyze these {len(chunk)} resumes against this JD: {jd_text}
        Return a JSON list of objects: [{{"name": "...", "email": "...", "match_score": 85, "justification": "..."}}]
        Resumes:
        """
        for idx, item in enumerate(chunk):
            batch_prompt += f"\n--- Candidate {idx} ---\n{item['text']}\n"

        try:
            response = get_gemini_response(batch_prompt, is_json=True)
            clean_json = response.strip().replace("```json", "").replace("```", "").strip()
            batch_data = json.loads(clean_json)

            for idx, data in enumerate(batch_data):
                c_id = chunk[idx]['cloud_id']
                raw_score = data.get('match_score', 0)
                try:
                    match_score = int(raw_score)
                except (ValueError, TypeError):
                    match_score = 85 if "high" in str(raw_score).lower() else 50

                status = "Not Shortlisted"
                if match_score >= threshold:
                    # ✅ FIXED: Added 'job_title=session_name' to satisfy the function requirements
                    send_shortlist_notification(
                        to_email=data.get('email'),
                        candidate_name=data.get('name'),
                        job_title=session_name
                    )
                    status = "Shortlisted"

                # 4. Save Results to Cloud
                report_payload = {
                    "name": data.get('name'),
                    "email": data.get('email'),
                    "match_score": match_score,
                    "justification": data.get('justification'),
                    "status": status
                }
                update_candidate_results(session_id, c_id, report_payload)
                final_results.append(report_payload)

            time.sleep(2)
        except Exception as batch_err:
            print(f"Batch Error at session {session_id}: {batch_err}")
            continue

    return jsonify({
        "status": "success",
        "batch_id": session_id,
        "candidates": final_results,
        "message": "Screening complete. Proceed to assessment setup."
    })

@app.route('/api/download-all-zip/<session_id>')
def download_all(session_id):
    """Retrieves results and resumes from Cloud Storage to build the ZIP."""
    # 1. Fetch data from Cloud instead of session_results dict
    candidates_ref = db.collection('recruitment_sessions').document(session_id) \
        .collection('candidates').where("processed", "==", True)
    docs = candidates_ref.stream()

    memory_file = io.BytesIO()
    try:
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for doc in docs:
                c = doc.to_dict()
                # 2. Reconstruct the PDF from Cloud Data
                pdf_bytes = create_pdf_report(c)
                safe_name = "".join([x for x in c.get('name', 'Candidate') if x.isalnum() or x == ' '])

                # Add PDF to ZIP
                zf.writestr(f"Reports/{safe_name}_Analysis.pdf", pdf_bytes)

        memory_file.seek(0)
        return send_file(memory_file, download_name=f"HirePilot_{session_id}.zip", as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Cloud Retrieval Failed: {str(e)}"}), 500

# ------ DOCUMENTED JOB DESCRIPTION -------


@app.route('/init/document')
def init_document(): return render_template('init_document.html')


@app.route('/api/process-document-bulk', methods=['POST'])
def handle_document_bulk():
    """
    Migrated Document Path: Processes JD Files + Bulk Resumes via Cloud Storage.
    """
    # 1. Capture Inputs
    session_name = request.form.get('session_name', 'Document_Drive')
    jd_file = request.files.get('jd_file')
    threshold = int(request.form.get('threshold', 75))
    resume_files = request.files.getlist('resumes')
    hr_email = session.get('admin_email', 'system@hirepilot.ai')

    if not jd_file or not resume_files:
        return jsonify({"detail": "JD document and resumes are required"}), 400

    # 2. Extract JD Text from File
    jd_path = app.config['UPLOAD_FOLDER'] / f"JD_{uuid.uuid4()}_{secure_filename(jd_file.filename)}"
    jd_file.save(jd_path)
    jd_text = extract_text_from_file(jd_path)[:2000]

    # 3. ✅ CLOUD SYNC: Initialize Session with Documented JD
    session_id = create_recruitment_session(session_name, hr_email, jd_text=jd_text)

    # 4. Resume Extraction & Cloud Storage (Unpacking ZIPs/Files)
    cloud_candidates = []
    for file in resume_files:
        if file.filename.endswith('.zip'):
            zip_path = app.config['UPLOAD_FOLDER'] / f"{uuid.uuid4()}.zip"
            file.save(zip_path)
            with zipfile.ZipFile(zip_path, 'r') as z:
                ext_dir = app.config['UPLOAD_FOLDER'] / str(uuid.uuid4())
                z.extractall(ext_dir)
                for r, _, fs in os.walk(ext_dir):
                    for f in fs:
                        if f.lower().endswith(('.pdf', '.docx')):
                            file_path = Path(r) / f
                            text = extract_text_from_file(file_path)[:3000]
                            # ✅ CLOUD SYNC: Store individual resume from ZIP
                            c_id = save_extracted_resume_to_cloud(session_id, f, text)
                            cloud_candidates.append({"name": f, "text": text, "cloud_id": c_id})
        else:
            path = app.config['UPLOAD_FOLDER'] / f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            file.save(path)
            text = extract_text_from_file(path)[:3000]
            # ✅ CLOUD SYNC: Store individual file
            c_id = save_extracted_resume_to_cloud(session_id, file.filename, text)
            cloud_candidates.append({"name": file.filename, "text": text, "cloud_id": c_id})

    # 5. Agentic Batch Processing (Standard Gemini Logic)
    final_results = []
    for i in range(0, len(cloud_candidates), 10):
        chunk = cloud_candidates[i:i + 10]

        batch_prompt = f"""
        Analyze these {len(chunk)} resumes against this extracted Job Description: {jd_text}
        Return a JSON list of objects: [{{"name": "...", "email": "...", "match_score": 85, "justification": "..."}}]
        Resumes:
        """
        for idx, item in enumerate(chunk):
            batch_prompt += f"\n[ID:{idx}] Filename:{item['name']}\nText: {item['text']}\n"

        try:
            response = get_gemini_response(batch_prompt, is_json=True)
            clean_json = response.strip().replace("```json", "").replace("```", "").strip()
            batch_data = json.loads(clean_json)

            for idx, data in enumerate(batch_data):
                # Map back to cloud document
                c_id = chunk[idx]['cloud_id']

                # Defensive Score Conversion
                raw_score = data.get('match_score', 0)
                try:
                    match_score = int(raw_score)
                except (ValueError, TypeError):
                    match_score = 85 if "high" in str(raw_score).lower() else 50

                status = "Not Shortlisted"
                if match_score >= threshold:
                    status = "Shortlisted"
                    if data.get('email'):
                        try:
                            send_shortlist_notification(data['email'], data['name'])
                            status = "Shortlisted & Notified"
                        except:
                            status = "Shortlisted (Mail Fail)"

                # 6. ✅ CLOUD SYNC: Update candidate with AI screening results
                report_payload = {
                    "name": data.get('name'),
                    "email": data.get('email'),
                    "match_score": match_score,
                    "justification": data.get('justification'),
                    "status": status
                }
                update_candidate_results(session_id, c_id, report_payload)
                final_results.append(report_payload)

            time.sleep(6)  # RPM Protection for Free Tier
        except Exception as e:
            print(f"Batch Error at offset {i}: {e}")
            continue

    return jsonify({"status": "success", "batch_id": session_id, "candidates": final_results})

# flask imports moved to top
from services.auth_service import request_registration, verify_login
from werkzeug.security import generate_password_hash

app.secret_key = "1245769nfrjknsefhkfgidk4568neoifj"


@app.route('/register')
def register_ui():
    # This must match the actual filename in your /templates folder
    return render_template('register.html')

# handling access control

from google.cloud import firestore

@app.route('/request_access', methods=['POST'])
def handle_request_access():
    """
    Captures user details and stores them in the 'pending_registrations' collection.
    Then notifies the Super-Admin (Omkar) for approval.
    """
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')

    if not name or not email or not password:
        flash("All fields are required.", "error")
        return redirect(url_for('register_ui'))

    try:
        # 1. Save to Pending Collection in Firestore
        token = request_registration(email, password, name)

        # 2. Notify Super-Admin (Omkar Bhambe)
        # The email will contain the approval link: /approve_admin/<token>
        admin_email = "bhambeomkar@gmail.com" # Your verified email
        send_admin_approval_email(name,
            email,
            token)

        flash("Request sent successfully! Access is pending Super-Admin approval.", "success")
        return redirect(url_for('admin_login'))

    except Exception as e:
        print(f"Registration Error: {e}")
        flash("An error occurred. Please try again later.", "error")
        return redirect(url_for('register_ui'))


@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    # 1. Handle the Submission (POST)
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Verify against your Cloud Firestore admins collection
        success, admin_data = verify_login(email, password)

        if success:
            session['admin_email'] = email
            session['admin_name'] = admin_data.get('full_name')
            flash(f"Welcome back, {admin_data.get('full_name')}!", "success")
            return redirect(url_for('admin_dashboard'))  # Go to main dashboard
        else:
            flash("Access Denied: Invalid credentials or pending approval.", "error")
            return redirect(url_for('admin_login'))

    # 2. Handle the Page Load (GET)
    return render_template('login.html')

@app.route('/approve_admin/<token>')
def approve_admin(token):
    try:
        # Logic provided earlier: Moves from pending -> admins with hashing
        pending_ref = db.collection('pending_registrations').document(token)
        doc = pending_ref.get()

        if not doc.exists:
            return "<h1>Link Expired</h1><p>This approval link is invalid or has already been used.</p>", 404

        data = doc.to_dict()
        user_email = data['email']

        admin_ref = db.collection('admins').document(user_email)
        admin_ref.set({
            "full_name": data['name'],
            "password_hash": generate_password_hash(data['password']),
            "role": "HR_Admin",
            "organization": "Indira College of Engineering and Management",
            "approved_at": firestore.SERVER_TIMESTAMP,
            "last_login": None
        })

        pending_ref.delete()

        return render_template('approval_success.html', user=data['name'])

    except Exception as e:
        print(f"Approval Error: {e}")
        return f"<h1>System Error</h1><p>{str(e)}</p>", 500

# Reset Password
from services.email_service import send_reset_password_email

@app.route('/test_reset')
def reset_password_form():
    return render_template('reset_password_form.html')


from flask import flash, redirect, url_for, render_template


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        # 1. Check if user exists in Firestore
        admin_ref = db.collection('admins').document(email).get()

        if admin_ref.exists:
            # 2. Generate Token & Send Email (Logic we built earlier)
            token = str(uuid.uuid4())
            db.collection('password_resets').document(token).set({
                "email": email, "created_at": firestore.SERVER_TIMESTAMP
            })
            send_reset_password_email(email, token)

            # 3. This is the "Message" part
            flash("Check your email! A reset link has been sent.")
        else:
            flash("Email not found in our system.")

        return redirect(url_for('admin_login'))  # Go back to login to see the flash message

    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # 1. Verify if the token is valid in Firestore

    reset_ref = db.collection('password_resets').document(token)
    reset_doc = reset_ref.get()

    if not reset_doc.exists:
        return "Invalid or expired reset link.", 404

    if request.method == 'POST':
        new_password = request.form.get('password')
        email = reset_doc.to_dict()['email']

        # 2. Update the password in the 'admins' collection
        db.collection('admins').document(email).update({
            "password_hash": generate_password_hash(new_password)
        })

        # 3. Delete the token so it can't be used again
        reset_ref.delete()

        return "Password updated successfully! You can now login."

    return render_template('reset_password_form.html')

# Test Agent


ai_agent = OnlineTestAgent('AIzaSyCdvHcqScAzrXgl2ycqytHJLMi_NQJHLmI')

@app.route('/admin/setup/<session_id>')
def setup_page(session_id):
    # Bridge: Automatically pull JD from the existing recruitment session
    data = get_session_data(session_id)
    return render_template('setup.html', session_id=session_id, jd=data['jd_text'])


@app.route('/api/generate-test', methods=['POST'])
def generate_test():
    """
    Captures HR inputs and saves them to the Cloud Session.
    """
    try:
        content = request.json
        session_id = content.get('session_id')

        # 1. Capture the exact variable being sent from your JS (t_limit)
        # We default to 60 if HR leaves it blank
        q_count = int(content.get('q_count', 90))
        time_limit = int(content.get('t_limit', 60))
        min_score = int(content.get('min_score', 70))

        # 2. Generate questions via your AI Agent
        questions = ai_agent.generate_full_test(content.get('jd_text', ''), q_count)

        # 3. SAVE TO FIRESTORE (Crucial Step)
        # We save it as 'time_limit' for consistency in the DB
        db.collection('recruitment_sessions').document(session_id).update({
            "active_test": questions,
            "question_count": q_count,
            "time_limit": time_limit,  # <--- THIS was missing
            "min_score": min_score,
            "status": "Testing Phase"
        })

        return jsonify({"status": "success", "message": "Assessment Configured"})
    except Exception as e:
        print(f"❌ Generation Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/take-test/<session_id>/<c_id>')
def exam_page(session_id, c_id):
    """
    Final Integrated Secure Exam Entry:
    1. Normalizes section keywords (Aptitude/Technical/Coding) for the UI.
    2. Fetches the dynamic HR-set timer from the active session.
    """
    # 1. Fetch the Session data
    session_ref = db.collection('recruitment_sessions').document(session_id)
    session_snap = session_ref.get()

    if not session_snap.exists:
        return "Session Error: The recruitment drive was not found.", 404

    session_data = session_snap.to_dict()
    questions = session_data.get('active_test', [])

    # 2. Fetch specific candidate details for identity verification
    cand_doc = session_ref.collection('candidates').document(c_id).get()
    if not cand_doc.exists:
        return "Unauthorized: You are not registered for this assessment.", 401

    # 3. NORMALIZATION: Ensures Aptitude/Coding sections work in the UI
    # This maps whatever keyword the AI Agent used back to a consistent 'category'
    for q in questions:
        q['category'] = q.get('category') or q.get('section') or q.get('type') or 'Technical'

    # 4. Fetch the dynamic Time Limit (default to 60 if missing in DB)
    hr_time_limit = session_data.get('time_limit', 60)

    # 5. Pass everything to the 'Iron Dome' template
    return render_template('exam.html',
                           questions=questions,
                           session_id=session_id,
                           c_id=c_id,
                           candidate=cand_doc.to_dict(),
                           role=session_data.get('session_name'),
                           time_limit=hr_time_limit) # <--- HR defined minutes


@app.route('/api/submit-test', methods=['POST'])
def submit_test():
    try:
        data = request.json
        s_id = data.get('session_id')
        c_id = data.get('c_id')
        user_answers = data.get('answers', {})
        violations = data.get('violations', 0)

        session_ref = db.collection('recruitment_sessions').document(s_id)
        session_doc = session_ref.get().to_dict()

        # 1. Run Evaluation Agent
        active_test = session_doc.get('active_test', [])
        score = ai_agent.calculate_score(user_answers, active_test)

        # 2. Status Logic
        min_threshold = int(session_doc.get('min_score', 70))

        if violations >= 3:
            status = "Disqualified (Proctoring)"
        elif score >= min_threshold:
            # Auto-schedule Virtual Interview
            from backend.services.interview_service import schedule_interview_service
            cand_doc = session_ref.collection('candidates').document(c_id).get().to_dict()
            
            interview_data = {
                "name": cand_doc.get("name", "Candidate"),
                "email": cand_doc.get("email", "unknown@example.com"),
                "job_description": session_doc.get("jd_text", "Job Role"),
                "resume": cand_doc.get("raw_resume_text", ""),
                "schedule_time": None
            }
            interview_id = schedule_interview_service(interview_data)
            status = "Virtual Interview Scheduled"
            
            # Save the linked virtual interview id
            session_ref.collection('candidates').document(c_id).update({
                "virtual_interview_id": interview_id
            })
        else:
            status = "Rejected (Low Score)"

        # 3. SAVE TO CLOUD (Crucial Fix)
        session_ref.collection('candidates').document(c_id).update({
            "test_score": score,
            "submitted_answers": user_answers,  # <--- THIS MUST BE SAVED
            "status": status,
            "proctoring_violations": violations,
            "test_status": "Completed",
            "submitted_at": firestore.SERVER_TIMESTAMP
        })

        return jsonify({"status": "success", "score": score})
    except Exception as e:
        print(f"❌ Critical Submission Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/test-manager/<session_id>')
def admin_test_manager(session_id):
    """
    Universal Assessment Manager: Loads data for WHATEVER session is selected.
    """
    # 1. Fetch the specific session data (JD, Role, Year) from Firestore
    session_data = get_session_data(session_id)
    if not session_data:
        return "Error: Session Not Found", 404

    # 2. FILTER: Fetch ONLY candidates belonging to THIS session_id
    # AND who have a 'Shortlisted' status.
    candidates = []
    shortlist_variants = ["Shortlisted", "Shortlisted & Notified", "Test Link Sent"]

    docs = db.collection('recruitment_sessions').document(session_id) \
        .collection('candidates') \
        .where("status", "in", shortlist_variants) \
        .stream()

    for doc in docs:
        cand = doc.to_dict()
        cand['id'] = doc.id
        candidates.append(cand)

    # 3. Pass EVERYTHING to the template
    return render_template('setup.html',
                           session_id=session_id,
                           role=session_data.get('session_name', 'Technical Drive'),
                           year=session_data.get('year', 'N/A'),
                           jd=session_data.get('jd_text', 'No JD provided'),
                           candidates=candidates)

from google.cloud.firestore_v1.base_query import FieldFilter


@app.route('/api/send-bulk-invites', methods=['POST'])
def api_send_bulk_invites():
    """
    Final Phase: Sends proctored test links.
    Updated to handle varied 'Shortlisted' status strings and modern Firestore syntax.
    """
    data = request.json
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({"status": "error", "message": "Missing session_id"}), 400

    try:
        # 1. Fetch Session Metadata
        session_ref = db.collection('recruitment_sessions').document(session_id)
        session_snap = session_ref.get()

        if not session_snap.exists:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        session_info = session_snap.to_dict()
        # Use the role assigned during setup, fallback to JD role if needed
        role = session_info.get('role', 'Technical Intern')

        # 2. Query candidates with ANY shortlisted status
        # This catches "Shortlisted", "Shortlisted & Notified", and "Shortlisted (Mail Fail)"
        shortlist_variants = ["Shortlisted", "Shortlisted & Notified", "Shortlisted (Mail Fail)"]

        candidates_ref = session_ref.collection('candidates').where(
            filter=FieldFilter("status", "in", shortlist_variants)
        ).stream()

        sent_count = 0
        fail_count = 0

        for doc in candidates_ref:
            cand_data = doc.to_dict()
            candidate_email = cand_data.get('email')
            candidate_name = cand_data.get('name', 'Candidate')

            if not candidate_email:
                continue

            # 3. Trigger the Invite Mail (Phase 2 Template)
            # This uses the specific template with the 'Start Assessment' button
            success = send_test_invite_notification(
                to_email=candidate_email,
                candidate_name=candidate_name,
                session_id=session_id,
                c_id=doc.id,
                job_title=role
            )

            if success:
                doc.reference.update({"status": "Test Link Sent"})
                sent_count += 1
            else:
                # Log the error in the terminal for debugging
                print(f"❌ Failed to send link to: {candidate_email}")
                doc.reference.update({"status": "Invite Failed"})
                fail_count += 1

        return jsonify({
            "status": "success",
            "message": f"Successfully sent {sent_count} links. {fail_count} failed."
        })

    except Exception as e:
        print(f"Invite System Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# --- DOCUMENT HUB ROUTES ---

@app.route('/admin/document-setup/<session_id>')
def document_setup(session_id):
    """HR sets what documents are required for this session."""
    session_data = get_session_data(session_id)
    # Default to empty list if no config exists yet
    config = session_data.get('document_config', [
        {"name": "Aadhar Card", "type": "single"},
        {"name": "PAN Card", "type": "single"},
        {"name": "Marksheets", "type": "multiple"}
    ])
    return render_template('admin_document_setup.html', session_id=session_id, config=config)


@app.route('/api/save-doc-config', methods=['POST'])
def save_doc_config():
    data = request.json
    db.collection('recruitment_sessions').document(data['session_id']).update({
        "document_config": data['config']
    })
    return jsonify({"status": "success"})


@app.route('/upload-docs/<session_id>/<c_id>')
def candidate_upload_view(session_id, c_id):
    """Dynamic upload page for candidates based on HR config."""
    session_data = get_session_data(session_id)
    config = session_data.get('document_config', [])
    return render_template('candidate_upload.html', session_id=session_id, c_id=c_id, config=config)


@app.route('/api/upload-files', methods=['POST'])
def handle_file_uploads():
    session_id = request.form.get('session_id')
    c_id = request.form.get('c_id')

    # Create folder structure: storage/docs/session_id/candidate_id/
    upload_path = Path(f"storage/docs/{session_id}/{c_id}")
    upload_path.mkdir(parents=True, exist_ok=True)

    uploaded_docs = {}
    for key in request.files:
        files = request.files.getlist(key)
        file_paths = []
        for file in files:
            fname = secure_filename(file.filename)
            fpath = upload_path / f"{key}_{fname}"
            file.save(fpath)
            file_paths.append(str(fpath))
        uploaded_docs[key] = file_paths

    # Update Firestore candidate record
    db.collection('recruitment_sessions').document(session_id) \
        .collection('candidates').document(c_id).update({
        "documents": uploaded_docs,
        "doc_status": "Uploaded"
    })

    return jsonify({"status": "success"})


# --- DOCUMENT HUB MANAGEMENT ---

@app.route('/admin/document-manager/<session_id>')
def admin_document_manager(session_id):
    """
    The HR Hub for viewing candidate documents.
    This route fetches the data so the HTML can display the 'Vault Cards'.
    """
    try:
        # 1. Fetch all candidates for the session from Firestore
        candidates = []
        docs = db.collection('recruitment_sessions').document(session_id) \
            .collection('candidates').stream()

        for doc in docs:
            cand = doc.to_dict()
            cand['id'] = doc.id  # Ensure we have the Firestore ID for downloading
            candidates.append(cand)

        # 2. Render the manager dashboard
        return render_template('admin_document_manager.html',
                               session_id=session_id,
                               candidates=candidates)
    except Exception as e:
        print(f"❌ Document Hub Error: {e}")
        return f"Error loading hub: {e}", 500


@app.route('/api/download-docs/<session_id>/<c_id>/<doc_name>')
def download_candidate_documents(session_id, c_id, doc_name):
    """
    Downloads a single file directly if only one exists,
    otherwise wraps them in a category-specific ZIP.
    """
    target_dir = BASE_DIR / "storage" / "docs" / session_id / c_id

    # Find all files starting with the category name (e.g., Aadhar_Card_...)
    matching_files = list(target_dir.glob(f"{doc_name}_*"))

    if not matching_files:
        return "No files found", 404

    # FEATURE 1: If only one file, send it directly
    if len(matching_files) == 1:
        return send_file(matching_files[0], as_attachment=True)

    # FEATURE 2: If multiple files, ZIP them
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for file in matching_files:
            zf.write(file, arcname=file.name)

    memory_file.seek(0)
    return send_file(memory_file, download_name=f"{doc_name}_{c_id}.zip", as_attachment=True)


@app.route('/api/download-all-candidate-docs/<session_id>/<c_id>')
def download_all_candidate_docs(session_id, c_id):
    """
    Master ZIP: Grabs EVERY document uploaded by this specific student.
    """
    target_dir = BASE_DIR / "storage" / "docs" / session_id / c_id

    if not target_dir.exists():
        return "No documents found for this candidate", 404

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        # Recursively add everything in the candidate's folder
        for file in target_dir.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=file.name)

    memory_file.seek(0)
    # Fetch candidate name for a professional filename
    cand_doc = db.collection('recruitment_sessions').document(session_id).collection('candidates').document(c_id).get()
    safe_name = cand_doc.to_dict().get('name', 'Candidate').replace(" ", "_")

    return send_file(memory_file, download_name=f"Full_Docs_{safe_name}.zip", as_attachment=True)


# --- NEW ROUTE: CREATE DRIVE ---

@app.route('/admin/create-session')
def render_create_session():
    return render_template('create_session.html')


@app.route('/api/create-session', methods=['POST'])
def handle_create_session():
    """
    Initializes a new isolated recruitment session in Firestore.
    """
    session_name = request.form.get('session_name')
    year = request.form.get('year')
    hr_email = session.get('admin_email', 'system@hirepilot.ai')

    # 1. Handle JD Extraction (Text or File)
    jd_text = request.form.get('jd_text')
    if 'jd_file' in request.files and request.files['jd_file'].filename != '':
        file = request.files['jd_file']
        path = app.config['UPLOAD_FOLDER'] / f"JD_{uuid.uuid4()}_{secure_filename(file.filename)}"
        file.save(path)
        jd_text = extract_text_from_file(path)

    # 2. Create Master Session Object
    session_id = f"{session_name.lower().replace(' ', '_')}_{int(time.time())}"

    session_payload = {
        "session_name": session_name,
        "year": year,
        "jd_text": jd_text,
        "status": "Screening Phase",  # Initial Stage
        "created_at": firestore.SERVER_TIMESTAMP,
        "hr_email": hr_email,
        "total_candidates": 0,
        "shortlisted_count": 0
    }

    db.collection('recruitment_sessions').document(session_id).set(session_payload)

    # Save to user session for easy navigation
    session['last_session_id'] = session_id

    return redirect(url_for('admin_dashboard', session_id=session_id))


# --- UPDATED HISTORY ROUTE ---

# --- CONSOLIDATED HISTORY ROUTE ---

@app.route('/history')
def history_page():
    try:
        sessions_ref = db.collection('recruitment_sessions').order_by('created_at',
                                                                      direction=firestore.Query.DESCENDING)
        all_sessions = []

        for doc in sessions_ref.stream():
            s = doc.to_dict()
            s['id'] = doc.id

            # CRITICAL FIX: Ensure the template sees the real 'Active' status from DB
            s['active'] = s.get('is_active', False)

            status_colors = {
                "Screening Phase": "bg-blue-100 text-blue-600",
                "Testing Phase": "bg-amber-100 text-amber-600",
                "Onboarding Phase": "bg-emerald-100 text-emerald-600"
            }
            s['color_class'] = status_colors.get(s['status'], "bg-slate-100 text-slate-400")
            all_sessions.append(s)

        return render_template('history.html', sessions=all_sessions)
    except Exception as e:
        return render_template('history.html', sessions=[])

@app.route('/admin/session/<session_id>')
def session_command_center(session_id):
    """The 'Drive Control Room' for a specific session."""
    session_data = get_session_data(session_id)
    if not session_data:
        return "Session Not Found", 404

    # Store in flask session to 'remember' which drive we are working on
    session['last_session_id'] = session_id
    return render_template('session_control.html', session_id=session_id, data=session_data)


@app.route('/admin/screen/<session_id>')
def start_screening_for_session(session_id):
    """Opens the screening page pre-loaded with the session's JD."""
    data = get_session_data(session_id)
    return render_template('index.html', session_id=session_id, jd_text=data.get('jd_text', ''))


@app.route('/api/toggle-session/<session_id>', methods=['POST'])
def toggle_session(session_id):
    """
    When HR flips the switch in History, we set THIS
    session as the global active session for the tools.
    """
    data = request.json
    is_active = data.get('active', False)

    # 1. Update DB
    db.collection('recruitment_sessions').document(session_id).update({"is_active": is_active})

    # 2. Update Global Context if activated
    if is_active:
        session['last_session_id'] = session_id
    elif session.get('last_session_id') == session_id:
        session['last_session_id'] = None  # Clear if deactivated

    return jsonify({"status": "success"})


@app.route('/api/update-session-jd', methods=['POST'])
def update_session_jd():
    """Updates the JD context for a specific session."""
    try:
        data = request.json
        s_id = data.get('session_id')
        new_jd = data.get('new_jd')

        db.collection('recruitment_sessions').document(s_id).update({
            "jd_text": new_jd
        })
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/promote-to-interview', methods=['POST'])
def promote_to_interview():
    """
    The Interview Agent: Takes the decision to schedule a
    Virtual Interview based on Test Score + Proctoring Integrity.
    """
    try:
        data = request.json
        s_id = data.get('session_id')
        c_id = data.get('c_id')
        mode = data.get('mode', 'manual')  # 'manual' or 'auto'

        session_ref = db.collection('recruitment_sessions').document(s_id)
        cand_ref = session_ref.collection('candidates').document(c_id)

        candidate = cand_ref.get().to_dict()
        session_data = session_ref.get().to_dict()

        # --- THE AGENT'S BRAIN (Decision Logic) ---
        score = candidate.get('test_score', 0)
        violations = candidate.get('proctoring_violations', 0)
        min_req = int(session_data.get('min_score', 70))

        # Agent Decision
        if mode == 'auto':
            if score >= min_req and violations == 0:
                decision = "Recommended for Interview"
                new_status = "Interview Scheduled (Auto)"
            else:
                return jsonify({"status": "denied", "reason": "Candidate does not meet AI integrity standards."})
        else:
            new_status = "Interview Scheduled (Manual)"

        # Update Status & Move to Interview Pipeline
        cand_ref.update({
            "status": new_status,
            "interview_ready": True,
            "stage": "Virtual Interview"
        })

        # Trigger Virtual Interview Invite (Mocking for now)
        # send_interview_invite(candidate['email'], s_id, c_id)

        return jsonify({"status": "success", "new_status": new_status})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/admin/session-results/<session_id>')
def session_results_hub(session_id):
    """
    The Post-Assessment Merit List:
    Shows HR the final standings and allows for manual verification.
    """
    session_data = get_session_data(session_id)
    if not session_data:
        return "Session Not Found", 404

    # Fetch all candidates who COMPLETED the test
    # We sort by test_score descending to create a natural Leaderboard
    candidates = []
    docs = db.collection('recruitment_sessions').document(session_id) \
        .collection('candidates') \
        .order_by('test_score', direction=firestore.Query.DESCENDING) \
        .stream()

    for doc in docs:
        c = doc.to_dict()
        c['id'] = doc.id
        candidates.append(c)

    return render_template('session_results.html',
                           session_id=session_id,
                           data=session_data,
                           candidates=candidates)

@app.route('/api/virtual-interview-report/<interview_id>')
def virtual_interview_report(interview_id):
    from backend.services.interview_service import get_interview_service
    interview_data = get_interview_service(interview_id)
    if not interview_data:
        return jsonify({"error": "Interview not found"}), 404
        
    return jsonify({
        "status": interview_data.get("status", "unknown"),
        "qa_pairs": interview_data.get("qa_pairs", []),
        "overall_feedback": interview_data.get("overall_feedback", "Not completed yet")
    })


import csv

@app.route('/api/export-merit-zip/<session_id>')
def export_merit_zip(session_id):
    """
    Creates a master archive for HR containing:
    1. merit_list.csv (Ranked)
    2. individual_analysis_reports/ (Folder of PDFs)
    """
    session_ref = db.collection('recruitment_sessions').document(session_id)
    candidates = session_ref.collection('candidates').order_by('test_score',
                                                               direction=firestore.Query.DESCENDING).stream()

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        # 1. Create Merit List CSV
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(['Rank', 'Name', 'Email', 'Screening Score', 'Test Score', 'Violations', 'Status'])

        for idx, doc in enumerate(candidates, 1):
            c = doc.to_dict()
            writer.writerow([idx, c.get('name'), c.get('email'), c.get('match_score'), c.get('test_score'),
                             c.get('proctoring_violations', 0), c.get('status')])

            # 2. Add individual PDF reports to the ZIP
            pdf_bytes = create_pdf_report(c)  # Using your existing PDF function
            safe_name = "".join([x for x in c.get('name', 'Candidate') if x.isalnum() or x == ' '])
            zf.writestr(f"Reports/{idx}_{safe_name}_Audit.pdf", pdf_bytes)

        zf.writestr("Master_Merit_List.csv", csv_buffer.getvalue())

    memory_file.seek(0)
    return send_file(memory_file, download_name=f"HirePilot_Final_Results_{session_id}.zip", as_attachment=True)


@app.route('/api/candidate-test-details/<session_id>/<c_id>')
def get_candidate_test_details(session_id, c_id):
    """
    Fetches real Q&A pairs for HR audit.
    Aligned with 'q0', 'q1' indexing to prevent 'Not Attempted' errors.
    """
    try:
        session_ref = db.collection('recruitment_sessions').document(session_id)
        session_data = session_ref.get().to_dict()

        cand_doc = session_ref.collection('candidates').document(c_id).get()
        if not cand_doc.exists:
            return jsonify({"error": "Candidate not found"}), 404

        candidate = cand_doc.to_dict()
        questions = session_data.get('active_test', [])

        # This is where the mismatch was happening:
        user_answers = candidate.get('submitted_answers', {})

        audit_log = []

        # We loop by index to match the 'q0', 'q1' format sent by the frontend
        for idx, q in enumerate(questions):
            frontend_key = f"q{idx}"

            # 1. Get what the candidate chose
            selected = user_answers.get(frontend_key, "Not Attempted")

            # 2. Get the correct answer text
            correct_idx = q.get('correct')
            options = q.get('options', [])
            correct_text = options[correct_idx] if correct_idx is not None and correct_idx < len(options) else "N/A"

            audit_log.append({
                "question": q.get('question'),
                "selected": selected,
                "correct": correct_text,
                "is_correct": str(selected).strip() == str(correct_text).strip()
            })

        return jsonify({
            "candidate_name": candidate.get('name'),
            "score": candidate.get('test_score'),
            "audit": audit_log
        })
    except Exception as e:
        print(f"❌ Audit API Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/update-min-score', methods=['POST'])
def update_min_score():
    """Dynamically updates the passing threshold for the session."""
    try:
        data = request.json
        s_id = data.get('session_id')
        new_min = int(data.get('min_score', 70))

        # Update the session config
        db.collection('recruitment_sessions').document(s_id).update({
            "min_score": new_min
        })

        # Optional: You could run a batch update on candidate statuses here,
        # but doing it via Jinja2 in the UI (below) is faster for HR to visualize.
        return jsonify({"status": "success", "new_threshold": new_min})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)