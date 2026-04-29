from flask import Flask, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
import os

# ================= DATABASE =================
from database.db import init_db

# ================= INIT APP =================
app = Flask(__name__)
app.secret_key = "super_secret_key"

# ================= CONFIG =================
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ================= INIT DB =================
init_db()

# ================= CREATE FOLDERS =================
os.makedirs("uploads", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# ================= IMPORT ROUTES =================
from routes.interview_routes import interview_bp
from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp

# ================= REGISTER BLUEPRINTS =================
app.register_blueprint(interview_bp, url_prefix="/api/interview")
app.register_blueprint(admin_bp, url_prefix="/api/admin")
app.register_blueprint(auth_bp, url_prefix="/api/auth")
from routes.voice_routes import voice_bp
app.register_blueprint(voice_bp, url_prefix="/api/voice")

# ================= BASIC ROUTES =================
@app.route("/")
def home():
    return jsonify({
        "status": "success",
        "message": "AI Interview System Running 🚀"
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })

# ================= TEMPLATE ROUTES =================

# 🔐 Admin Login Page
@app.route("/admin")
def admin_login():
    return render_template("admin_login.html")

# 📊 Admin Dashboard
@app.route("/dashboard")
def dashboard():
    return render_template("admin_dashboard.html")

# 🎤 Interview Page
@app.route("/interview/<interview_id>")
def interview_page(interview_id):
    return render_template("interview.html", interview_id=interview_id)

# ================= ERROR HANDLING =================
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "error": "not_found"
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "status": "error",
        "error": "internal_server_error"
    }), 500

# ================= RUN =================
if __name__ == "__main__":
    print("\n🚀 Server running on http://localhost:5000\n")
    print("👉 Admin Login: http://localhost:5000/admin")
    print("👉 Dashboard: http://localhost:5000/dashboard\n")

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True
    )