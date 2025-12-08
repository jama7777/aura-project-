export class GestureHandler {
    constructor(avatar) {
        this.avatar = avatar;
        this.hands = null;
        this.camera = null;
        this.videoElement = document.getElementById('user-camera');
        this.isActive = false;
        this.lastGesture = null;
        this.gestureCooldown = 0;
    }

    init() {
        this.hands = new Hands({
            locateFile: (file) => {
                return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
            }
        });

        this.hands.setOptions({
            maxNumHands: 1,
            modelComplexity: 1,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5
        });

        this.hands.onResults((results) => this.onResults(results));

        // Initialize Camera
        // Note: Camera starts when user clicks the camera button in main.js
    }

    start() {
        if (this.isActive) return;

        this.isActive = true;
        this.log("Gesture recognition started");
        this.processVideo();
    }

    stop() {
        if (!this.isActive) return;
        this.isActive = false;
        this.log("Gesture recognition stopped");
    }

    async processVideo() {
        if (!this.isActive) return;

        if (this.videoElement && this.videoElement.readyState >= 2) {
            try {
                await this.hands.send({ image: this.videoElement });
            } catch (error) {
                console.error("Hands send error:", error);
            }
        }

        if (this.isActive) {
            requestAnimationFrame(() => this.processVideo());
        }
    }

    log(msg) {
        console.log(msg);
        const debugDiv = document.getElementById('debug-console');
        if (debugDiv) {
            debugDiv.innerHTML += `<div>[Gesture] ${msg}</div>`;
            debugDiv.scrollTop = debugDiv.scrollHeight;
        }
    }

    onResults(results) {
        if (!results.multiHandLandmarks || results.multiHandLandmarks.length === 0) {
            return;
        }

        const landmarks = results.multiHandLandmarks[0];
        const gesture = this.detectGesture(landmarks);

        if (gesture && gesture !== this.lastGesture) {
            const now = Date.now();
            if (now - this.gestureCooldown > 1000) { // 1 second cooldown
                console.log(`Detected Gesture: ${gesture}`);
                this.triggerAction(gesture);
                this.lastGesture = gesture;
                this.gestureCooldown = now;
            }
        } else if (!gesture) {
            this.lastGesture = null;
        }
    }

    detectGesture(landmarks) {
        // Simple heuristic gesture detection

        // Finger states (Open/Closed)
        const thumbOpen = this.isThumbOpen(landmarks);
        const indexOpen = this.isFingerOpen(landmarks, 8);
        const middleOpen = this.isFingerOpen(landmarks, 12);
        const ringOpen = this.isFingerOpen(landmarks, 16);
        const pinkyOpen = this.isFingerOpen(landmarks, 20);

        const openFingersCount = [indexOpen, middleOpen, ringOpen, pinkyOpen].filter(Boolean).length;

        // Logic
        if (thumbOpen && openFingersCount === 4) {
            return 'open_palm'; // 5 fingers
        }

        if (!thumbOpen && openFingersCount === 0) {
            return 'fist'; // 0 fingers
        }

        if (indexOpen && middleOpen && !ringOpen && !pinkyOpen) {
            return 'victory'; // Peace sign
        }

        if (thumbOpen && openFingersCount === 0) {
            return 'thumbs_up';
        }

        // Thumbs down is harder with just landmarks relative to wrist without orientation, 
        // but we can check if thumb tip is below thumb IP joint and other fingers are closed.
        // For simplicity, let's stick to these 4 first.

        return null;
    }

    isFingerOpen(landmarks, tipIdx) {
        // Check if tip is higher (smaller y) than pip joint (tipIdx - 2)
        // This assumes hand is upright. For more robust detection, we need vector math.
        return landmarks[tipIdx].y < landmarks[tipIdx - 2].y;
    }

    isThumbOpen(landmarks) {
        // Check if thumb tip is to the side of the ip joint
        // Depending on hand (left/right), x comparison flips.
        // Simplified: Check distance between tip and pinky base (17) vs IP and pinky base.
        // If tip is further, it's open.

        const tip = landmarks[4];
        const ip = landmarks[3];
        const pinkyBase = landmarks[17];

        const distTip = Math.hypot(tip.x - pinkyBase.x, tip.y - pinkyBase.y);
        const distIp = Math.hypot(ip.x - pinkyBase.x, ip.y - pinkyBase.y);

        return distTip > distIp;
    }

    triggerAction(gesture) {
        switch (gesture) {
            case 'open_palm':
                this.avatar.playAnimation('clap', true);
                break;
            case 'victory':
                this.avatar.playAnimation('dance', true);
                break;
            case 'thumbs_up':
                this.avatar.playAnimation('happy', true);
                break;
            case 'fist':
                // Maybe stop or idle?
                this.avatar.playAnimation('idle');
                break;
        }
    }
}
