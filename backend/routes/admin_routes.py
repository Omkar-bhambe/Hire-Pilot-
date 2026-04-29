from flask import Blueprint, jsonify, request
import os

from services.interview_service import INTERVIEWS, schedule_interview_service
from middleware.jwt_auth import require_admin
from utils.pdf_parser import extract_text_from_pdf

admin_bp = Blueprint("admin", __name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ================= CREATE INTERVIEW =================
@admin_bp.route("/create-interview", methods=["POST"])
@require_admin
def create_interview():
    try:
        name = request.form.get("name")
        email = request.form.get("email")
        job_description = request.form.get("job_description")
        schedule_time = request.form.get("schedule_time")
        file = request.files.get("resume")

        # 🔥 VALIDATION
        if not all([name, email, job_description, schedule_time, file]):
            return jsonify({"error": "All fields required"}), 400

        # ================= SAVE FILE =================
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # ================= EXTRACT TEXT =================
        try:
            resume_text = extract_text_from_pdf(file_path)
        except Exception as e:
            print("PDF Error:", e)
            return jsonify({"error": "PDF parsing failed"}), 500

        # ================= CREATE DATA =================
        data = {
            "name": name,
            "email": email,
            "job_description": job_description,
            "resume": resume_text,
            "schedule_time": schedule_time
        }

        # ================= CREATE INTERVIEW =================
        interview_id = schedule_interview_service(data)

        return jsonify({
            "status": "success",
            "interview_id": interview_id
        })

    except Exception as e:
        print("Create Interview Error:", e)
        return jsonify({"error": str(e)}), 500


# ================= GET ALL INTERVIEWS =================
@admin_bp.route("/interviews", methods=["GET"])
@require_admin
def get_all_interviews():
    try:
        # Convert dictionary to list
        interviews = list(INTERVIEWS.values())

        # Optional: sort latest first
        interviews = sorted(interviews, key=lambda x: x.get("schedule_time", ""), reverse=True)

        return jsonify({
            "data": interviews
        })

    except Exception as e:
        print("Fetch Error:", e)
        return jsonify({"error": "Failed to fetch interviews"}), 500


# ================= GET SINGLE INTERVIEW =================
@admin_bp.route("/interview/<interview_id>", methods=["GET"])
@require_admin
def get_interview(interview_id):
    try:
        interview = INTERVIEWS.get(interview_id)

        if not interview:
            return jsonify({"error": "Interview not found"}), 404

        return jsonify({
            "data": interview
        })

    except Exception as e:
        print("Get Interview Error:", e)
        return jsonify({"error": "Failed to fetch interview"}), 500