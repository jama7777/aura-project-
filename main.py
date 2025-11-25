# main.py - Entry point for AURA project
import threading
from src.perception.audio import input_queue, audio_thread
from src.core.brain import process_input
from src.output.tts import speak
import time

def main_loop():
    threading.Thread(target=audio_thread).start()
    last_input_time = time.time()
    while True:
        if not input_queue.empty():
            input_data = input_queue.get()
            response = process_input(input_data)
            speak(response)
            last_input_time = time.time()
        if time.time() - last_input_time > 300:  # 5 min
            speak("Hey, you seem quiet. Want to chat?")
            last_input_time = time.time()
        time.sleep(1)

if __name__ == "__main__":
    main_loop()