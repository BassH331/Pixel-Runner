import pygame as pg
from src.my_engine.animation import Animation, Animator
from src.my_engine.asset_manager import AssetManager

class Bat(pg.sprite.Sprite):
    """
    A flying enemy that moves in a pattern across the screen.
    
    States:
    - WAITING: Initial delay before entering
    - ENTER: Flying in from off-screen
    - IDLE: Brief pause before attacking
    - ATTACK: Performing an attack animation
    - EXIT: Flying off-screen
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
        self.speed = 250  # Pixels per second
        self.state = "WAITING" if start_delay > 0 else "ENTER"
        self.state_timer = 0
        self.start_x = x  # Store starting position for reset
        
    def set_scale(self, scale):
        """
        Update the scale of the bat's sprite.
        
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
        """Load and prepare all animation frames for the bat."""
        base_path = "assets/graphics/bat"
        
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
        
        # Load idle animation (when bat is hovering)
        idle_frames = load_and_scale(f"{base_path}/idle")
        self.animator.add("idle", Animation(idle_frames, 0.1))  # 0.1s per frame
        
        # Load flying animation (for movement)
        fly_frames = load_and_scale(f"{base_path}/running")
        self.animator.add("fly", Animation(fly_frames, 0.1))
        
        # Load attack animation (plays once when attacking)
        atk_frames = load_and_scale(f"{base_path}/attacking")
        self.animator.add("attack", Animation(atk_frames, 0.1, loop=False))
        
        # Start with flying animation by default
        self.animator.set("fly")

    def update(self, dt):
        """
        Update bat state and position based on current state.
        
        Args:
            dt (int): Time since last update in milliseconds
        """
        dt_sec = dt / 1000.0  # Convert to seconds
        
        # State machine for bat behavior
        if self.state == "WAITING":
            # Wait for initial delay before entering
            self.state_timer += dt_sec
            if self.state_timer >= self.start_delay:
                self.state = "ENTER"
                self.state_timer = 0
                
        elif self.state == "ENTER":
            # Fly in from left side of screen
            self.rect.x += self.speed * dt_sec
            self.animator.set("fly")
            self.animator.flip_x = True  # Face right (flipped)
            
            # Switch to IDLE when reaching center
            if self.rect.centerx >= self.screen_width // 2:
                self.state = "IDLE"
                self.state_timer = 0
                self.animator.set("idle")
                
        elif self.state == "IDLE":
            # Brief pause before attacking
            self.state_timer += dt_sec
            if self.state_timer >= 0.5:  # Wait 0.5 seconds
                self.state = "ATTACK"
                self.animator.set("attack")

        elif self.state == "ATTACK":
            # Wait for attack animation to complete
            if self.animator.current_animation.finished:
                self.state = "EXIT"
                self.animator.set("fly")
                
        elif self.state == "EXIT":
            # Fly off to the right
            self.rect.x += self.speed * dt_sec
            self.animator.set("fly")
            self.animator.flip_x = True  # Keep facing right
            
            # Reset position when off screen (for looping behavior)
            if self.rect.left > self.screen_width:
                self.rect.right = 0
                self.state = "ENTER"
        
        # Update animation frame
        self.animator.update(dt_sec)
        self.image = self.animator.get_frame()
        
    def draw(self, surface):
        """
        Draw the bat on the given surface if not in WAITING state.
        
        Args:
            surface (pygame.Surface): The surface to draw on
        """
        if self.state != "WAITING":
            surface.blit(self.image, self.rect)
