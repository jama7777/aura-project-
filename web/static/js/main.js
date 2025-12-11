import { Avatar } from './avatar.js';
import { GestureHandler } from './gesture.js';

const avatar = new Avatar();
let currentEmotion = "neutral";
// Emotion Trigger State
let lastTriggeredEmotion = null;
let emotionStartTime = 0;
let emotionCooldown = 0;

const gestureHandler = new GestureHandler(avatar, (gesture) => {
    // Send gesture to backend
    log(`Sending gesture: ${gesture} (Emotion: ${currentEmotion})`);
    addMessage(`(Gesture: ${gesture})`, 'user');
    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: "", emotion: currentEmotion, gesture: gesture })
    })
        .then(res => res.json())
        .then(data => handleResponse(data))
        .catch(err => console.error("Error sending gesture:", err));
});
let isRecording = false;
let mediaRecorder;
let audioChunks = [];

function log(msg) {
    console.log(msg);
    const debugDiv = document.getElementById('debug-console');
    if (debugDiv) {
        debugDiv.innerHTML += `<div>[Main] ${msg}</div>`;
        debugDiv.scrollTop = debugDiv.scrollHeight;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    // SECURITY CHECK: Navigator.mediaDevices is undefined in insecure contexts (non-localhost HTTP)
    if (location.hostname !== 'localhost' && location.hostname !== '127.0.0.1' && location.protocol !== 'https:') {
        const warning = "⚠️ SECURITY RESTRICTION: Camera & Mic are BLOCKED by browsers on non-HTTPS connections (except localhost). Please access this site via http://localhost:8000 on this machine.";
        log(warning);
        addMessage(warning, 'aura');
        alert(warning);
        // Disable buttons
        document.getElementById('mic-btn').disabled = true;
        document.getElementById('camera-btn').disabled = true;
        document.getElementById('mic-btn').style.opacity = '0.5';
        document.getElementById('camera-btn').style.opacity = '0.5';
        return;
    }

    avatar.init();

    // Initialize Face API
    await loadFaceAPI();

    // Initialize Gesture Handler (waits for camera)
    gestureHandler.init();

    setupEventListeners();
});

async function loadFaceAPI() {
    log("Loading Face API models...");
    try {
        log("Loading Face API models...");
        // Tuning for High Accuracy: Using SSD MobileNet V1
        // This model is slower but much more accurate than TinyFaceDetector
        await faceapi.nets.ssdMobilenetv1.loadFromUri('/assets/models');
        await faceapi.nets.faceExpressionNet.loadFromUri('/assets/models');
        log("Face API models (SSD MobileNet V1) loaded successfully.");
    } catch (e) {
        log("Local models not found, attempting CDN fallback...");
        try {
            const modelUrl = 'https://justadudewhohacks.github.io/face-api.js/models';
            await faceapi.nets.ssdMobilenetv1.loadFromUri(modelUrl);
            await faceapi.nets.faceExpressionNet.loadFromUri(modelUrl);
            log("Face API models (SSD MobileNet V1) loaded from CDN.");
        } catch (err) {
            console.error("Face API Error:", err);
            log(`Failed to load Face Models: ${err.message}`);
            addMessage("⚠️ Face detection disabled (Models failed to load).", 'aura');
        }
    }
}

function setupEventListeners() {
    const textInput = document.getElementById('text-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');
    const cameraBtn = document.getElementById('camera-btn');

    // Text Input
    textInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    sendBtn.addEventListener('click', sendMessage);

    // Mic Input - TOGGLE Mode
    micBtn.addEventListener('click', toggleMicrophone);

    // Camera Toggle
    cameraBtn.addEventListener('click', toggleCamera);

    // Gesture Control
    const gestureBtn = document.getElementById('gesture-btn');
    const gestureMenu = document.getElementById('gesture-menu');

    gestureBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        gestureMenu.classList.toggle('hidden');
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!gestureBtn.contains(e.target) && !gestureMenu.contains(e.target)) {
            gestureMenu.classList.add('hidden');
        }
    });

    // Gesture Options
    document.querySelectorAll('.gesture-option-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const gesture = btn.dataset.gesture;
            triggerManualGesture(gesture);
            gestureMenu.classList.add('hidden');
        });
    });
}

