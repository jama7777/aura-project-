import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class Avatar {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.mixer = null;
        this.animations = {};
        this.currentAction = null;
        this.clock = new THREE.Clock();
        this.isTalking = false;
        this.debugDiv = null;
    }

    log(msg) {
        console.log(msg);
        if (this.debugDiv) {
            this.debugDiv.innerHTML += `<div>${msg}</div>`;
            this.debugDiv.scrollTop = this.debugDiv.scrollHeight;
        }
    }

    init() {
        // Create Debug UI
        this.debugDiv = document.createElement('div');
        this.debugDiv.id = 'debug-console'; // Added ID for testing
        this.debugDiv.style.position = 'absolute';
        this.debugDiv.style.top = '10px';
        this.debugDiv.style.left = '10px';
        this.debugDiv.style.color = 'yellow';
        this.debugDiv.style.fontFamily = 'monospace';
        this.debugDiv.style.zIndex = '1000';
        this.debugDiv.style.background = 'rgba(0,0,0,0.5)';
        this.debugDiv.style.padding = '10px';
        this.debugDiv.style.maxHeight = '200px';
        this.debugDiv.style.overflowY = 'auto';
        document.body.appendChild(this.debugDiv);

        this.log("Initializing 3D Scene...");

        const container = document.getElementById('canvas-container');

        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x111111);
        this.scene.fog = new THREE.Fog(0x111111, 200, 1000);

        // Camera
        this.camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 2000);
        this.camera.position.set(0, 150, 400);

        // Lights
        const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 1.5);
        hemiLight.position.set(0, 200, 0);
        this.scene.add(hemiLight);

        const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
        dirLight.position.set(0, 200, 100);
        dirLight.castShadow = true;
        this.scene.add(dirLight);

        // Ground
        const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000), new THREE.MeshPhongMaterial({ color: 0x999999, depthWrite: false }));
        mesh.rotation.x = - Math.PI / 2;
        mesh.receiveShadow = true;
        this.scene.add(mesh);

        const grid = new THREE.GridHelper(2000, 20, 0x000000, 0x000000);
        grid.material.opacity = 0.2;
        grid.material.transparent = true;
        this.scene.add(grid);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.shadowMap.enabled = true;
        container.appendChild(this.renderer.domElement);

        // Controls
        const controls = new OrbitControls(this.camera, this.renderer.domElement);
        controls.target.set(0, 100, 0);
        controls.update();

        // Load Model
        this.loadModel();

        // Resize Event
        window.addEventListener('resize', () => this.onWindowResize());

        // Animation Loop
        this.animate();
    }

    loadModel() {
        const loadingManager = new THREE.LoadingManager();

        loadingManager.onLoad = () => {
            console.log('Loading complete!');
            this.log('Loading complete!');
            // Hide loading indicator if we had one

            // Start Intro Sequence
            this.playIntroSequence();
        };

        const modelLoader = new FBXLoader(loadingManager);

        // Load Character
        // Using Hip Hop Dancing.fbx as base because character.fbx is too old (v6100)
        this.log("Starting model load: /assets/animations/Hip Hop Dancing.fbx");
        modelLoader.load('/assets/animations/Hip Hop Dancing.fbx', (object) => {
            this.log("Model loaded successfully!");
            this.mixer = new THREE.AnimationMixer(object);

            // Rename the default animation to 'dance'
            if (object.animations && object.animations.length > 0) {
                object.animations[0].name = 'dance';
                this.cleanAnimationClips(object.animations[0]);
            }

            object.traverse((child) => {
                if (child.isMesh) {
                    child.castShadow = true;
                    child.receiveShadow = true;
                    // Ensure material is visible
                    if (child.material) {
                        child.material.side = THREE.DoubleSide;
                        child.material.needsUpdate = true;
                    }
                }
            });

            // Auto-scale
            const box = new THREE.Box3().setFromObject(object);
            const size = box.getSize(new THREE.Vector3());
            this.log(`Model Size: ${size.x.toFixed(2)}, ${size.y.toFixed(2)}, ${size.z.toFixed(2)}`);

            const maxDim = Math.max(size.x, size.y, size.z);
            if (maxDim === 0) {
                this.log("ERROR: Model has 0 size!");
            } else {
                const scale = 150 / maxDim;
                object.scale.set(scale, scale, scale);
                this.log(`Applied Scale: ${scale.toFixed(4)}`);
            }

            // Center it
            object.position.y = 0;

            this.scene.add(object);
            this.model = object; // Save reference

            // Load Animations
            this.loadAnimations(modelLoader);

        }, (xhr) => {
            if (xhr.total > 0) {
                const percent = (xhr.loaded / xhr.total * 100).toFixed(0);
                // this.log(`Loading: ${percent}%`);
            }
        }, (error) => {
            this.log(`ERROR loading model: ${error.message || error}`);
            console.error('An error happened loading model:', error);
        });
    }

    loadAnimations(loader) {
        const anims = [
            { name: 'dance', path: '/assets/animations/Hip Hop Dancing.fbx' },
            { name: 'idle', path: '/assets/animations/Catwalk Walk Turn 180 Tight.fbx' }, // Catwalk is IDLE
            { name: 'happy', path: '/assets/animations/Sitting Laughing.fbx' },
            { name: 'sad', path: '/assets/animations/Defeated.fbx' },
            { name: 'jump', path: '/assets/animations/Jumping Down.fbx' },
            { name: 'pray', path: '/assets/animations/Praying.fbx' },
            { name: 'crouch', path: '/assets/animations/Crouch To Stand.fbx' },
            { name: 'clap', path: '/assets/animations/Clapping.fbx' }
        ];

        anims.forEach(anim => {
            loader.load(anim.path, (object) => {
                if (object.animations && object.animations.length > 0) {
                    const clip = object.animations[0];
                    clip.name = anim.name; // Rename clip
                    this.cleanAnimationClips(clip);
                    const action = this.mixer.clipAction(clip);
                    this.animations[anim.name] = action;
                }
            });
        });
    }

    playAnimation(name, loopOnce = false) {
        if (!this.mixer) return;

        // Fallback
        if (!this.animations[name]) {
            console.warn(`Animation ${name} not found.`);
            return;
        }

        const action = this.animations[name];
        if (this.currentAction !== action) {
            if (this.currentAction) this.currentAction.fadeOut(0.5);

            action.reset().fadeIn(0.5);
            action.clampWhenFinished = true;

            if (loopOnce) {
                action.setLoop(THREE.LoopOnce);
                // When finished, go back to idle
                this.mixer.addEventListener('finished', (e) => {
                    if (e.action === action) {
                        this.playAnimation('idle');
                    }
                });
            } else {
                action.setLoop(THREE.LoopRepeat);
            }

            action.play();
            this.currentAction = action;
        }
    }

    playIntroSequence() {
        this.log("Playing Intro Sequence...");
        const sequence = ['dance', 'happy', 'sad', 'jump', 'pray', 'clap'];
        this.playSequence(sequence, () => {
            this.log("Intro complete. Switching to Idle.");
            this.playAnimation('idle');
        });
    }

    playSequence(sequence, onComplete) {
        let index = 0;

        const playNext = () => {
            if (index >= sequence.length) {
                if (onComplete) onComplete();
                return;
            }

            const animName = sequence[index];
            // this.log(`Sequence: ${animName}`);

            if (!this.animations[animName]) {
                index++;
                playNext();
                return;
            }

            const action = this.animations[animName];

            if (this.currentAction) this.currentAction.fadeOut(0.5);

            action.reset().fadeIn(0.5);
            action.setLoop(THREE.LoopOnce);
            action.clampWhenFinished = true;
            action.play();
            this.currentAction = action;

            const onFinished = (e) => {
                if (e.action === action) {
                    this.mixer.removeEventListener('finished', onFinished);
                    index++;
                    playNext();
                }
            };
            this.mixer.addEventListener('finished', onFinished);
        };

        playNext();
    }

    setTalking(talking) {
        this.isTalking = talking;
        // If we had a specific talk animation or morph targets, we'd use them here.
        // For now, maybe just bob the head or switch to a 'talk' animation if available.
        if (talking) {
            this.playAnimation('talk'); // Will try to find 'talk' or fallback
        } else {
            this.playAnimation('idle'); // Will try to find 'idle' or fallback
        }
    }

    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        const delta = this.clock.getDelta();
        if (this.mixer) this.mixer.update(delta);

        this.renderer.render(this.scene, this.camera);
    }
    cleanAnimationClips(clip) {
        if (!clip) return;
        clip.tracks.forEach(track => {
            // Remove mixamorig: or any other namespace prefix
            // Also remove .bones if present in some loaders
            track.name = track.name.replace(/^.*:/, '');
        });
    }
}
