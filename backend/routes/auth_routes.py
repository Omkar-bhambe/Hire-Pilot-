from flask import Blueprint, request, jsonify
import jwt
from datetime import datetime, timedelta

auth_bp = Blueprint("auth", __name__)

SECRET = "super_secret_key"


# ================= LOGIN =================
@auth_bp.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    # 🔥 Hardcoded admin (for now)
    if email == "admin@gmail.com" and password == "admin123":

        token = jwt.encode({
            "email": email,
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=5)
        }, SECRET, algorithm="HS256")

        return jsonify({
            "status": "success",
            "token": token
        })

    return jsonify({
        "status": "error",
        "error": "Invalid credentials"
    }), 401