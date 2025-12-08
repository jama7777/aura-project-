
import { Avatar } from './avatar.js';
import { GestureHandler } from './gesture.js';

const avatar = new Avatar();
const gestureHandler = new GestureHandler(avatar);
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

document.addEventListener('DOMContentLoaded', () => {
    avatar.init();
    gestureHandler.init();
    setupEventListeners();
});

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

    // Mic Input
    micBtn.addEventListener('mousedown', startRecording);
    micBtn.addEventListener('mouseup', stopRecording);
    micBtn.addEventListener('touchstart', startRecording);
    micBtn.addEventListener('touchend', stopRecording);

    // Camera Toggle
    cameraBtn.addEventListener('click', toggleCamera);
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
            body: JSON.stringify({ text: text, emotion: 'neutral' })
        });

        const data = await response.json();
        handleResponse(data);
    } catch (error) {
        console.error('Error sending message:', error);
        addMessage("Error connecting to AURA.", 'aura');
    }
}

async function startRecording() {
    if (isRecording) return;

    try {
        log("Requesting microphone access...");
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
        log("Recording started...");
    } catch (err) {
        console.error("Error accessing microphone:", err);
        log(`Error accessing microphone: ${err.message}`);
    }
}

function stopRecording() {
    if (!isRecording) return;
    mediaRecorder.stop();
    isRecording = false;
    document.getElementById('mic-btn').classList.remove('active');
}

async function sendAudio() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
    const formData = new FormData();
    formData.append('file', audioBlob, 'input.wav');

    addMessage("🎤 Audio sent...", 'user');

    try {
        const response = await fetch('/api/audio', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (data.input_text) {
            // Update the last user message with transcribed text
            const lastMsg = document.querySelector('.message.user:last-child');
            if (lastMsg) lastMsg.textContent = data.input_text;
        }
        handleResponse(data);
    } catch (error) {
        console.error('Error sending audio:', error);
    }
}

function handleResponse(data) {
    addMessage(data.text, 'aura');

    // Play Audio
    if (data.audio_url) {
        log(`Playing audio: ${data.audio_url}`);
        const audio = new Audio(data.audio_url);

        audio.play().then(() => {
            log("Audio playback started.");
        }).catch(e => {
            log(`Audio playback failed: ${e.message}`);
        });

        // Lip sync (simple) / Talk animation
        // If we had a talk animation, we'd play it here.
        // For now, let's just ensure we are not in idle if we want movement
        // avatar.playAnimation('talk'); 

        audio.onended = () => {
            // Go back to idle when done talking
            avatar.playAnimation('idle');
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
    document.getElementById('current-emotion').textContent = emotionText;
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
    } else {
        // Start camera
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = cameraStream;
            video.classList.remove('hidden');
            btn.classList.add('active');
            gestureHandler.start();
        } catch (err) {
            console.error("Error accessing camera:", err);
        }
    }
}

