import os
import sys
import threading
import time

if __name__ == "__main__":
    print("Select Task:")
    print("1. Audio Talk (Default)")
    print("2. Text Writing")
    print("3. Face Camera Talk")
    
    try:
        choice = input("Enter choice (1/2/3): ").strip()
    except EOFError:
        choice = "1"

    mode = "audio"
    if choice == "2":
        mode = "text"
    elif choice == "3":
        mode = "face"
    
    print(f"Starting in {mode} mode...")

    # Shared modules
    import src.perception.audio as audio_module
    from src.core.brain import process_input
    from src.output.tts import speak
    
    # Initialize Avatar
    # We will initialize it later or let it be handled by the main loop
    import src.output.avatar as avatar_module
    # avatar = Avatar()

    # Start Threads based on mode
    if mode == "audio" or mode == "face":
        # Load Audio Models
        from src.perception.audio import load_audio_models
        load_audio_models()
        
        # Load TTS
        from src.output.tts import load_tts_model
        load_tts_model()
        
        audio_thread = threading.Thread(target=audio_module.audio_thread, daemon=True)
        audio_thread.start()
        
    if mode == "face":
        # Start Vision Thread
        import src.perception.vision as vision_module
        # Vision thread handles its own loading but we can ensure it starts
        vision_thread = threading.Thread(target=vision_module.vision_thread, daemon=True)
        vision_thread.start()

    # Text Input Loop (if text mode) - Define it here so it's available for the thread start below
    if mode == "text":
        def text_input_loop():
            print("Type your message (or 'quit' to exit):")
            while True:
                try:
                    text = input("> ")
                    if text.lower() == "quit":
                        sys.exit(0)
                    if text.strip():
                        # We can also run text emotion analysis here if we want, 
                        # but audio_module has the classifier. 
                        # Let's use audio_module's classifier if available, or just pass neutral.
                        emotion = "neutral"
                        if audio_module.text_emotion_classifier:
                             try:
                                preds = audio_module.text_emotion_classifier(text)
                                emotion = preds[0]['label']
                             except:
                                 pass
                        
                        audio_module.input_queue.put({"text": text, "emotion": emotion})
                except EOFError:
                    break

        # Load Text Emotion Model
        from src.perception.audio import load_text_emotion_model
        load_text_emotion_model()
        
        # Load TTS
        from src.output.tts import load_tts_model
        load_tts_model()
        
        # Run text input in a separate thread so Pyglet can run in main
        text_thread = threading.Thread(target=text_input_loop, daemon=True)
        text_thread.start()

    # Brain Loop
    def brain_loop():
        print("Brain Loop Started...")
        while True:
            try:
                input_data = None
                
                # Input source depends on mode
                if mode == "text":
                    # For text mode, we block on user input in the main thread usually, 
                    # but here we are in a separate thread. 
                    # Actually, for text mode, we should probably run the input loop in the main thread 
                    # or a separate thread and put into queue.
                    # Let's use the queue for consistency.
                    if not audio_module.input_queue.empty():
                        input_data = audio_module.input_queue.get()
                else:
                    # Audio/Face mode
                    if not audio_module.input_queue.empty():
                        input_data = audio_module.input_queue.get()
                        
                        # If face mode, we can augment emotion with face emotion
                        if mode == "face":
                            face_emotion = vision_module.latest_face_emotion
                            if face_emotion != "neutral":
                                print(f"Augmenting with Face Emotion: {face_emotion}")
                                # Combine logic: maybe face overrides? or just log for now.
                                # Let's append it to text for Brain to know?
                                # Or update emotion if audio/text was neutral.
                                if input_data['emotion'] == "neutral":
                                    input_data['emotion'] = face_emotion
                
                if input_data:
                    print(f"Processing: {input_data}")
                    
                    # Process
                    response = process_input(input_data)
                    
                    # Trigger Animation
                    if avatar_module.instance:
                        lower_resp = response.lower()
                        if "hug" in lower_resp:
                            avatar_module.instance.set_animation("hug")
                        elif "dance" in lower_resp:
                            avatar_module.instance.set_animation("dance")
                        elif "happy" in lower_resp:
                            avatar_module.instance.set_animation("happy")
                        elif "sad" in lower_resp or "cry" in lower_resp:
                            avatar_module.instance.set_animation("sad")
                        else:
                            avatar_module.instance.set_animation("dance") # Default to dance for testing or idle
                    
                    # Speak
                    speak(response)
                    
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in brain loop: {e}")

    brain_thread = threading.Thread(target=brain_loop, daemon=True)
    brain_thread.start()

    # Text Input Loop (if text mode)
    if mode == "text":
        def text_input_loop():
            print("Type your message (or 'quit' to exit):")
            while True:
                try:
                    text = input("> ")
                    if text.lower() == "quit":
                        sys.exit(0)
                    if text.strip():
                        # We can also run text emotion analysis here if we want, 
                        # but audio_module has the classifier. 
                        # Let's use audio_module's classifier if available, or just pass neutral.
                        emotion = "neutral"
                        if audio_module.text_emotion_classifier:
                             try:
                                preds = audio_module.text_emotion_classifier(text)
                                emotion = preds[0]['label']
                             except:
                                 pass
                        
                        audio_module.input_queue.put({"text": text, "emotion": emotion})
                except EOFError:
                    break
        
        # Run text input in a separate thread so Pyglet can run in main
        text_thread = threading.Thread(target=text_input_loop, daemon=True)
        text_thread.start()

    # Run Panda3D App (Blocking)
    # Note: Panda3D usually needs to run in the main thread on macOS.
    from src.output.avatar import run_avatar
    run_avatar()