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
from src.perception.nv_ace import ace_client

app = FastAPI()

print("\n" + "="*50)
print("AURA SERVER STARTED")
print("ACCESS URL: http://localhost:8000")
print("="*50 + "\n")

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
    gesture: str = "none"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    print(f"Received chat: {request.text} ({request.emotion}), Gesture: {request.gesture}")
    # Process input
    response_text = process_input({"text": request.text, "emotion": request.emotion, "gesture": request.gesture})
    
    # Generate Audio
    audio_file = speak(response_text, return_file=True)
    
    # Generate Face Animation using NVIDIA ACE
    face_animation = None
    if audio_file:
        face_animation = ace_client.process_audio(audio_file)
    
    # Determine animations (list)
    # Determine animations (list)
    animations = []
    lower_resp = response_text.lower()
    
    # Priority: Gesture -> Keywords -> Default
    
    # 1. Gesture Mapping (Explicit Visual Feedback)
    if "thumbs_up" in request.gesture:
        animations.append("happy")
    elif "victory" in request.gesture:
        animations.append("dance")
    elif "wave" in request.gesture:
        animations.append("clap") # Fallback for wave
    elif "clap" in request.gesture:
        animations.append("clap")
    elif "dance" in request.gesture:
        animations.append("dance")
    elif "hug" in request.gesture:
        animations.append("happy") # Fallback for hug

    # 1.5 Emotion Mapping (Visual Feedback for Face)
    if request.emotion == "happy":
        animations.append("happy")
    elif request.emotion == "sad":
        animations.append("sad")
    elif request.emotion == "surprised":
        animations.append("happy") # Or some surprise animation if we had one
    elif request.emotion == "angry":
        animations.append("sad") # Or angry behavior if defined
        
    # 2. Keyword Mapping (if no gesture specific animation or to add more)
    if not animations:
        if "hug" in lower_resp: animations.append("happy") # Fallback
        if "dance" in lower_resp: animations.append("dance")
        if "happy" in lower_resp: animations.append("happy")
        if "sad" in lower_resp or "cry" in lower_resp: animations.append("sad")
        if "clap" in lower_resp: animations.append("clap")
        if "pray" in lower_resp: animations.append("pray")
        if "jump" in lower_resp: animations.append("jump")
    
    # If no specific animation, default to "idle" (client handles talking state separately logic)
    # or "talk" if we had one.
    if not animations:
        animations = ["idle"]
    
    audio_url = f"/audio/{os.path.basename(audio_file)}" if audio_file else None
    
    return {
        "text": response_text,
        "audio_url": audio_url,
        "animations": animations, # Return list
        "face_animation": face_animation # New field for blendshapes
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
        return {"input_text": None, "text": None, "audio_url": None, "animations": ["idle"]}
        
    print(f"Transcribed: {text}, Emotion: {emotion}")
    
    # Process
    response_text = process_input({"text": text, "emotion": emotion})
    
    # Generate Audio
    audio_file = speak(response_text, return_file=True)

    # Generate Face Animation using NVIDIA ACE
    face_animation = None
    if audio_file:
        face_animation = ace_client.process_audio(audio_file)
    
    # Determine animations (list)
    animations = []
    lower_resp = response_text.lower()
    
    if "hug" in lower_resp: animations.append("happy")
    if "dance" in lower_resp: animations.append("dance")
    if "happy" in lower_resp: animations.append("happy")
    if "sad" in lower_resp or "cry" in lower_resp: animations.append("sad")
    if "clap" in lower_resp: animations.append("clap")
    if "pray" in lower_resp: animations.append("pray")
    if "jump" in lower_resp: animations.append("jump")
    
    if not animations:
        animations = ["idle"]
    
    audio_url = f"/audio/{os.path.basename(audio_file)}" if audio_file else None
    
    return {
        "input_text": text,
        "input_emotion": emotion,
        "text": response_text,
        "audio_url": audio_url,
        "animations": animations,
        "face_animation": face_animation
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
