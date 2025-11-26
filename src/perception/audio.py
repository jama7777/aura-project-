import openwakeword
import pyaudio
import whisper
import torchaudio
import torch
# Monkeypatch torchaudio.list_audio_backends for speechbrain compatibility
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"] # Mock return

import speechbrain as sb
from speechbrain.inference.classifiers import EncoderClassifier
import threading
import queue
import numpy as np
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

input_queue = queue.Queue()
latest_audio_emotion = "neutral"

def audio_thread():
    try:
        # Check if aura.tflite exists, if not use a default or skip
        if os.path.exists("aura.tflite"):
            oww = openwakeword.Model(wakeword_models=["aura.tflite"])
        else:
            print("Warning: 'aura.tflite' not found. Using default 'alexa' for testing if available, or skipping wake word.")
            # For now, let's just use a simple threshold on volume or skip wake word for testing
            oww = None

        pa = pyaudio.PyAudio()
        audio_stream = pa.open(rate=16000, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=1280)
        print("Audio stream started. Listening...")

        while True:
            data = audio_stream.read(1280, exception_on_overflow=False)
            pcm = np.frombuffer(data, dtype=np.int16)
            
            # Wake word detection
            triggered = False
            if oww:
                prediction = oww.predict(pcm)
                if prediction.get("aura", 0) > 0.5:
                    triggered = True
            else:
                # Fallback: simple energy threshold for testing
                # Calculate RMS
                rms = np.sqrt(np.mean(pcm.astype(np.float32)**2))
                if rms > 1000: # Threshold
                    print(f"Sound detected (RMS: {rms:.2f}), triggering...")
                    triggered = True

            # For MVP, let's just record if we detect loud sound or if wake word triggered
            if triggered:
                print("Wake word detected! Recording...")
                frames = []
                for _ in range(0, int(16000 / 1280 * 5)):  # 5s recording
                    data = audio_stream.read(1280, exception_on_overflow=False)
                    frames.append(np.frombuffer(data, dtype=np.int16))
                
                audio_data = np.hstack(frames).astype(np.float32) / 32768.0
                
                text = ""
                if model:
                    result = model.transcribe(audio_data)
                    text = result["text"]
                
                # Audio Emotion
                audio_emotion = "neutral"
                if emotion_model:
                    try:
                        # Save to temp file for stable classification
                        temp_wav = "temp_emotion.wav"
                        import soundfile as sf
                        sf.write(temp_wav, audio_data, 16000)
                        
                        # Load manually to avoid torchcodec issues in classify_file
                        signal, fs = torchaudio.load(temp_wav)
                        
                        # Classify
                        # Use classify_file for simplicity as it handles loading correctly usually
                        # But since we have signal, let's try to fix classify_batch usage
                        # The error 'ModuleDict' object has no attribute 'compute_features' suggests internal issue.
                        # Let's try classify_file with the temp file.
                        emotion_out = emotion_model.classify_file(temp_wav)
                        # emotion_out is usually (out_prob, score, index, text_lab)
                        audio_emotion = emotion_out[3][0] 
                        
                        # Cleanup
                        if os.path.exists(temp_wav):
                            os.remove(temp_wav)
                            
                    except Exception as e_emo:
                        print(f"Audio Emotion classification failed: {e_emo}")
                        audio_emotion = "neutral"

                # Text Emotion
                text_emotion = "neutral"
                if text_emotion_classifier and text.strip():
                    try:
                        preds = text_emotion_classifier(text)
                        # Debug print
                        # print(f"Text Emotion Preds: {preds}")
                        # preds structure depends on pipeline, usually [{'label': 'joy', 'score': 0.9}] (list of dicts)
                        if isinstance(preds, list) and len(preds) > 0:
                            if isinstance(preds[0], dict):
                                text_emotion = preds[0].get('label', 'neutral')
                            elif isinstance(preds[0], list): # Nested list sometimes
                                if len(preds[0]) > 0 and isinstance(preds[0][0], dict):
                                    text_emotion = preds[0][0].get('label', 'neutral')
                        
                        print(f"Text Emotion Analysis: {text_emotion}")
                    except Exception as e:
                        print(f"Text emotion error: {e}")

                # Combine emotions
                # If text emotion is strong (not neutral), use it.
                # Or if audio emotion is neutral, use text emotion.
                final_emotion = audio_emotion
                if text_emotion != "neutral":
                    final_emotion = text_emotion
                
                # Update global state (to be accessed by API)
                global latest_audio_emotion
                latest_audio_emotion = final_emotion

                if text.strip():
                    input_queue.put({"text": text, "emotion": final_emotion})
                    print(f"Text: {text}, Emotion: {final_emotion} (Audio: {audio_emotion}, Text: {text_emotion})")
            
    except Exception as e:
        print(f"Error in audio thread: {e}")

if __name__ == "__main__":
    threading.Thread(target=audio_thread, daemon=True).start()
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")