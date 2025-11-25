from TTS.api import TTS

tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)  # Free model, download once

def speak(text):
    tts.tts_to_file(text=text, file_path="output.wav")
    # Play audio (use playsound or similar; pip install playsound if needed)
    from playsound import playsound
    playsound("output.wav")