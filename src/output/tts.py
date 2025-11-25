from TTS.api import TTS
import os
import subprocess

# Initialize TTS model
try:
    # Using a faster/smaller model if possible, or stick to the one requested but handle errors
    tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)
    print("TTS model loaded.")
except Exception as e:
    print(f"Error loading TTS model: {e}")
    tts = None

def speak(text):
    if not tts:
        print(f"TTS not available. Text: {text}")
        return

    try:
        output_file = "output.wav"
        if os.path.exists(output_file):
            os.remove(output_file)
            
        tts.tts_to_file(text=text, file_path=output_file)
        
        # Play audio using afplay (macOS default)
        subprocess.run(["afplay", output_file])
    except Exception as e:
        print(f"Error in speak: {e}")