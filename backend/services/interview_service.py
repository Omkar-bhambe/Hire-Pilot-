import uuid
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# These imports will work because we'll append backend to sys.path in main.py
from backend.agents.questions_agent import QuestionAgent
from backend.utils.gemini_client import GeminiClient

# Import the new firestore functions
from services.database_service import (
    create_virtual_interview,
    get_virtual_interview,
    update_virtual_interview_answers,
    complete_virtual_interview
)

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCdvHcqScAzrXgl2ycqytHJLMi_NQJHLmI")
gemini = GeminiClient(api_key=API_KEY)
question_agent = QuestionAgent(gemini)


def check_interview_time(schedule_time):
    try:
        if not schedule_time:
            return "active"
        dt = datetime.strptime(schedule_time, "%b %d, %Y, %I:%M %p")
        now = datetime.now()
        end = dt + timedelta(minutes=30)

        if now < dt:
            return "not_started"
        elif dt <= now <= end:
            return "active"
        else:
            return "expired"
    except:
        return "active"


def schedule_interview_service(data):
    # Create interview in firestore
    interview_id = create_interview_service(data)

    # SEND EMAIL
    from services.notification_service import send_virtual_interview_link
    try:
        send_virtual_interview_link(
            to_email=data["email"],
            candidate_name=data["name"],
            interview_id=interview_id
        )
    except Exception as e:
        print("Error sending virtual interview email:", e)
        
    return interview_id


def create_interview_service(data):
    interview_id = str(uuid.uuid4())
    create_virtual_interview(interview_id, data)
    return interview_id


def get_interview_service(interview_id):
    interview = get_virtual_interview(interview_id)

    if not interview:
        return None

    time_status = check_interview_time(interview.get("schedule_time"))

    if time_status == "not_started":
        return {
            "status": "not_started",
            "schedule_time": interview.get("schedule_time")
        }

    if time_status == "expired":
        return {"status": "expired"}
        
    # Check if completed
    if interview.get('status') == 'completed':
        return {"status": "completed"}

    # ================= ACTIVE =================
    answers = interview.get("answers", [])

    # FIRST QUESTION
    if len(answers) == 0:
        question = question_agent.first_question(
            interview.get("job_description", ""),
            interview.get("resume", "")
        )
    # NEXT QUESTION
    else:
        last = answers[-1]
        question = question_agent.next_question(
            interview.get("job_description", ""),
            interview.get("resume", ""),
            last["question"],
            last["answer"],
            answers
        )

    return {
        "status": "active",
        "current_question": question
    }


def submit_answer_service(interview_id, question, answer):
    interview = get_virtual_interview(interview_id)
    if not interview:
        return {"status": "error", "message": "Interview not found"}

    answers = interview.get("answers", [])
    answers.append({
        "question": question,
        "answer": answer
    })

    # Save immediately back to firestore
    update_virtual_interview_answers(interview_id, answers)

    next_q = question_agent.next_question(
        interview.get("job_description", ""),
        interview.get("resume", ""),
        question,
        answer,
        answers
    )

    return {
        "next_question": next_q,
        "completed": False
    }


def complete_interview_service(interview_id):
    complete_virtual_interview(interview_id)
    return {"message": "completed"}