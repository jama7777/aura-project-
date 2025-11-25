# main.py - Entry point for AURA project
import threading
from src.perception.audio import input_queue, audio_thread
from src.core.brain import process_input
from src.output.tts import speak
import time
import sys

def text_input_thread():
    print("Text input ready. Type something and press Enter:")
    while True:
        try:
            text = sys.stdin.readline()
            if not text:
                break
            text = text.strip()
            if text:
                input_queue.put({"text": text, "emotion": "neutral"})
        except Exception as e:
            print(f"Error in text input: {e}")
            break

def main_loop():
    print("Starting AURA...")
    
    # Start audio thread
    t_audio = threading.Thread(target=audio_thread, daemon=True)
    t_audio.start()
    print("Audio perception started.")
    
    # Start text input thread
    t_text = threading.Thread(target=text_input_thread, daemon=True)
    t_text.start()
    
    last_input_time = time.time()
    
    try:
        while True:
            if not input_queue.empty():
                input_data = input_queue.get()
                print(f"Processing input: {input_data}")
                
                response = process_input(input_data)
                print(f"AURA Response: {response}")
                
                speak(response)
                last_input_time = time.time()
            
            # Idle chat trigger (every 5 mins)
            if time.time() - last_input_time > 300:
                print("Triggering idle chat...")
                speak("Hey, you seem quiet. Want to chat?")
                last_input_time = time.time()
            
            time.sleep(0.1) # Reduce CPU usage
            
    except KeyboardInterrupt:
        print("\nStopping AURA...")
        sys.exit(0)
    except Exception as e:
        print(f"Error in main loop: {e}")

if __name__ == "__main__":
    main_loop()