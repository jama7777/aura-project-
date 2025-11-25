import openwakeword
import pyaudio
import whisper
import torchaudio
# Monkeypatch torchaudio.list_audio_backends for speechbrain compatibility
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"] # Mock return

import speechbrain as sb
from speechbrain.inference.classifiers import EncoderClassifier
import threading
import queue
import numpy as np
import os

# Initialize models
try:
    model = whisper.load_model("tiny")
    print("Whisper model loaded.")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    model = None

try:
    # Use the correct class for emotion recognition
    emotion_model = EncoderClassifier.from_hparams(
        source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
        savedir="pretrained_models/emotion_model"
    )
    print("Emotion model loaded.")
except Exception as e:
    print(f"Error loading Emotion model: {e}")
    emotion_model = None

input_queue = queue.Queue()

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
                if np.abs(pcm).mean() > 500: # Arbitrary threshold
                    # triggered = True # Too sensitive, let's rely on user input or just record chunks
                    pass

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
                
                emotion = "neutral"
                if emotion_model:
                    # SpeechBrain expects a tensor
                    import torch
                    signal = torch.tensor(audio_data).unsqueeze(0)
                    emotion_out = emotion_model.classify_batch(signal)
                    emotion = emotion_out[3][0] # Get the label

                if text.strip():
                    input_queue.put({"text": text, "emotion": emotion})
                    print(f"Text: {text}, Emotion: {emotion}")
            
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