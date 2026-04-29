import jwt
from functools import wraps
from flask import request, jsonify

# 🔐 CHANGE THIS IN PRODUCTION
SECRET = "super_secret_key"


# ================= VERIFY TOKEN =================
def verify_token(token):
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
        return data
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}
    except Exception:
        return {"error": "Token verification failed"}


# ================= ADMIN MIDDLEWARE =================
def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        # Check header exists
        if not auth_header:
            return jsonify({"error": "Authorization header missing"}), 401

        # Format check: Bearer <token>
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Invalid token format"}), 401

        try:
            token = auth_header.split(" ")[1]
        except IndexError:
            return jsonify({"error": "Token missing"}), 401

        # Verify token
        data = verify_token(token)

        # Handle token errors
        if not data or "error" in data:
            return jsonify({"error": data.get("error", "Unauthorized")}), 401

        # Check admin role
        if data.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)

    return wrapper