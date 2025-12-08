from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import uuid
from pydantic import BaseModel

# Import Aura modules
# Ensure src is in path
import sys
sys.path.append(os.getcwd())

from src.core.brain import process_input
from src.output.tts import speak, load_tts_model
from src.perception.audio import transcribe_audio_file, analyze_emotion_file, load_audio_models, load_text_emotion_model

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Load models on startup
@app.on_event("startup")
async def startup_event():
    print("Loading models...")
    try:
        load_tts_model()
        load_audio_models()
        load_text_emotion_model()
        print("Models loaded.")
    except Exception as e:
        print(f"Error loading models: {e}")

class ChatRequest(BaseModel):
    text: str
    emotion: str = "neutral"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    print(f"Received chat: {request.text} ({request.emotion})")
    # Process input
    response_text = process_input({"text": request.text, "emotion": request.emotion})
    
    # Generate Audio
    audio_file = speak(response_text, return_file=True)
    
    # Determine animations (list)
    animations = []
    lower_resp = response_text.lower()
    
    # Check for keywords and add corresponding animations
    if "hug" in lower_resp: animations.append("hug")
    if "dance" in lower_resp: animations.append("dance")
    if "happy" in lower_resp: animations.append("happy")
    if "sad" in lower_resp or "cry" in lower_resp: animations.append("sad")
    if "clap" in lower_resp: animations.append("clap")
    if "pray" in lower_resp: animations.append("pray")
    if "jump" in lower_resp: animations.append("jump")
    
    # If no specific animation, default to just talk (or empty list which means idle/talk)
    if not animations:
        animations = ["talk"]
    
    audio_url = f"/audio/{os.path.basename(audio_file)}" if audio_file else None
    
    return {
        "text": response_text,
        "audio_url": audio_url,
        "animations": animations # Return list
    }

@app.post("/api/audio")
async def upload_audio(file: UploadFile = File(...)):
    temp_filename = f"temp_{uuid.uuid4()}.wav"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    print(f"Processing audio file: {temp_filename}")
    # Transcribe
    text = transcribe_audio_file(temp_filename)
    emotion = analyze_emotion_file(temp_filename)
    
    os.remove(temp_filename)
    
    if not text:
        return {"text": "I couldn't hear you.", "audio_url": None, "animation": "idle"}
        
    print(f"Transcribed: {text}, Emotion: {emotion}")
    
    # Process
    response_text = process_input({"text": text, "emotion": emotion})
    
    # Generate Audio
    audio_file = speak(response_text, return_file=True)
    
    # Determine animations (list)
    animations = []
    lower_resp = response_text.lower()
    
    if "hug" in lower_resp: animations.append("hug")
    if "dance" in lower_resp: animations.append("dance")
    if "happy" in lower_resp: animations.append("happy")
    if "sad" in lower_resp or "cry" in lower_resp: animations.append("sad")
    if "clap" in lower_resp: animations.append("clap")
    if "pray" in lower_resp: animations.append("pray")
    if "jump" in lower_resp: animations.append("jump")
    
    if not animations:
        animations = ["talk"]
    
    audio_url = f"/audio/{os.path.basename(audio_file)}" if audio_file else None
    
    return {
        "input_text": text,
        "input_emotion": emotion,
        "text": response_text,
        "audio_url": audio_url,
        "animations": animations
    }

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.abspath(filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTTPException(status_code=404, detail="File not found")

@app.get("/")
async def read_index():
    return FileResponse("web/static/index.html")
