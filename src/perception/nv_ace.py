import os
import grpc
import time
import numpy as np

# Note: In a real implementation, you would need the generated protobuf classes 
# from NVIDIA ACE (e.g. nvidia_ace.audio2face.v1_pb2).
# Since these are not publicly available in a simple pip package, we will
# structure this client to be easily pluggable once those files are generated.
# For now, we will simulate the connection or use a generic structure.

class NvidiaACEClient:
    def __init__(self, api_key=None, url="grpc.nvcf.nvidia.com:443", function_id=None):
        self.api_key = api_key or os.getenv("NV_API_KEY")
        self.url = url
        self.function_id = function_id or "760ca5ed-e18e-4f51-8763-7935df626c9f" # Example Audio2Face Function ID
        self.channel = None
        self.stub = None
        
        if not self.api_key:
            print("WARNING: NV_API_KEY is not set. serialization will fail.")

    def connect(self):
        if not self.api_key:
            return False
            
        try:
            creds = grpc.ssl_channel_credentials()
            call_creds = grpc.metadata_call_credentials(
                lambda context, callback: callback((("authorization", f"Bearer {self.api_key}"),), None)
            )
            composite_creds = grpc.composite_channel_credentials(creds, call_creds)
            self.channel = grpc.secure_channel(self.url, composite_creds)
            
            # self.stub = A2FStub(self.channel) # Requires generated proto
            print(f"Connected to NVIDIA ACE at {self.url}")
            return True
        except Exception as e:
            print(f"Failed to connect to NVIDIA ACE: {e}")
            return False

    def process_audio(self, audio_file_path):
        """
        Sends audio to ACE and returns animation data.
        Returns a dictionary or list of blendshape frames.
        """
        if not self.channel:
            if not self.connect():
                print("NVIDIA ACE not connected. Returning empty animation.")
                return None

        print(f"Sending {audio_file_path} to NVIDIA ACE...")
        
        # Mock Response for now since we don't have the real protos generated in this environment
        # In a real scenario, this would yield frames from a response stream
        
        # Simulating processing delay
        # time.sleep(0.5)
        
        # Mock Blendshapes (Basic ARKit 52 subset)
        # We will generate a fake wave of 'jawOpen' synchronized with file duration
        try:
            # Get duration
            import wave
            with wave.open(audio_file_path, 'rb') as wf:
                duration = wf.getnframes() / wf.getframerate()
            
            fps = 60
            total_frames = int(duration * fps)
            animations = []
            
            for i in range(total_frames):
                # Simple sine wave for jaw movement to simulate talking
                jaw_open = abs(np.sin(i * 0.2)) * 0.8
                
                frame = {
                    "time": i / fps,
                    "blendshapes": {
                        "jawOpen": float(jaw_open),
                        "mouthSmile": 0.1
                    }
                }
                animations.append(frame)
                
            print(f"Generated {len(animations)} frames of mock animation data.")
            return animations
            
        except Exception as e:
            print(f"Error processing audio for ACE: {e}")
            return None

# Singleton instance
ace_client = NvidiaACEClient()
