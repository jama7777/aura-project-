import openwakeword
import pyaudio
import whisper
import speechbrain as sb
import threading
import queue
import numpy as np

model = whisper.load_model("tiny")  # Local STT
emotion_model = sb.pretrained.EncoderClassifier.from_hparams(source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP", savedir="pretrained_models")

input_queue = queue.Queue()

def audio_thread():
    oww = openwakeword.Model(wakeword_models=["aura.tflite"])  # Download free model or train custom
    pa = pyaudio.PyAudio()
    audio_stream = pa.open(rate=16000, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=1280)
    
    while True:
        pcm = np.frombuffer(audio_stream.read(1280), dtype=np.int16)
        prediction = oww.predict(pcm)
        if prediction.get("aura", 0) > 0.5:  # Threshold for detection
            print("Wake word detected! Recording...")
            frames = []
            for _ in range(0, int(16000 / 1280 * 5)):  # 5s recording
                data = audio_stream.read(1280)
                frames.append(np.frombuffer(data, dtype=np.int16))
            audio_data = np.hstack(frames).astype(np.float32) / 32768.0
            
            text = model.transcribe(audio_data)["text"]
            emotion = emotion_model.classify_vector(emotion_model.encode_batch(audio_data))[0]
            
            input_queue.put({"text": text, "emotion": emotion})
            print(f"Text: {text}, Emotion: {emotion}")

if __name__ == "__main__":
    threading.Thread(target=audio_thread, daemon=True).start()
    while True:
        pass