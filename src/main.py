from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import openai
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from functools import lru_cache

# Demo at: http://127.0.0.1:5001

# Load environment variables
load_dotenv()

app = FastAPI()

# Set up template directory
templates = Jinja2Templates(directory="templates")

# Configure API keys from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please check your .env file.")

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY environment variable is not set. Please check your .env file.")

openai.api_key = OPENAI_API_KEY

# Import Whisper for speech-to-text
try:
    import whisper
    print(f"Successfully imported Whisper")
    has_whisper = True
    # Load Whisper STT model
    model = whisper.load_model("tiny")
except Exception as e:
    print(f"Warning: Failed to initialize Whisper: {str(e)}")
    has_whisper = False

# Import ElevenLabs for text-to-speech
try:
    import elevenlabs
    # Set API key using the current ElevenLabs API version (0.2.24)
    elevenlabs.set_api_key(ELEVENLABS_API_KEY)
    has_elevenlabs = True
    print("Successfully initialized ElevenLabs")
except Exception as e:
    print(f"Warning: Failed to initialize ElevenLabs: {str(e)}")
    has_elevenlabs = False

# Import PyDub for audio processing
try:
    from pydub import AudioSegment
    has_pydub = True
    print("Successfully imported PyDub")
except ImportError:
    print("Warning: pydub module not available. Audio conversion functionality will be limited.")
    has_pydub = False

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request) -> HTMLResponse:
    """Serve the frontend application."""
    return templates.TemplateResponse("index.html", {"request": request, "components": {
        "whisper": has_whisper,
        "elevenlabs": has_elevenlabs,
        "pydub": has_pydub,
        "gpt_model": "gpt-3.5-turbo",
        "whisper_model": "tiny",
        "tts_caching": "active (100 entries)"
    }})

@app.get("/test")
async def test_endpoint() -> dict:
    """Test endpoint to check if API is responsive."""
    return {"status": "ok", "message": "Test endpoint is working"}

@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "message": "Voice agent API is running",
        "components": {
            "whisper": has_whisper,
            "elevenlabs": has_elevenlabs,
            "pydub": has_pydub,
            "tts_caching": "active (100 entries)"
        }
    }

@app.post("/talk")
async def talk(audio: UploadFile = File(...)) -> dict:
    """Processes user speech, generates AI response, and returns spoken output."""
    
    timing_data = {}
    
    # Step 1: Audio Input Processing
    step1_start = time.time()
    
    # Create temp directory if it doesn't exist
    os.makedirs("temp", exist_ok=True)
    
    # Save the uploaded audio
    audio_path = f"temp/{audio.filename}"
    with open(audio_path, "wb") as f:
        f.write(audio.file.read())

    # Convert to WAV if needed and if pydub is available
    if has_pydub and not audio.filename.endswith(".wav"):
        try:
            sound = AudioSegment.from_file(audio_path)
            audio_path = audio_path.replace(audio.filename.split('.')[-1], "wav")
            sound.export(audio_path, format="wav")
        except Exception as e:
            return {"error": f"Failed to convert audio: {str(e)}"}
    
    step1_end = time.time()
    timing_data["audio_processing"] = round((step1_end - step1_start) * 1000, 2)  # in milliseconds
    
    # Step 2: Speech-to-Text Conversion
    step2_start = time.time()
    
    # Transcribe speech to text if whisper is available
    if has_whisper:
        try:
            result = model.transcribe(audio_path)
            user_text = result["text"]
        except Exception as e:
            return {"error": f"Failed to transcribe audio: {str(e)}"}
    else:
        # Fallback for testing when whisper is not available
        user_text = "Hello, I'd like to talk to you today."
    
    step2_end = time.time()
    timing_data["speech_to_text"] = round((step2_end - step2_start) * 1000, 2)  # in milliseconds
    
    # Step 3: AI Response Generation
    step3_start = time.time()
    
    # Generate AI response using GPT
    try:
        gpt_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a friendly companion for elderly users."},
                      {"role": "user", "content": user_text}]
        )
        bot_text = gpt_response["choices"][0]["message"]["content"]
    except Exception as e:
        return {"error": f"Failed to generate response: {str(e)}"}
    
    step3_end = time.time()
    timing_data["ai_response"] = round((step3_end - step3_start) * 1000, 2)  # in milliseconds
    
    # Step 4: Text-to-Speech Synthesis
    step4_start = time.time()
    
    # Convert AI response to speech if elevenlabs is available
    if has_elevenlabs:
        try:
            # Use the appropriate function for ElevenLabs version 0.2.24
            voice = "Bella"
            
            # Use cached TTS generation
            tts_audio = cached_tts_generate(bot_text, voice)
            
            # Save generated speech
            output_path = "temp/output.mp3"
            with open(output_path, "wb") as f:
                f.write(tts_audio)
            
            step4_end = time.time()
            timing_data["text_to_speech"] = round((step4_end - step4_start) * 1000, 2)  # in milliseconds
            
            # Step 5: Response Delivery
            step5_start = time.time()
            
            response = FileResponse(output_path, media_type="audio/mpeg")
            
            # Add timing data to response headers
            for key, value in timing_data.items():
                response.headers[f"X-Timing-{key}"] = str(value)
            
            step5_end = time.time()
            timing_data["response_delivery"] = round((step5_end - step5_start) * 1000, 2)  # in milliseconds
            
            # Add total processing time
            timing_data["total_time"] = round(sum(timing_data.values()), 2)
            
            # Add timing data to headers
            response.headers["X-Timing-Data"] = str(timing_data)
            
            return response
            
        except Exception as e:
            step4_end = time.time()
            timing_data["text_to_speech"] = round((step4_end - step4_start) * 1000, 2)  # in milliseconds
            timing_data["response_delivery"] = 0  # Failed
            timing_data["total_time"] = round(sum(timing_data.values()), 2)
            
            return {"error": f"Failed to generate speech with elevenlabs: {str(e)}", 
                    "text": bot_text,
                    "timing": timing_data}
    else:
        # Fallback when text-to-speech is not available
        step4_end = time.time()
        timing_data["text_to_speech"] = 0  # Not performed
        
        # Step 5: Response Delivery
        step5_start = time.time()
        step5_end = time.time()
        timing_data["response_delivery"] = round((step5_end - step5_start) * 1000, 2)  # in milliseconds
        
        # Add total processing time
        timing_data["total_time"] = round(sum(timing_data.values()), 2)
        
        return {"text": bot_text, "timing": timing_data}

# Add LRU cache for TTS generation to improve performance on repetitive responses
@lru_cache(maxsize=100)
def cached_tts_generate(text: str, voice: str = "Bella") -> bytes:
    """Cache TTS responses to avoid regenerating the same text.
    
    Args:
        text: The text to convert to speech
        voice: The voice to use for generation
        
    Returns:
        Bytes containing the generated audio
    """
    return elevenlabs.generate(
        text=text,
        voice=voice
    )

# Add entry point to run the FastAPI app with Uvicorn
if __name__ == "__main__":
    import uvicorn
    # Run on port 5001 to avoid conflicts with AirPlay on macOS
    uvicorn.run(app, host="127.0.0.1", port=5001)
