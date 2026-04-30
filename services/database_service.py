import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
import uuid

# Initialize Firebase Admin SDK
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
local_key_path = os.path.join(base_dir, "firebase-key.json")
render_secret_path = "/etc/secrets/firebase-key.json"

if os.environ.get("FIREBASE_CREDENTIALS"):
    cred_dict = json.loads(os.environ.get("FIREBASE_CREDENTIALS"))
    cred = credentials.Certificate(cred_dict)
elif os.path.exists(render_secret_path):
    cred = credentials.Certificate(render_secret_path)
else:
    cred = credentials.Certificate(local_key_path)

if not firebase_admin._apps:
    initialize_app(cred)
db = firestore.client()



def get_batch_results(batch_id):
    """
    Retrieves all candidates for a specific recruitment batch.
    """
    results = []
    docs = db.collection('screenings').where("batch_id", "==", batch_id).stream()
    for doc in docs:
        results.append(doc.to_dict())
    return results




# (Keep your existing initialization code here)
#
def initialize_screening_session(session_name, hr_email, jd_prompt=None, jd_file_text=None):
    """
    Creates the main session document.
    This acts as the 'Anchor' for Online Tests and AI Interviews.
    """
    # Use the name as the document ID (slugified for URL safety)
    session_id = session_name.replace(" ", "_").lower()
    session_ref = db.collection('resume_screening').document(session_id)

    session_ref.set({
        "session_name": session_name,
        "hr_owner": hr_email,
        "created_at": firestore.SERVER_TIMESTAMP,
        "job_context": {
            "prompt": jd_prompt,
            "file_text": jd_file_text,
            "processed_at": datetime.now()
        },
        "status": "Active"
    })
    return session_id


