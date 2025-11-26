import cv2
from deepface import DeepFace
import threading
import time
import queue

# Global state for latest face emotion
latest_face_emotion = "neutral"
stop_vision = False

def vision_thread():
    global latest_face_emotion, stop_vision
    
    # Initialize webcam
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open webcam. Vision features disabled.")
            stop_vision = True
            return
    except Exception as e:
        print(f"Error initializing webcam: {e}")
        stop_vision = True
        return

    print("Vision thread started. Watching...")
    
    frame_count = 0
    
    while not stop_vision:
        ret, frame = cap.read()
        if not ret:
            continue
            
        # Analyze every 10th frame to save resources
        frame_count += 1
        if frame_count % 10 == 0:
            try:
                # DeepFace expects BGR, which OpenCV provides
                # enforce_detection=False allows it to return even if no face is confidently found (avoids crash)
                objs = DeepFace.analyze(img_path = frame, 
                                       actions = ['emotion'], 
                                       enforce_detection=False,
                                       silent=True)
                
                if objs and isinstance(objs, list):
                    # Get dominant emotion of the first face
                    emotion = objs[0]['dominant_emotion']
                    latest_face_emotion = emotion
                    # print(f"Face Emotion: {emotion}")
                
            except Exception as e:
                # print(f"Vision error: {e}")
                pass
        
        # Optional: Show video feed (might conflict with Pyglet if not handled carefully, 
        # but useful for debugging. For now, let's NOT show it to avoid UI conflicts)
        # cv2.imshow('AURA Vision', frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Test
    t = threading.Thread(target=vision_thread)
    t.start()
    try:
        while True:
            print(f"Latest: {latest_face_emotion}")
            time.sleep(1)
    except KeyboardInterrupt:
        stop_vision = True
        t.join()
