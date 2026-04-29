from flask import Blueprint, request, jsonify
from backend.services.voice_service import generate_voice

voice_bp = Blueprint("voice", __name__)


@voice_bp.route("/speak", methods=["POST"])
def speak():
    data = request.get_json()
    text = data.get("text")

    file_path = generate_voice(text)

    if not file_path:
        return jsonify({"error": "Voice generation failed"}), 500

    return jsonify({
        "audio_url": "/" + file_path
    })