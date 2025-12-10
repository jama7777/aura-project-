import { Avatar } from './avatar.js';
import { GestureHandler } from './gesture.js';

const avatar = new Avatar();
let currentEmotion = "neutral";

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
        await faceapi.nets.tinyFaceDetector.loadFromUri('/assets/models');
        await faceapi.nets.faceExpressionNet.loadFromUri('/assets/models');
        log("Face API models loaded.");
    } catch (e) {
        log("Error loading Face API models. Make sure /assets/models exists or use CDN models.");
        // Fallback or retry? For now, we assume user might need to download models.
        // Actually, face-api needs model files. We can try to load from a public URL if local fails?
        // Let's try loading from a public CDN if local 404s, but face-api usually expects a directory.
        // For this task, strict Web UI requirement, we might not have models locally.
        // I'll assume we need to point to a CDN or user needs to put models in folders.
        // Strategy: Use CDN base URL for models.
        try {
            const modelUrl = 'https://justadudewhohacks.github.io/face-api.js/models';
            await faceapi.nets.tinyFaceDetector.loadFromUri(modelUrl);
            await faceapi.nets.faceExpressionNet.loadFromUri(modelUrl);
            log("Face API models loaded from CDN.");
        } catch (err) {
            log(`Failed to load Face Models: ${err}`);
            addMessage("⚠️ Face API failed to load. Emotion detection disabled.", 'aura');
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
    micBtn.addEventListener('click', toggleRecording);

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


function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

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

async function startRecording() {
    if (isRecording) return;

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
            const volume = dataArray.reduce((a, b) => a + b) / dataArray.length;

            // Thresholds - Adjusted for better sensitivity
            const speakThreshold = 20; // Slightly increased to avoid noise
            const silenceThreshold = 10;

            if (volume > speakThreshold) {
                if (!isSpeaking) {
                    isSpeaking = true;
                    log("Voice detected... (User Speaking)");
                    document.getElementById('mic-btn').classList.add('speaking');
                }
                silenceStart = Date.now();
            } else if (volume < silenceThreshold) {
                // Wait for 2.0s silence to be sure user is done
                if (isSpeaking && (Date.now() - silenceStart > 2000)) {
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
        }).catch(e => {
            log(`Audio playback failed: ${e.message}`);
        });

        audio.onended = () => {
            avatar.setTalking(false);
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
                startRecording();
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
                avatar.playAnimation('idle');
            });
        }
    } else if (data.animation && data.animation !== 'talk') {
        // Fallback for old API
        avatar.playAnimation(data.animation, true);
    }

    // Update emotion UI
    const emotionText = (data.animations && data.animations.length > 0) ? data.animations.join(", ") : (data.animation || "Neutral");
    // Don't overwrite current-emotion with response emotion, 
    // we want to show USER emotion there? 
    // Actually the UI says "Emotion: [Neutral]" usually refers to the User's detected emotion or Avatar's state?
    // In status bar: "Emotion: Neutral". Let's stick to showing USER's detected emotion live.
    // So we DON'T update it from response data here.
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
        if (!video || video.paused || video.ended) return;

        // Detect emotions
        // tinyFaceDetector is faster/lighter
        try {
            const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions())
                .withFaceExpressions();

            if (detections && detections.length > 0) {
                // Get dominant emotion
                const expressions = detections[0].expressions;
                const sorted = Object.entries(expressions).sort((a, b) => b[1] - a[1]);
                const dominant = sorted[0];

                if (dominant[1] > 0.5) { // Threshold
                    currentEmotion = dominant[0];
                    statusSpan.textContent = currentEmotion.charAt(0).toUpperCase() + currentEmotion.slice(1);
                }
            }
        } catch (e) {
            // console.warn("Face detection error:", e);
        }

    }, 500); // Check every 500ms
}

function stopFaceDetection() {
    if (faceInterval) clearInterval(faceInterval);
}
