from flask import Flask, render_template, request, send_file
import requests
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allow CORS for frontend-backend communication
from flask_cors import CORS
CORS(app)

FASTAPI_BACKEND_URL = "http://127.0.0.1:8000/talk"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_audio():
    if "audio" not in request.files:
        return "No audio file provided", 400

    audio_file = request.files["audio"]
    audio_path = os.path.join(UPLOAD_FOLDER, "voice.wav")
    audio_file.save(audio_path)

    # Send audio to FastAPI backend
    with open(audio_path, "rb") as f:
        response = requests.post(FASTAPI_BACKEND_URL, files={"audio": f})

    if response.status_code == 200:
        # Save received audio response
        output_audio_path = os.path.join(UPLOAD_FOLDER, "response.mp3")
        with open(output_audio_path, "wb") as f:
            f.write(response.content)
        return send_file(output_audio_path, as_attachment=True, mimetype="audio/mpeg")

    return "Error processing audio", 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
