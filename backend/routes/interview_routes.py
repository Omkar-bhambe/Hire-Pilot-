from flask import Blueprint, request, jsonify
from backend.services.interview_service import (
    create_interview_service,
    get_interview_service,
    submit_answer_service,
    complete_interview_service
)

# ================= BLUEPRINT =================
interview_bp = Blueprint("interview", __name__)

# ================= CREATE INTERVIEW =================
@interview_bp.route("/create", methods=["POST"])
def create_interview():
    try:
        data = request.get_json()

        required_fields = ["name", "email", "job_description", "resume"]

        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "status": "error",
                    "message": f"{field} is required"
                }), 400

        interview_id = create_interview_service(data)

        return jsonify({
            "status": "success",
            "interview_id": interview_id
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ================= GET INTERVIEW =================
@interview_bp.route("/<interview_id>", methods=["GET"])
def get_interview(interview_id):
    try:
        interview = get_interview_service(interview_id)

        if not interview:
            return jsonify({
                "status": "error",
                "message": "Interview not found"
            }), 404

        return jsonify(interview)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ================= SUBMIT ANSWER =================
@interview_bp.route("/<interview_id>/answer", methods=["POST"])
def submit_answer(interview_id):
    try:
        data = request.get_json()

        question = data.get("question")
        answer = data.get("answer")

        if not question or not answer:
            return jsonify({
                "status": "error",
                "message": "question and answer required"
            }), 400

        result = submit_answer_service(interview_id, question, answer)

        return jsonify({
            "status": "success",
            "data": result
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ================= COMPLETE INTERVIEW =================
@interview_bp.route("/<interview_id>/complete", methods=["POST"])
def complete_interview(interview_id):
    try:
        result = complete_interview_service(interview_id)

        return jsonify({
            "status": "success",
            "data": result
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500