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
            model = whisper.load_model("tiny")
            print("Whisper model loaded.")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            model = None

    if emotion_model is None:
        try:
            # Use the correct class for emotion recognition
            emotion_model = EncoderClassifier.from_hparams(
                source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
                savedir="pretrained_models/emotion_model"
            )
            print("Audio Emotion model loaded.")
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
            # Classify
            emotion_out = emotion_model.classify_file(file_path)
            # emotion_out is usually (out_prob, score, index, text_lab)
            return emotion_out[3][0]
        except Exception as e:
            print(f"Audio Emotion classification failed: {e}")
            return "neutral"
    return "neutral"