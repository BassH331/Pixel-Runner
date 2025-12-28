import pygame as pg
from src.my_engine.animation import Animation, Animator
from src.my_engine.asset_manager import AssetManager

class Goblin(pg.sprite.Sprite):
    """
    A ground-based enemy that moves across the screen in a pattern.
    
    States:
    - WAITING: Initial delay before entering
    - ENTER: Running in from off-screen
    - IDLE: Brief pause before attacking
    - ATTACK: Performing an attack animation
    - EXIT: Running off-screen
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
        self.state_timer = 0
        self.start_x = x  # Store starting position for reset
        
    def set_scale(self, scale):
        """
        Update the scale of the goblin's sprite.
        
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
        """Load and prepare all animation frames for the goblin."""
        base_path = "assets/graphics/Goblin"
        
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
        
        # Load idle animation (when goblin is standing still)
        idle_frames = load_and_scale(f"{base_path}/Idle")
        self.animator.add("idle", Animation(idle_frames, 0.1))  # 0.1s per frame
        
        # Load running animation (for movement)
        run_frames = load_and_scale(f"{base_path}/Run")
        self.animator.add("run", Animation(run_frames, 0.1))
        
        # Load attack animation (plays once when attacking)
        atk_frames = load_and_scale(f"{base_path}/Attack")
        self.animator.add("attack", Animation(atk_frames, 0.1, loop=False))
        
        # Start with running animation by default
        self.animator.set("run")

    def update(self, dt):
        """
        Update goblin state and position based on current state.
        
        Args:
            dt (int): Time since last update in milliseconds
        """
        dt_sec = dt / 1000.0  # Convert to seconds
        
        # State machine for goblin behavior
        if self.state == "WAITING":
            # Wait for initial delay before entering
            self.state_timer += dt_sec
            if self.state_timer >= self.start_delay:
                self.state = "ENTER"
                self.state_timer = 0
                
        elif self.state == "ENTER":
            # Run in from left side of screen
            self.rect.x += self.speed * dt_sec
            self.animator.set("run")
            self.animator.flip_x = False  # Face right
            
            # Switch to IDLE when reaching near center
            if self.rect.centerx >= self.screen_width // 2 - 100:  # Stop left of center
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
                self.animator.set("run")
                
        elif self.state == "EXIT":
            # Run off to the right
            self.rect.x += self.speed * dt_sec
            self.animator.set("run")
            self.animator.flip_x = False  # Keep facing right
            
            # Reset position when off screen (for looping behavior)
            if self.rect.left > self.screen_width:
                self.rect.right = 0
                self.state = "ENTER"
        
        # Update animation frame
        self.animator.update(dt_sec)
        self.image = self.animator.get_frame()
        
    def draw(self, surface):
        """
        Draw the goblin on the given surface if not in WAITING state.
        
        Args:
            surface (pygame.Surface): The surface to draw on
        """
        if self.state != "WAITING":
            surface.blit(self.image, self.rect)