function triggerManualGesture(gesture) {
    log(`Manual/Body Gesture Triggered: ${gesture}`);

    // 1. Play animation locally immediately for feedback
    // Mapping gesture to animation
    // 'wave' -> we don't have wave animation code in gesture.js, but let's see server.py...
    // Server has: hug, dance, happy, sad, clap, pray, jump.
    // 'wave' -> maybe mapping to 'talk' or we need to add 'tier1' animations if available in avatar.
    // For now, allow server to decide or simple mapping.

    // We send to server as gesture, brain.py handles it.

    addMessage(`(Gesture: ${gesture})`, 'user');

    // Check audio context just in case (interaction requirement)
    if (audioContext && audioContext.state === 'suspended') {
        audioContext.resume();
    }

    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: "", emotion: currentEmotion, gesture: gesture })
    })
        .then(res => res.json())
        .then(data => handleResponse(data))
        .catch(err => console.error("Error sending gesture:", err));
}


// toggleRecording removed - used toggleMicrophone instead


async function sendMessage() {
    const input = document.getElementById('text-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    input.value = '';

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, emotion: currentEmotion })
        });

        const data = await response.json();
        handleResponse(data);
    } catch (error) {
        console.error('Error sending message:', error);
        addMessage("Error connecting to AURA.", 'aura');
    }
}

let audioContext;
let analyser;
let microphone;
let silenceStart = Date.now();
let isSpeaking = false;
let vadInterval;

async function toggleMicrophone() {
    if (isRecording) {
        log("Manual stop requested. Sending audio...");
        stopRecording();
        return;
    }

    try {
        log("Requesting microphone access...");
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error("Browser API navigator.mediaDevices.getUserMedia not available");
        }

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        log("Microphone access granted.");

        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = sendAudio;

        mediaRecorder.start();
        isRecording = true;
        document.getElementById('mic-btn').classList.add('active');
        log("Listening...");

        // VAD Setup
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }

        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        microphone = audioContext.createMediaStreamSource(stream);
        microphone.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);

        // VAD Loop
        clearInterval(vadInterval);
        vadInterval = setInterval(() => {
            analyser.getByteFrequencyData(dataArray);
            analyser.getByteFrequencyData(dataArray);
            const volume = dataArray.reduce((a, b) => a + b) / dataArray.length;

            // Debug Volume Visual
            // log(`Vol: ${volume.toFixed(1)}`); // Spammy, but helpful if user opens console.
            const micBtn = document.getElementById('mic-btn');
            if (volume > 5) {
                micBtn.style.boxShadow = `0 0 ${volume}px #00ff00`; // Glow based on volume
            } else {
                micBtn.style.boxShadow = 'none';
            }

            // Thresholds - Adjusted for better sensitivity
            const speakThreshold = 25; // Increased to avoid background noise triggering (was 10)
            const silenceThreshold = 5; // Lowered (was 8)

            if (volume > speakThreshold) {
                if (!isSpeaking) {
                    isSpeaking = true;
                    log("Voice detected... (User Speaking)");
                    document.getElementById('mic-btn').classList.add('speaking');
                    // Add visual pulse or indicator if possible
                }
                silenceStart = Date.now();
            } else if (volume < silenceThreshold) {
                // Wait for 2.5s silence to be sure user is done
                if (isSpeaking && (Date.now() - silenceStart > 2500)) {
                    log("Silence detected. Sending audio...");
                    stopRecording();
                }
            }
        }, 100);

    } catch (err) {
        console.error("Error accessing microphone:", err);
        log(`Error accessing microphone: ${err.message}`);
        addMessage("⚠️ Microphone error. Check permissions or use HTTPS/Localhost.", 'aura');
    }
}

