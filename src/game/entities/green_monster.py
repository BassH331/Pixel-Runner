import pygame as pg
from src.my_engine.animation import Animation, Animator
from src.my_engine.asset_manager import AssetManager

class GreenMonster(pg.sprite.Sprite):
    """
    A powerful enemy that performs a sequence of two different attacks.
    
    States:
    - WAITING: Initial delay before entering
    - ENTER: Walking in from off-screen
    - IDLE_1: Brief pause before first attack
    - ATTACK_1: First attack animation
    - IDLE_2: Brief pause before second attack
    - ATTACK_2: Second attack animation
    - EXIT: Walking off-screen
    """
    def __init__(self, x, y, screen_width, scale=1.0, start_delay=0.0):
        super().__init__()
        # Animation and rendering
        self.animator = Animator()
        self.scale = scale
        self.screen_width = screen_width
        self.start_delay = start_delay
        
        # Load all animation frames
        self.load_animations()
        
        # Set initial frame and position
        self.image = self.animator.get_frame()
        self.rect = self.image.get_rect(midbottom=(x, y))
        
        # Movement properties
        self.speed = 200  # Pixels per second
        self.state = "WAITING" if start_delay > 0 else "ENTER"
        self.state_timer = 0  # Tracks time in current state
        
    def set_scale(self, scale):
        """
        Update the scale of the green monster's sprite.
        
        Args:
            scale (float): New scale multiplier for the sprite
        """
        self.scale = scale
        # Reload animations with new scale
        self.load_animations()
        # Update rect size while maintaining position
        old_midbottom = self.rect.midbottom
        self.image = self.animator.get_frame()
        self.rect = self.image.get_rect(midbottom=old_midbottom)

    def load_animations(self):
        """Load and prepare all animation frames for the green monster."""
        base_path = "assets/graphics/green_monster"
        
        def load_and_scale(path):
            """Helper to load and scale animation frames."""
            frames = AssetManager.get_animation_frames(path)
            if self.scale != 1.0:
                scaled_frames = []
                for frame in frames:
                    # Calculate new size while maintaining aspect ratio
                    new_size = (
                        int(frame.get_width() * self.scale),
                        int(frame.get_height() * self.scale)
                    )
                    scaled_frames.append(pg.transform.scale(frame, new_size))
                return scaled_frames
            return frames
        
        # Load idle animation (standing still between actions)
        idle_frames = load_and_scale(f"{base_path}/idle")
        self.animator.add("idle", Animation(idle_frames, 0.1))  # 0.1s per frame
        
        # Load walk animation (for movement)
        walk_frames = load_and_scale(f"{base_path}/walk")
        self.animator.add("walk", Animation(walk_frames, 0.1))
        
        # Load first attack animation (plays once, slower for emphasis)
        atk1_frames = load_and_scale(f"{base_path}/1atk")
        self.animator.add("attack_1", Animation(atk1_frames, 0.15, loop=False))
        
        # Load second attack animation (plays once, different from first attack)
        atk2_frames = load_and_scale(f"{base_path}/2atk")
        self.animator.add("attack_2", Animation(atk2_frames, 0.15, loop=False))
        
        # Start with walk animation by default
        self.animator.set("walk")

    def update(self, dt):
        """
        Update green monster state and position based on current state.
        
        Args:
            dt (int): Time since last update in milliseconds
        """
        dt_sec = dt / 1000.0  # Convert to seconds
        
        # State machine for green monster behavior
        if self.state == "WAITING":
            # Wait for initial delay before entering
            self.state_timer += dt_sec
            if self.state_timer >= self.start_delay:
                self.state = "ENTER"
                self.state_timer = 0
        
        elif self.state == "ENTER":
            # Walk in from left side of screen
            self.rect.x += self.speed * dt_sec
            self.animator.set("walk")
            self.animator.flip_x = False  # Face right
            
            # Switch to IDLE_1 when reaching center
            if self.rect.centerx >= self.screen_width // 2:
                self.state = "IDLE_1"
                self.state_timer = 0
                self.animator.set("idle")
                
        elif self.state == "IDLE_1":
            # Brief pause before first attack
            self.state_timer += dt_sec
            if self.state_timer >= 0.5:  # Wait 0.5 seconds
                self.state = "ATTACK_1"
                self.animator.set("attack_1")
    
        elif self.state == "ATTACK_1":
            # Wait for first attack animation to complete
            if self.animator.current_animation.finished:
                self.state = "IDLE_2"
                self.state_timer = 0
                self.animator.set("idle")
                
        elif self.state == "IDLE_2":
            # Shorter pause before second attack
            self.state_timer += dt_sec
            if self.state_timer >= 0.2:  # Wait 0.2 seconds
                self.state = "ATTACK_2"
                self.animator.set("attack_2")
                
        elif self.state == "ATTACK_2":
            # Wait for second attack animation to complete
            if self.animator.current_animation.finished:
                self.state = "EXIT"
                self.animator.set("walk")
                
        elif self.state == "EXIT":
            # Walk off to the right
            self.rect.x += self.speed * dt_sec
            self.animator.set("walk")
            
            # Loop back to start when off screen
            if self.rect.left > self.screen_width:
                self.rect.right = 0
                self.state = "ENTER"
        
        # Update animation frame
        self.animator.update(dt_sec)
        self.image = self.animator.get_frame()
        
    def draw(self, surface):
        """
        Draw the green monster on the given surface.
        
        Args:
            surface (pygame.Surface): The surface to draw on
        """
        surface.blit(self.image, self.rect)
