from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import WindowProperties, AmbientLight, DirectionalLight, Vec4, AntialiasAttrib
import threading
import os
import math

# Global instance for external control
instance = None

class Avatar(ShowBase):
    def __init__(self):
        global instance
        instance = self
        
        # Initialize Panda3D ShowBase
        ShowBase.__init__(self)
        
        # Window Properties
        props = WindowProperties()
        props.setTitle("AURA Avatar")
        props.setSize(800, 600)
        self.win.requestProperties(props)
        
        self.disableMouse()
        self.setBackgroundColor(0.2, 0.2, 0.2) # Grey background
        self.render.setAntialias(AntialiasAttrib.MAuto)

        # UI Imports
        from direct.gui.DirectGui import DirectButton, DirectFrame, OnscreenText
        from panda3d.core import TextNode

        # Lighting
        dlight = DirectionalLight('dlight')
        dlight.setColor(Vec4(0.8, 0.8, 0.8, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(0, -60, 0)
        self.render.setLight(dlnp)
        
        alight = AmbientLight('alight')
        alight.setColor(Vec4(0.4, 0.4, 0.4, 1)) # Brighter ambient
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)

        # Paths
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_dir = os.path.join(project_root, 'assets', 'models')
        anim_dir = os.path.join(project_root, 'assets', 'animations')
        
        self.character = None
        self.is_actor = False
        self.current_anim = None
        self.requested_anim = None

        # 1. Try Loading Character FBX (Animated)
        char_fbx = os.path.join(model_dir, 'character.fbx')
        
        # Map animations
        anims = {
            'dance': os.path.join(anim_dir, 'Hip Hop Dancing.fbx'),
            'clap': os.path.join(anim_dir, 'Clapping.fbx'),
            'jump': os.path.join(anim_dir, 'Jumping Down.fbx'),
            'idle': os.path.join(anim_dir, 'Clapping.fbx'),
        }

        if os.path.exists(char_fbx):
            print(f"Found character.fbx at {char_fbx}")
            try:
                self.character = Actor(char_fbx, anims)
                self.character.reparentTo(self.render)
                self.is_actor = True
                print("Loaded character.fbx as Actor.")
            except Exception as e:
                print(f"Failed to load character.fbx as Actor: {e}")
                self.character = None
        
        # 2. Fallback to character.obj (Static) - PRIORITIZE USER'S MODEL
        if not self.character:
            char_obj = os.path.join(model_dir, 'character.obj')
            if os.path.exists(char_obj):
                print(f"Trying static fallback: {char_obj}")
                try:
                    # Load as static model, NOT Actor
                    self.character = self.loader.loadModel(char_obj)
                    self.character.reparentTo(self.render)
                    self.is_actor = False
                    print("Loaded character.obj as Static Model.")
                except Exception as e:
                    print(f"Failed to load character.obj: {e}")
                    self.character = None

        # 3. Fallback to Clapping.fbx (Animated)
        if not self.character:
            fallback_fbx = os.path.join(anim_dir, 'Clapping.fbx')
            if os.path.exists(fallback_fbx):
                print(f"Trying fallback: {fallback_fbx}")
                try:
                    self.character = Actor(fallback_fbx, anims)
                    self.character.reparentTo(self.render)
                    self.is_actor = True
                    print("Loaded Clapping.fbx as Actor.")
                except Exception as e:
                    print(f"Failed to load Clapping.fbx: {e}")
                    self.character = None

        # Setup Character (Scale/Pos)
        if self.character:
            try:
                # Auto-scale
                min_point, max_point = self.character.getTightBounds()
                size = max_point - min_point
                center = (min_point + max_point) / 2
                print(f"Bounds: {size}, Center: {center}")
                
                max_dim = max(size.getX(), size.getY(), size.getZ())
                if max_dim > 0:
                    scale_factor = 10.0 / max_dim
                    self.character.setScale(scale_factor)
                    print(f"Scaled by: {scale_factor}")
                
                # Center it
                self.character.setPos(-center.getX() * scale_factor, -center.getY() * scale_factor + 5, -center.getZ() * scale_factor - 5)
                # Fix Orientation (Mixamo models are often Y-up, Panda is Z-up)
                # Trying 0,0,0 first as requested by user to fix orientation issues
                self.character.setHpr(180, 0, 0) 
                
                # Start Animation if Actor
                if self.is_actor:
                    try:
                        self.character.loop('idle')
                        self.current_anim = 'idle'
                    except Exception as e:
                        print(f"Could not loop idle: {e}")
            except Exception as e:
                print(f"Error setting up character: {e}")

        # Debug Cube
        try:
            self.box = self.loader.loadModel("models/box")
            self.box.reparentTo(self.render)
            self.box.setPos(5, 10, 0)
            self.box.setColor(1, 0, 0, 1)
        except:
            pass

        # Camera
        self.camera.setPos(0, -60, 10) # Moved back
        self.camera.lookAt(0, 0, 0)
        
        # Add Camera Spin Task - DISABLED
        # self.taskMgr.add(self.spinCameraTask, "SpinCameraTask")
        self.taskMgr.add(self.updateAnimTask, "UpdateAnimTask")

        # UI Overlay
        self.ui_frame = DirectFrame(frameColor=(0, 0, 0, 0.5),
                                    frameSize=(-1.2, 1.2, -0.15, 0.15),
                                    pos=(0, 0, -0.85))
        
        buttons = ['dance', 'happy', 'sad', 'hug']
        x = -0.6
        for anim in buttons:
            DirectButton(text=anim.title(),
                         scale=0.07,
                         pos=(x, 0, 0),
                         parent=self.ui_frame,
                         command=self.set_animation,
                         extraArgs=[anim])
            x += 0.4

    def spinCameraTask(self, task):
        angleDegrees = task.time * 10.0
        angleRadians = angleDegrees * (3.14159 / 180.0)
        self.camera.setPos(30 * math.sin(angleRadians), -30 * math.cos(angleRadians), 5)
        self.camera.lookAt(0, 0, 0)
        return task.cont

    def set_animation(self, anim_type):
        # Thread-safe: just set the requested state, let the main thread handle it
        self.requested_anim = anim_type
        print(f"Animation requested: {anim_type}")

    def updateAnimTask(self, task):
        if self.requested_anim:
            anim_type = self.requested_anim
            self.requested_anim = None # Clear request
            
            if not self.character or not self.is_actor:
                return task.cont

            print(f"Applying Animation: {anim_type}")
            
            target_anim = 'idle'
            if anim_type == 'dance': target_anim = 'dance'
            elif anim_type == 'happy': target_anim = 'jump'
            elif anim_type == 'sad': target_anim = 'clap'
            elif anim_type == 'hug': target_anim = 'clap'
            
            if target_anim != self.current_anim:
                try:
                    self.character.stop()
                    self.character.loop(target_anim)
                    self.current_anim = target_anim
                except Exception as e:
                    print(f"Error switching animation: {e}")
        return task.cont

def run_avatar():
    try:
        app = Avatar()
        app.run()
    except Exception as e:
        print(f"Panda3D Critical Error: {e}")

if __name__ == "__main__":
    run_avatar()