function stopRecording() {
    if (!isRecording) return;
    clearInterval(vadInterval);
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    isRecording = false;
    isSpeaking = false;
    document.getElementById('mic-btn').classList.remove('active');
    document.getElementById('mic-btn').classList.remove('speaking');

    // Stop tracks to release mic
    if (mediaRecorder && mediaRecorder.stream) {
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
}

async function sendAudio() {
    if (audioChunks.length === 0) return;

    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
    const formData = new FormData();
    formData.append('file', audioBlob, 'input.wav');

    // addMessage("🎤 Processing...", 'user'); 

    try {
        const response = await fetch('/api/audio', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (data.input_text) {
            // Update UI with what was heard
            addMessage(data.input_text + ` (${data.input_emotion || currentEmotion})`, 'user');
        }

        if (data.text) {
            handleResponse(data);
        }
    } catch (error) {
        console.error('Error sending audio:', error);
    }
}

function handleResponse(data) {
    addMessage(data.text, 'aura');

    // Play Audio
    if (data.audio_url) {
        // Stop currently playing audio if any
        if (window.currentAudio) {
            window.currentAudio.pause();
            window.currentAudio = null;
        }

        log(`Playing audio: ${data.audio_url}`);
        const audio = new Audio(data.audio_url);
        window.currentAudio = audio; // Track it

        audio.play().then(() => {
            // log("Audio playback started.");
            avatar.setTalking(true);

            // Sync Face Animation
            if (data.face_animation) {
                log(`Starting Face Animation (${data.face_animation.length} frames)`);
                startFaceSync(audio, data.face_animation);
            }

        }).catch(e => {
            log(`Audio playback failed: ${e.message}`);
        });

        audio.onended = () => {
            avatar.setTalking(false);
            stopFaceSync();
            avatar.playAnimation('idle');
            window.currentAudio = null;
            // Loop functionality: If "Always On", maybe restart listening?
            // For now, user has to click to start loop again or we can auto-restart.
            // But strict "Google Meet" implies we stay listening.
            // Let's AUTO-RESTART listening for "Always On" feel if the mic was active?
            // Actually, best "Google Meet" UX is: Microphone stays open.
            // But we stopped recording to send. So we should restart recording now.
            // HOWEVER, playing audio while recording causes echo.
            // So we restart recording AFTER audio finishes.
            // Auto-restart listening loop (Google Meet style)
            // Wait a moment before listening to avoid self-triggering from echo
            setTimeout(() => {
                log("Auto-restarting listener...");
                toggleMicrophone(); // Changed from startRecording()
            }, 500);
        };
    }

    // Animation based on emotion/keywords
    if (data.animations && data.animations.length > 0) {
        // If it's just one and it's 'talk', we might want to ignore it if we handle lip sync separately
        // But for now, let's play the sequence.
        // If the sequence contains 'talk', we might want to skip it or handle it differently?
        // Let's filter out 'talk' if we have other animations, or just play it.

        const anims = data.animations.filter(a => a !== 'talk');

        if (anims.length > 0) {
            avatar.playSequence(anims, () => {
                // Only return to idle if not talking
                if (window.currentAudio && !window.currentAudio.paused) {
                    // do nothing, let talk continue
                } else {
                    avatar.playAnimation('idle');
                }
            });
        }
    } else if (data.animation && data.animation !== 'talk') {
        // Fallback for old API
        avatar.playAnimation(data.animation, true);
    }
}

let faceSyncInterval;
function startFaceSync(audio, frames) {
    if (faceSyncInterval) clearInterval(faceSyncInterval);

    // Sort frames by time just in case
    // frames.sort((a, b) => a.time - b.time);

    // Use requestAnimationFrame for smoother look? 
    // Or setInterval aligned to fps (e.g. 60fps = 16ms)

    faceSyncInterval = setInterval(() => {
        if (!audio || audio.paused || audio.ended) {
            stopFaceSync();
            return;
        }

        const currentTime = audio.currentTime;

        // Find the frame closest to current time
        // Optimization: track last index to avoid full search
        const frame = frames.find(f => Math.abs(f.time - currentTime) < 0.05); // 50ms window

        if (frame) {
            avatar.updateFace(frame.blendshapes);
        }

    }, 16); // ~60fps
}

function stopFaceSync() {
    if (faceSyncInterval) clearInterval(faceSyncInterval);
    if (window.avatar) window.avatar.resetFace();
}


function addMessage(text, sender) {
    const history = document.getElementById('chat-history');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender} `;
    msgDiv.textContent = text;
    history.appendChild(msgDiv);

    // Scroll to bottom
    const container = document.getElementById('chat-container');
    container.scrollTop = container.scrollHeight;
}

let cameraStream = null;
async function toggleCamera() {
    const video = document.getElementById('user-camera');
    const btn = document.getElementById('camera-btn');

    if (cameraStream) {
        // Stop camera
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
        video.srcObject = null;
        video.classList.add('hidden');
        btn.classList.remove('active');
        gestureHandler.stop();
        stopFaceDetection();
    } else {
        // Start camera
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = cameraStream;
            video.classList.remove('hidden');
            btn.classList.add('active');

            // Wait for video to play
            video.onloadedmetadata = () => {
                video.play();
                gestureHandler.start();
                startFaceDetection(video);
            };
        } catch (err) {
            console.error("Error accessing camera:", err);
            log(`Error accessing camera: ${err.message}`);
        }
    }
}

let faceInterval;
function startFaceDetection(video) {
    const statusSpan = document.getElementById('current-emotion');

    faceInterval = setInterval(async () => {
        if (!video || video.paused || video.ended || video.readyState < 2) return;

        // Detect emotions
        // Tuning: inputSize 320 (lighter/faster), scoreThreshold 0.2 (very sensitive)
        // This is a "Catch All" mode to debug if detection works at all.
        const options = new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.2 });

        try {
            const detections = await faceapi.detectAllFaces(video, options).withFaceExpressions();

            if (detections && detections.length > 0) {
                // Visual Feedback
                video.style.border = "3px solid #00ff00";
                video.style.boxShadow = "0 0 20px #00ff00";

                // Get dominant emotion
                const expressions = detections[0].expressions;
                const sorted = Object.entries(expressions).sort((a, b) => b[1] - a[1]);
                const dominant = sorted[0];

                // Debug log occasionally
                // if (Math.random() < 0.1) log(`Face detected: ${dominant[0]} (${(dominant[1]*100).toFixed(0)}%)`);

                if (dominant[1] > 0.2) { // Extremely low threshold for debugging
                    currentEmotion = dominant[0];
                    statusSpan.textContent = currentEmotion.charAt(0).toUpperCase() + currentEmotion.slice(1) + ` (${(dominant[1] * 100).toFixed(0)}%)`;
                    statusSpan.style.color = "#00ff00";

                    // Auto-Trigger Logic
                    const now = Date.now();
                    // Ignore neutral and ensure cooldown (5s) passed (was 15s)
                    if (currentEmotion !== 'neutral' && (now - emotionCooldown > 5000)) {
                        if (currentEmotion === lastTriggeredEmotion) {
                            // Sustained check
                            if (now - emotionStartTime > 1000) { // Held for 1 second (was 2s)
                                log(`Emotion Sustained (${currentEmotion}) - Triggering Reaction!`);
                                triggerEmotionReaction(currentEmotion);
                                emotionCooldown = now;
                                lastTriggeredEmotion = null; // Reset to avoid double trigger
                            }
                        } else {
                            // New emotion started
                            lastTriggeredEmotion = currentEmotion;
                            emotionStartTime = now;
                        }
                    } else if (currentEmotion !== lastTriggeredEmotion) {
                        // Reset tracker if emotion changes
                        lastTriggeredEmotion = currentEmotion;
                        emotionStartTime = now;
                    }

                } else {
                    lastTriggeredEmotion = null; // Reset if confidence drops
                    statusSpan.style.color = "#aaa";
                }
            } else {
                video.style.border = "2px solid #333";
                video.style.boxShadow = "none";
                if (Math.random() < 0.05) log("No face detected (Check lighting/angle)");
            }
        } catch (e) {
            console.warn("Face detection error:", e);
        }

    }, 500); // Check every 500ms
}

function triggerEmotionReaction(emotion) {
    addMessage(`(Emotion Detected: ${emotion})`, 'user');

    // Play sound or visual feedback?
    // For now just console log and send

    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: "", emotion: emotion, gesture: "none" })
    })
        .then(res => res.json())
        .then(data => handleResponse(data))
        .catch(err => console.error("Error triggering emotion:", err));
}

function stopFaceDetection() {
    if (faceInterval) clearInterval(faceInterval);
}