def save_candidate_to_session(session_id, data):
    """
    Saves candidate results into a sub-collection under the specific session.
    """
    # Sub-collection 'candidates' under the specific session document
    candidate_ref = db.collection('resume_screening').document(session_id).collection('candidates').document()

    candidate_ref.set({
        "name": data.get('name'),
        "email": data.get('email'),
        "match_score": data.get('match_score'),
        "justification": data.get('justification'),
        "status": data.get('status'),
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    return candidate_ref.id



def save_extracted_resume_to_cloud(session_id, candidate_name, resume_text):
    """Stores individual extracted resumes (from files or ZIPs) to the cloud."""
    # We create the document now so we have a place to put AI results later
    doc_ref = db.collection('recruitment_sessions').document(session_id) \
 .collection('candidates').document()
    doc_ref.set({
        "name": candidate_name,
        "raw_resume_text": resume_text,
        "processed": False,
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return doc_ref.id


def update_candidate_results(session_id, candidate_id, ai_results):
    """Updates the existing candidate document with Gemini's screening output."""
    candidate_ref = db.collection('recruitment_sessions').document(session_id) \
        .collection('candidates').document(candidate_id)
    candidate_ref.update({
        **ai_results,
        "processed": True,
        "processed_at": firestore.SERVER_TIMESTAMP
    })

def create_recruitment_session(session_name, hr_email, jd_text):
    """
    Step 1: The 'Anchor'. Creates the master session ID and stores the JD.
    This ensures the 'setup' page can find the JD later.
    """
    # Create a unique, URL-safe ID using name and timestamp
    timestamp = int(datetime.now().timestamp())
    session_id = f"{session_name.replace(' ', '_').lower()}_{timestamp}"

    session_ref = db.collection('recruitment_sessions').document(session_id)
    session_ref.set({
        "session_id": session_id,
        "session_name": session_name,
        "hr_owner": hr_email,
        "jd_text": jd_text,  # CRITICAL: This allows the setup page to find the JD
        "created_at": firestore.SERVER_TIMESTAMP,
        "status": "Screening Phase"
    })
    return session_id

def save_screening_result(session_id, candidate_data):
    """
    Step 2: Saves candidate results INTO the session's sub-collection.
    """
    try:
        # Link directly to the session created in Step 1
        candidate_ref = db.collection('recruitment_sessions').document(session_id) \
            .collection('candidates').document()

        candidate_ref.set({
            "name": candidate_data.get('name'),
            "email": candidate_data.get('email'),
            "match_score": candidate_data.get('match_score'),
            "justification": candidate_data.get('justification'),
            "status": candidate_data.get('status'),
            "timestamp": datetime.now()
        })
        return True
    except Exception as e:
        print(f"Database Error: {e}")
        return False

def get_session_test_context(session_id):
    """Retrieves JD and Shortlisted candidates for the Test Agent."""
    session_ref = db.collection('recruitment_sessions').document(session_id)
    session_data = session_ref.get().to_dict()

    # Only pull candidates who passed the initial AI Screening
    candidates = session_ref.collection('candidates') \
        .where("status", "in", ["Shortlisted", "Shortlisted & Notified"]).stream()

    return {
        "jd_text": session_data.get('job_description'),
        "candidates": [doc.to_dict() for doc in candidates]
    }


def save_test_results(session_id, candidate_email, score_data):
    """Saves test performance into the existing candidate cloud document."""
    candidate_query = db.collection('recruitment_sessions').document(session_id) \
        .collection('candidates').where("email", "==", candidate_email).stream()

    for doc in candidate_query:
        doc.reference.update({
            "test_score": score_data.get('score'),
            "test_status": "Completed",
            "test_completed_at": firestore.SERVER_TIMESTAMP,
            "test_metadata": score_data.get('metadata')
        })


def init_cloud_session(jd_text, role):
    """
    Step 1: Creates a unique recruitment session ID.
    This is triggered during the resume screening phase.
    """
    session_id = str(uuid.uuid4())[:8]  # Generates an 8-character unique ID
    doc_ref = db.collection('recruitment_sessions').document(session_id)
    doc_ref.set({
        'session_id': session_id,
        'jd_text': jd_text,
        'role': role,
        'created_at': datetime.now(),
        'status': 'screening'
    })
    return session_id


def get_session_data(session_id):
    """
    Step 2: Retrieves session context (JD, Role, Generated Test).
    Used by the HR Setup and Candidate Exam pages.
    """
    doc_ref = db.collection('recruitment_sessions').document(session_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None


def save_candidate_test(session_id, candidate_id, test_results):
    """
    Step 3: Saves results to the candidate's specific document.
    Stores score, proctoring violations, and compliance status.
    """
    # Logic: Update the specific candidate record within the session
    candidate_ref = db.collection('recruitment_sessions').document(session_id) \
        .collection('candidates').document(candidate_id)

    candidate_ref.update({
        'test_results': test_results,
        'updated_at': datetime.now(),
        'last_action': 'Assessment Completed'
    })
    return True

# ==========================================
# Virtual Interview Methods
# ==========================================

def create_virtual_interview(interview_id, data):
    """Saves a scheduled virtual interview to Firestore."""
    db.collection('virtual_interviews').document(interview_id).set({
        "id": interview_id,
        "name": data.get("name"),
        "email": data.get("email"),
        "job_description": data.get("job_description"),
        "resume": data.get("resume"),
        "schedule_time": data.get("schedule_time"),
        "status": "scheduled",
        "answers": [],
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return interview_id

def get_virtual_interview(interview_id):
    """Retrieves a virtual interview from Firestore."""
    doc = db.collection('virtual_interviews').document(interview_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

def update_virtual_interview_answers(interview_id, answers):
    """Updates the answers array in Firestore."""
    db.collection('virtual_interviews').document(interview_id).update({
        "answers": answers,
        "updated_at": firestore.SERVER_TIMESTAMP
    })

def complete_virtual_interview(interview_id):
    """Marks a virtual interview as completed in Firestore."""
    db.collection('virtual_interviews').document(interview_id).update({
        "status": "completed",
        "completed_at": firestore.SERVER_TIMESTAMP
    })
