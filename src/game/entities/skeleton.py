import pygame as pg
import random
from src.my_engine.ecs import Entity
from src.my_engine.asset_manager import AssetManager

class Skeleton(Entity):
    """
    A skeletal enemy that chases and attacks the player.
    
    States:
    - IDLE: Standing still, waiting for player
    - CHASE: Moving towards the player
    - ATTACK: Performing an attack
    - HURT: Reacting to taking damage
    - DEATH: Playing death animation
    """
    def __init__(self, x, y, player):
        """
        Initialize a skeleton enemy.
        
        Args:
            x (int): Initial x position
            y (int): Initial y position
            player (Player): Reference to the player object
        """
        super().__init__(x, y)
        self.player = player  # Reference to track player position
        
        # Load all animation frames
        self.idle_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Idle/skeleton-idle_{}.png", 8)
        self.walk_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Walk/skeleton-walk_{:02d}.png", 10)
        self.attack_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Attack1/skeleton-atk2_{:02d}.png", 10)
        self.attack2_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Attack2/skeleton-atk1_{}.png", 9)
        self.hurt_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Hurt/skeleton-hurt_{}.png", 5)
        self.death_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Die/skeleton-death_{:02d}.png", 13)
        
        # Animation state
        self.current_frames = self.idle_frames
        self.animation_index = 0
        self.image = self.current_frames[self.animation_index]
        self.rect = self.image.get_rect(midbottom=(x, y))
        
        # Hitbox adjustment (smaller than sprite for better gameplay)
        self.reduce_hitbox(40, 20, align='bottom')
        
        # AI properties
        self.speed = 2.5               # Movement speed
        self.detection_range = 1000    # Distance to detect player
        self.attack_range = 60         # Distance to start attacking
        self.state = "IDLE"            # Current AI state
        self.facing_left = True        # Direction skeleton is facing
        self.gravity = 0               # Current gravity force
        self.ground_y = pg.display.Info().current_h - 34  # Ground level
        self.health = 2                # Number of hits to defeat
        
    def _load_frames(self, path_pattern, count):
        """
        Load and scale animation frames from a file pattern.
        
        Args:
            path_pattern (str): Format string for frame paths (e.g., 'path/frame_{}.png')
            count (int): Number of frames to load
            
        Returns:
            list: List of scaled pygame.Surface objects
        """
        frames = []
        for i in range(count):
            try:
                path = path_pattern.format(i)
                frame = AssetManager.get_texture(path)
                # Scale up to match game style (original ~32x32, scaled to ~64x64)
                original_size = frame.get_size()
                scaled_size = (original_size[0] * 2, original_size[1] * 2)
                scaled_frame = pg.transform.scale(frame, scaled_size)
                frames.append(scaled_frame)
            except Exception as e:
                print(f"Error loading frame {i} from {path_pattern}: {e}")
        return frames

    def update(self, dt=None, scroll_speed=0):
        """
        Update skeleton state each frame.
        
        Args:
            dt (float, optional): Time since last update in seconds
            scroll_speed (int, optional): Scrolling speed of the level
        """
        # Apply level scrolling
        self.rect.x -= scroll_speed
        
        # Update physics and AI
        self.apply_gravity()
        self.ai_logic()
        self.animate()
        
        # Call parent class update
        super().update(dt)
        
    def take_damage(self):
        """
        Handle the skeleton taking damage.
        Changes state to HURT or DEATH based on remaining health.
        """
        # Ignore if already hurt or dying
        if self.state in ["HURT", "DEATH"]:
            return
            
        # Reduce health and update state
        self.health -= 1
        if self.health <= 0:
            self.state = "DEATH"  # No health left, die
        else:
            self.state = "HURT"   # Still alive, show hurt animation
            
        # Reset animation
        self.animation_index = 0
        
    def ai_logic(self):
        """
        Handle the skeleton's AI decision making.
        Determines whether to chase, attack, or idle based on player position.
        """
        # Don't process AI if no player or in hurt/death state
        if not self.player or self.state in ["HURT", "DEATH"]:
            return
            
        # Get player position and distances
        player_rect = self.player.sprite.rect
        dist_x = abs(self.rect.centerx - player_rect.centerx)
        dist_y = abs(self.rect.centery - player_rect.centery)
        
        # State machine for AI behavior
        if self.state == "ATTACK":
            # Let attack animation play out (handled in animate())
            pass
        else:
            # Check if player is in attack range (horizontally close, vertically aligned)
            if dist_x < self.attack_range and dist_y < 100:
                self.state = "ATTACK"
                self.animation_index = 0
                # Randomly choose between two attack animations
                self.current_frames = random.choice([self.attack_frames, self.attack2_frames])
            # Check if player is in detection range
            elif dist_x < self.detection_range and dist_y < 100:
                self.state = "CHASE"
            else:
                self.state = "IDLE"
        
        # Handle movement for CHASE state
        if self.state == "CHASE":
            # Move towards player
            if self.rect.centerx > player_rect.centerx:
                self.rect.x -= self.speed
                self.facing_left = True
            else:
                self.rect.x += self.speed
                self.facing_left = False

    def apply_gravity(self):
        """
        Apply gravity to the skeleton.
        Ensures the skeleton stays on the ground and falls when in the air.
        """
        self.gravity += 1  # Increase downward velocity
        self.rect.y += self.gravity
        
        # Stop at ground level
        if self.rect.bottom >= self.ground_y:
            self.rect.bottom = self.ground_y
            self.gravity = 0  # Reset gravity when on ground
                
    def animate(self):
        """
        Handle animation updates based on current state.
        Updates the current frame and handles state transitions.
        """
        # Handle death animation
        if self.state == "DEATH":
            self.current_frames = self.death_frames
            self.animation_index += 0.15  # Play death animation slowly
            if self.animation_index >= len(self.current_frames):
                self.kill()  # Remove from all sprite groups when done
                return
                
        # Handle hurt animation
        elif self.state == "HURT":
            self.current_frames = self.hurt_frames
            self.animation_index += 0.15
            if self.animation_index >= len(self.current_frames):
                self.state = "IDLE"  # Return to idle after hurt animation
                self.animation_index = 0
                
        # Handle attack animation
        elif self.state == "ATTACK":
            self.animation_index += 0.15
            if self.animation_index >= len(self.current_frames):
                self.animation_index = 0
                self.state = "IDLE"  # Return to idle after attack
                self.current_frames = self.idle_frames
                
        # Handle chase/walk animation
        elif self.state == "CHASE":
            self.current_frames = self.walk_frames
            self.animation_index += 0.15  # Walking animation speed
            if self.animation_index >= len(self.current_frames):
                self.animation_index = 0  # Loop walk animation
                
        # Handle idle animation (default state)
        else:  # IDLE
            self.current_frames = self.idle_frames
            self.animation_index += 0.1  # Slower animation for idle
            if self.animation_index >= len(self.current_frames):
                self.animation_index = 0  # Loop idle animation
        
        # Update current frame and handle facing direction
        if int(self.animation_index) < len(self.current_frames):
            self.image = self.current_frames[int(self.animation_index)]
            # Flip image if facing left
            if self.facing_left:
                self.image = pg.transform.flip(self.image, True, False)

    def draw(self, surface):
        """
        Draw the skeleton and its health bar.
        
        Args:
            surface (pygame.Surface): The surface to draw on
        """
        # Draw the skeleton sprite
        super().draw(surface)
        
        # Draw health bar if damaged and alive
        if self.health < 2 and self.state != "DEATH":
            # Health bar dimensions and position
            bar_width = 40
            bar_height = 5
            bar_x = self.rect.centerx - bar_width // 2
            bar_y = self.rect.top - 10  # Above the sprite
            
            # Draw background (empty health)
            pg.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
            
            # Draw current health (red)
            health_ratio = self.health / 2  # 2 is max health
            pg.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, bar_width * health_ratio, bar_height))
