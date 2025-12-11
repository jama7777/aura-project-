import whisper
import torchaudio
import torch

# Monkeypatch torchaudio.list_audio_backends for speechbrain compatibility
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"] # Mock return

import speechbrain as sb
from speechbrain.inference.classifiers import EncoderClassifier
import os
from transformers import pipeline

# Global model variables
model = None
emotion_model = None
text_emotion_classifier = None

def load_audio_models():
    global model, emotion_model
    if model is None:
        try:
            print("Loading Whisper model (tiny)...")
            model = whisper.load_model("tiny")
            print("Whisper model loaded.")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            model = None


    if emotion_model is None:
        try:
            print("Loading Audio Emotion model (Transformers)...")
            from transformers import pipeline
            # Use a robust model from HuggingFace
            emotion_model = pipeline("audio-classification", model="superb/wav2vec2-base-superb-er")
            print("Audio Emotion model loaded (Transformers).")
        except Exception as e:
            print(f"Error loading Audio Emotion model: {e}")
            emotion_model = None

def load_text_emotion_model():
    global text_emotion_classifier
    if text_emotion_classifier is None:
        try:
            print("Loading text emotion model...")
            text_emotion_classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", top_k=1)
            print("Text emotion model loaded.")
        except Exception as e:
            print(f"Error loading Text Emotion model: {e}")
            text_emotion_classifier = None

def transcribe_audio_file(file_path):
    global model
    if model is None:
        load_audio_models()
    
    if model:
        try:
            result = model.transcribe(file_path)
            return result["text"]
        except Exception as e:
            print(f"Error transcribing file: {e}")
            return ""
    return ""

def analyze_emotion_file(file_path):
    global emotion_model
    if emotion_model is None:
        load_audio_models()
        
    if emotion_model:
        try:
            # Classify using Transformers Pipeline
            # Returns list of dicts: [{'score': 0.9, 'label': 'neutral'}, ...]
            preds = emotion_model(file_path)
            # Get top prediction
            top_pred = preds[0]
            label = top_pred['label']
            
            # Map labels if needed (Superb model uses abbreviations)
            label_map = {
                "neu": "neutral",
                "hap": "happy",
                "ang": "angry",
                "sad": "sad",
            }
            return label_map.get(label, label)
        except Exception as e:
            print(f"Audio Emotion classification failed: {e}")
            return "neutral"
    return "neutral"