"""
Game state module implementing the main gameplay loop.

This module manages the core game session including entity updates,
collision detection with frame-accurate hit detection, and state transitions.
"""

from __future__ import annotations
import os

from random import randint
from typing import TYPE_CHECKING, Final, Optional
from dataclasses import dataclass

import pygame as pg

from src.game.entities.enemy import Enemy
from v3x_zulfiqar_gideon.world import WorldEventManager, InteractionPoint, WorldLoader, Sky
from src.game.entities.wizard_npc import WizardNPC
from src.game.entities.player import Player
from src.game.entities.skeleton import Skeleton, SkeletonState
from src.game.ui import PlayerUI, ObjectiveDisplay, ObjectiveTriggerManager, NotificationBanner
from v3x_zulfiqar_gideon.asset_manager import AssetManager
from v3x_zulfiqar_gideon.state_machine import State

if TYPE_CHECKING:
    from v3x_zulfiqar_gideon.state_machine import StateManager


class GameState(State):
    """
    Primary gameplay state managing entities, physics, and game logic.
    
    Handles player and enemy updates, collision detection with
    frame-precise combat resolution, and win/lose conditions.
    
    Combat System:
        Both player and enemy attacks use frame-based hit detection.
        Damage is only applied during specific animation frames,
        with duplicate hit prevention per attack.
    """
    
    # Score rewards
    _SCORE_PER_HIT: Final[int] = 10
    
    # Game over delay in milliseconds
    _GAME_OVER_DELAY_MS: Final[int] = 3000

    # Attack-two (smash) sound variants mapped by active frame index
    _SMASH_SOUND_MAP: Final[dict[int, str]] = {
        3: "smash_phase_1",
        7: "smash_phase_2",
        11: "smash_phase_3",
    }
    
    def __init__(self, manager: StateManager) -> None:
        """
        Initialize the game state.
        
        Args:
            manager: State machine manager for state transitions.
        """
        super().__init__(manager)
        
        display_surface = pg.display.get_surface()
        self.width: int = display_surface.get_width()
        self.height: int = display_surface.get_height()
        
        # Audio system
        self.audio_manager = self.manager.audio_manager
        self.bg_music_channel_id: Optional[int] = None
        
        # Entity groups
        self.player = pg.sprite.GroupSingle()
        self.player.add(
            Player(200, self.height + 135, self.audio_manager)
        )
        self.obstacle_group: pg.sprite.Group = pg.sprite.Group()
        self.ambient_group: pg.sprite.Group = pg.sprite.Group()
        
        # Initialize skeleton spawning
        
        # Interaction points (world-positioned proximity triggers)
        self.interaction_group: pg.sprite.Group = pg.sprite.Group()
        self._setup_interaction_points()

        # NPC group (animated world NPCs with dialogue)
        self.npc_group: pg.sprite.Group = pg.sprite.Group()

        # UI
        self.player_ui = PlayerUI()
        self.objective_display = ObjectiveDisplay()
        self.notification_banner = NotificationBanner(scale=0.6, icon_scale=0.6)
        self._show_objective_on_start: bool = True

        # Objective trigger manager (time & flag based)
        self.trigger_manager = ObjectiveTriggerManager()
        self._setup_triggers()
        self._game_start_ticks: int = pg.time.get_ticks()
        
        # Sky (parallax background)
        self.sky = Sky(
            self.width, 
            self.height,
            layer_paths=[f"assets/graphics/Clouds 3/{i}.png" for i in range(1, 5)],
            speeds=[0, 0, 20, 40]
        )

        # Background parallax
        self.bg_image = AssetManager.get_texture(
            "assets/graphics/background images/new_bg_images/bg_image.png"
        )
        self.bg_image = pg.transform.smoothscale(
            self.bg_image, (self.width, self.height)
        )
        self.bg_x1: int = 0
        self.bg_x2: int = self.width
        self.bg_scroll_speed: int = 0
        self.max_bg_scroll_speed: int = 5
        
        # Game state
        self.score: int = 0
        self.start_time: int = int(pg.time.get_ticks() / 1000)
        self.next_bat_group_time: int = pg.time.get_ticks()
        self.next_skeleton_spawn_time: int = pg.time.get_ticks()
        self._game_over_start_time: Optional[int] = None

        # Travel distance tracking
        self.world_distance: float = 0.0
        self.max_distance_reached: float = 0.0
        self._level_end_distance: float = 8000.0
        self._level_complete: bool = False
        self._level_name: str = "The Blight Begins"

        # World Event System (distance-based triggers)
        self.world_manager = WorldEventManager()
        self._setup_world_events()
        
        # Debug visualization
        self.debug_mode: bool = False
        self._last_log_time = pg.time.get_ticks()
        self._frame_count = 0
        
        self.level_data = WorldLoader.load_json(os.path.join("game_data", "level_1.json"))
        
        if self.level_data:
            self.BAT_GROUP_MIN_DELAY = self.level_data.get("spawn_rate_min", 5000)
            self.BAT_GROUP_MAX_DELAY = self.level_data.get("spawn_rate_max", 15000)

            # Level metadata
            self._level_name = self.level_data.get("level_name", self._level_name)
            self._level_end_distance = float(self.level_data.get("level_end_distance", self._level_end_distance))

            # Spawn zones (distance-based difficulty scaling)
            self._spawn_zones = self.level_data.get("spawn_zones", None)
            if self._spawn_zones:
                # Convert max_dist sentinel values for runtime comparisons
                for zone in self._spawn_zones:
                    if zone["max_dist"] >= 99999:
                        zone["max_dist"] = float("inf")
            else:
                self._spawn_zones = None  # Will use defaults in _get_spawn_zone

            # Bat spawn config
            bat_cfg = self.level_data.get("bat_spawn", {})
            self._bat_min_count: int = bat_cfg.get("min_count", 3)
            self._bat_max_count: int = bat_cfg.get("max_count", 5)
            
            # Apply player position from level data
            player_data = next(
                (e for e in self.level_data.get("entities", [])
                 if e["type"] == "player"),
                None
            )
            if player_data:
                self.player.sprite.rect.midbottom = (
                    player_data["x"],
                    player_data["y"],
                )
            
            # Load World Events from JSON
            world_events = self.level_data.get("world_events", [])
            for event in world_events:
                self.world_manager.add_event(
                    id=event["id"],
                    distance=event["distance"],
                    event_type=event["type"],
                    **event.get("params", {})
                )
            # Optimize the list after loading
            self.world_manager.finalize()
        else:
            self.BAT_GROUP_MIN_DELAY = 5000
            self.BAT_GROUP_MAX_DELAY = 15000
            self._spawn_zones = None
            self._bat_min_count = 3
            self._bat_max_count = 5
    
    def _setup_triggers(self) -> None:
        """Configure time-based and flag-based objective triggers."""
        # Combat tip after 15 seconds
        self.trigger_manager.add_trigger(
            text="Use Q, E, and W for different attack combos. "
                 "Press R or R2 to raise your shield and defend!",
            title="Combat Tip",
            trigger_type="time",
            delay_seconds=15.0,
        )
        # Congratulations on first skeleton kill
        self.trigger_manager.add_trigger(
            text="Well done, warrior! The undead fall before your blade. "
                 "Keep moving and stay vigilant for more threats ahead.",
            title="Progress",
            trigger_type="flag",
            flag_name="first_kill",
        )

    def _setup_interaction_points(self) -> None:
        """Initial interaction points (none — they spawn by distance now)."""
        pass  # Entities are spawned dynamically in _spawn_world_entities()

    def _get_spawn_zone(self) -> dict:
        """Get the current spawn zone based on max distance reached."""
        zones = self._spawn_zones if self._spawn_zones else [
            {"min_dist": 0,    "max_dist": 1000,  "max_skeletons": 2, "delay": 6000},
            {"min_dist": 1000, "max_dist": 3000,  "max_skeletons": 3, "delay": 4000},
            {"min_dist": 3000, "max_dist": 6000,  "max_skeletons": 5, "delay": 3000},
            {"min_dist": 6000, "max_dist": float("inf"), "max_skeletons": 6, "delay": 2000},
        ]
        for zone in reversed(zones):
            if self.max_distance_reached >= zone["min_dist"]:
                return zone
        return zones[0]

    def _setup_world_events(self) -> None:
        """Register handlers for world events. Scheduling is handled via JSON config."""
        self.world_manager.register_handler("interaction", self._handle_interaction_spawn)
        self.world_manager.register_handler("npc", self._handle_npc_spawn)
        self.world_manager.register_handler("enemy_wave", self._handle_enemy_wave)

    def _handle_interaction_spawn(self, params: dict) -> None:
        """Handler for 'interaction' events."""
        self.interaction_group.add(InteractionPoint(
            x=self.width + 50,
            y=self.height - 100,
            text=params["text"],
            title=params["title"],
            proximity_radius=params["radius"],
            font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf"
        ))

    def _handle_npc_spawn(self, params: dict) -> None:
        """Handler for 'npc' events."""
        if params.get("npc_type") == "wizard":
            self.npc_group.add(WizardNPC(
                x=self.width + 50,
                y=self.height - 100,
                text=params["text"],
                title=params["title"],
                scale=2.0,
                proximity_radius=params.get("radius", 160),
            ))

    def _handle_enemy_wave(self, params: dict) -> None:
        """Handler for 'enemy_wave' events."""
        count = params.get("count", 3)
        enemy_type = params.get("type", "bat")
        
        if enemy_type == "bat":
            for _ in range(count):
                y_pos = randint(50, self.height // 2)
                x_offset = randint(0, 175)
                bat = Enemy()
                bat.rect.midleft = (self.width + x_offset, y_pos)
                bat.y_base = y_pos
                self.ambient_group.add(bat)
            self.audio_manager.play_sound("bats")
        elif enemy_type == "skeleton":
            for _ in range(count):
                self.spawn_skeleton()

    # ─────────────────────────────────────────────────────────────────────────
    # State Lifecycle
    # ─────────────────────────────────────────────────────────────────────────
    
    def on_enter(self) -> None:
        """Initialize state when entering gameplay."""
        self.audio_manager.stop_all_sounds()
        self.bg_music_channel_id = self.audio_manager.play_sound(
            "game_loop",
            loop=True,
            volume=0.8,
        )
        self.player_ui.start_timer()

        # Show level notification banner on first entry
        if self._show_objective_on_start:
            self.notification_banner.show(self._level_name, notification="yellow")
            self._show_objective_on_start = False
        
    def on_exit(self) -> None:
        """Cleanup when leaving gameplay state."""
        if self.bg_music_channel_id is not None:
            self.audio_manager.stop_sound(self.bg_music_channel_id)
            self.bg_music_channel_id = None
        
    def handle_event(self, event: pg.event.Event) -> None:
        """
        Process input events.
        
        Args:
            event: Pygame event to process.
        """
        # While objective overlay is active, only listen for dismiss input
        if self.objective_display.is_active:
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                self.objective_display.dismiss()
            elif event.type == pg.JOYBUTTONDOWN and event.button == 0:
                self.objective_display.dismiss()
            return

        # Check for interaction input (ENTER / gamepad X)
        interact_pressed = (
            (event.type == pg.KEYDOWN and event.key == pg.K_RETURN) or
            (event.type == pg.JOYBUTTONDOWN and event.button == 2)
        )
        if interact_pressed:
            for point in self.interaction_group:
                if point.can_interact:
                    self.objective_display.show(point.text, point.title)
                    point.mark_interacted()
                    break
            else:
                # Check NPC group if no interaction point was triggered
                for npc in self.npc_group:
                    if npc.can_interact:
                        self.objective_display.show(npc.text, npc.title)
                        npc.mark_interacted()
                        break

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_d:
                self.debug_mode = not self.debug_mode
    
    # ─────────────────────────────────────────────────────────────────────────
    # Entity Spawning
    # ─────────────────────────────────────────────────────────────────────────
    
    def spawn_enemies(self, current_time: int) -> None:
        """
        Spawn enemy groups based on time and distance-scaled difficulty.
        
        Args:
            current_time: Current game time in milliseconds.
        """
        zone = self._get_spawn_zone()

        # Spawn bats
        if current_time >= self.next_bat_group_time:
            bat_count = randint(self._bat_min_count, self._bat_max_count)
            for _ in range(bat_count):
                y_pos = randint(50, self.height // 2)
                x_offset = randint(0, 175)
                
                bat = Enemy()
                bat.rect.midleft = (self.width + x_offset, y_pos)
                bat.y_base = y_pos
                self.ambient_group.add(bat)
                
            self.audio_manager.play_sound("bats")
            self.next_bat_group_time = current_time + randint(
                self.BAT_GROUP_MIN_DELAY,
                self.BAT_GROUP_MAX_DELAY,
            )
        
        # Spawn skeletons (distance-scaled)
        if current_time >= self.next_skeleton_spawn_time:
            current_skeletons = sum(1 for sprite in self.obstacle_group 
                                 if isinstance(sprite, Skeleton))
            
            if current_skeletons < zone["max_skeletons"]:
                self.spawn_skeleton()
                self.next_skeleton_spawn_time = current_time + zone["delay"]
    
    def spawn_skeleton(self) -> None:
        """Spawn a new skeleton at a random position on the right side of the screen."""
        # Calculate spawn position (off-screen right, but not too far)
        spawn_x = self.width + randint(100, 300)
        spawn_y = self.height - 70  # Same as initial spawn height
        
        # Get player sprite from GroupSingle
        player_sprite = self.player.sprite
        if player_sprite is None:
            return  # Can't spawn skeleton without player
            
        # Create and add new skeleton
        skeleton = Skeleton(
            x=spawn_x,
            y=spawn_y,
            player=player_sprite  # Pass the actual Player instance
        )
        self.obstacle_group.add(skeleton)
        self.audio_manager.play_sound("skeleton_spawn")
    
    # ─────────────────────────────────────────────────────────────────────────
    # Background Parallax
    # ─────────────────────────────────────────────────────────────────────────
    
    def update_background(self, scroll_delta: int) -> None:
        """
        Update parallax background positions.
        
        Args:
            scroll_delta: Horizontal scroll amount this frame.
        """
        self.bg_x1 -= scroll_delta
        self.bg_x2 -= scroll_delta
        
        # Wrap background images for infinite scroll
        if scroll_delta > 0:
            if self.bg_x1 <= -self.width:
                self.bg_x1 = self.width
            if self.bg_x2 <= -self.width:
                self.bg_x2 = self.width
        elif scroll_delta < 0:
            if self.bg_x1 >= self.width:
                self.bg_x1 = -self.width
            if self.bg_x2 >= self.width:
                self.bg_x2 = -self.width
    
    # ─────────────────────────────────────────────────────────────────────────
    # Combat Collision Detection
    # ─────────────────────────────────────────────────────────────────────────
    
    def _handle_combat_collisions(self) -> None:
        """
        Process combat interactions between player and enemies.
        
        Uses frame-accurate hit detection for both player and enemy attacks,
        ensuring damage is only applied during configured hit frames with
        duplicate hit prevention.
        """
        player_sprite = self.player.sprite
        
        if player_sprite.is_dead:
            return
        
        # Process player attacks against all enemies
        self._process_player_attacks(player_sprite)
        
        # Process enemy attacks against player
        self._process_enemy_attacks(player_sprite)
        
        # Clean up dead skeletons and spawn new ones if needed
        current_time = pg.time.get_ticks()
        if current_time >= self.next_skeleton_spawn_time:
            self._manage_skeleton_spawns()
    
    def _process_player_attacks(self, player: Player) -> None:
        """
        Process player attacks against all enemies using frame-based detection.
        
        Damage is only applied when:
        1. Player is on an active hit frame
        2. Attack hitbox collides with enemy hitbox
        3. Enemy has not already been hit this attack
        
        Args:
            player: Player sprite instance.
        """
        # Gate 1: Player must be on an active hit frame
        if not player.should_deal_damage():
            return
        
        # Get the attack hitbox for precise collision
        attack_hitbox = player.get_attack_hitbox()
        if attack_hitbox is None:
            return
        
        # Check against all obstacles
        for obstacle in self.obstacle_group:
            # Skip dead enemies
            if hasattr(obstacle, 'is_dead') and obstacle.is_dead:
                continue
            
            # Skip invincible enemies
            if hasattr(obstacle, 'is_invincible') and obstacle.is_invincible:
                continue
            
            # Get enemy hitbox (prefer .hitbox, fallback to .rect)
            target_hitbox = (
                obstacle.hitbox
                if hasattr(obstacle, 'hitbox')
                else obstacle.rect
            )
            
            # Gate 2: Check hitbox collision
            if not attack_hitbox.colliderect(target_hitbox):
                continue
            
            # Gate 3: Check if already hit this attack (prevent duplicates)
            target_id = (
                obstacle.entity_id
                if hasattr(obstacle, 'entity_id')
                else id(obstacle)
            )
            
            if not player.try_register_hit(target_id):
                continue
            
            # ─────────────────────────────────────────────────────────────────
            # HIT CONFIRMED - Apply damage and effects
            # ─────────────────────────────────────────────────────────────────
            
            self._apply_player_damage_to_enemy(player, obstacle)
    
    def _apply_player_damage_to_enemy(
        self,
        player: Player,
        enemy: pg.sprite.Sprite,
    ) -> None:
        """
        Apply player attack damage and effects to an enemy.
        
        Retrieves frame-specific damage and knockback from the player's
        active attack configuration.
        
        Args:
            player: Player sprite instance.
            enemy: Enemy sprite that was hit.
        """
        # Get frame-specific damage from attack state
        damage = player.get_current_attack_damage()
        
        # Calculate knockback vector toward enemy
        knockback = player.get_attack_knockback(enemy.rect.center)
        
        # Apply damage to enemy
        if hasattr(enemy, 'take_damage'):
            # Check if enemy's take_damage accepts knockback parameter
            try:
                enemy.take_damage(damage, knockback)
            except TypeError:
                # Fallback: take_damage only accepts damage
                enemy.take_damage(damage)
        else:
            # Non-damageable obstacle - just destroy it
            enemy.kill()
        
        # Audio feedback based on attack type
        from src.game.entities.player import PlayerState
        if player.state == PlayerState.ATTACK_SMASH:
            sound_name = self._select_smash_sound(player)
            self.audio_manager.play_sound(sound_name)
            self.audio_manager.play_sound("attack_one")
        elif player.state == PlayerState.ATTACK_THRUST:
            self.audio_manager.play_sound("attack_one")
        else:
            self.audio_manager.play_sound("thrust")
        
        if isinstance(enemy, Skeleton):
            if (enemy.state == SkeletonState.DEATH and
                    not getattr(enemy, "_death_sound_played", False)):
                self.audio_manager.play_sound("skeleton_death")
                setattr(enemy, "_death_sound_played", True)
                # Fire "first_kill" flag for objective triggers
                self.trigger_manager.set_flag("first_kill")
        
        # Score reward
        self.score += self._SCORE_PER_HIT

    def _select_smash_sound(self, player: Player) -> str:
        """Choose smash attack sound variant based on current hit frame."""
        frame = player.get_current_attack_frame()
        if frame is None:
            return "smash"
        return self._SMASH_SOUND_MAP.get(frame, "smash")

    def _manage_skeleton_spawns(self) -> None:
        """Maintain skeleton population within configured limits."""
        zone = self._get_spawn_zone()
        current_skeletons = sum(
            1 for sprite in self.obstacle_group if isinstance(sprite, Skeleton)
        )
        if current_skeletons < zone["max_skeletons"]:
            self.spawn_skeleton()
            self.next_skeleton_spawn_time = (
                pg.time.get_ticks() + zone["delay"]
            )

    def _process_enemy_attacks(self, player: Player) -> None:
        """
        Process all enemy attacks against the player.
        
        Iterates through all obstacles and delegates to type-specific
        attack handlers.
        
        Args:
            player: Player sprite instance.
        """
        # Skip if player is invincible
        if player.is_invincible:
            return
            
        # Process attacks from all obstacles that can attack
        for obstacle in self.obstacle_group:
            if isinstance(obstacle, Skeleton):
                self._handle_skeleton_attack(player, obstacle)
                
    def _handle_skeleton_attack(self, player: Player, skeleton: Skeleton) -> None:
        """
        Handle skeleton attack collision with frame-precise damage.
        
        Args:
            player: Player sprite instance.
            skeleton: Attacking skeleton instance.
        """
        # Gate 1: Skeleton must be in attack state
        if skeleton.state != SkeletonState.ATTACK:
            return
        
        # Gate 2: Must be on a hit frame and not already registered
        if not skeleton.should_deal_damage():
            return
        
        # Gate 3: Check hitbox collision (use skeleton's attack hitbox if available)
        skeleton_hitbox = (
            skeleton.get_attack_hitbox()
            if hasattr(skeleton, 'get_attack_hitbox')
            else skeleton.rect
        )
        
        player_hitbox = (
            player.hitbox
            if hasattr(player, 'hitbox')
            else player.rect
        )
        
        if skeleton_hitbox and not skeleton_hitbox.colliderect(player_hitbox):
            return
        
        # Always register the hit attempt to prevent multi-hit exploitation.
        # This ensures the skeleton can't "save" its hit for when i-frames end.
        skeleton.register_hit(id(player))
        
        # Gate 4: Player invincibility check (handled inside take_damage)
        damage = skeleton.get_current_attack_damage()
        damage_applied = player.take_damage(damage)
        
        # Only apply secondary effects if damage went through
        if not damage_applied:
            return
        
        # Apply knockback
        knockback = skeleton.get_current_attack_knockback()
        if knockback > 0:
            knockback_direction = (
                -1 if skeleton.rect.centerx > player.rect.centerx else 1
            )
            self._apply_knockback_to_player(
                player,
                knockback * knockback_direction,
            )
        
        # Audio feedback for successful hit
        self.audio_manager.play_sound("player_hit")
        
        # Visual feedback
        if hasattr(player, 'trigger_hit_flash'):
            player.trigger_hit_flash()
            
        # Update score if needed (e.g., for tracking hits taken)
        if hasattr(self, 'score'):
            # Optional: Deduct points for getting hit
            self.score = max(0, self.score - 5)
            
        # Debug output if in debug mode
        if hasattr(self, 'debug_mode') and self.debug_mode:
            print(f"Player hit by skeleton! Health: {player.health}")
        self.audio_manager.play_sound("player_hurt")
    
    def _apply_knockback_to_player(
        self,
        player: Player,
        force: float,
    ) -> None:
        """
        Apply horizontal knockback force to the player.
        
        Delegates to player's knockback method if available, otherwise
        applies a simple position offset as fallback.
        
        Args:
            player: Player sprite instance.
            force: Horizontal knockback force (negative = left, positive = right).
        """
        if hasattr(player, 'apply_knockback'):
            player.apply_knockback(force)
        else:
            # Fallback: Direct position offset with screen bounds clamping
            player.rect.x += int(force)
            player.rect.left = max(player.rect.left, 0)
            
            screen_width = pg.display.get_surface().get_width()
            player.rect.right = min(player.rect.right, screen_width)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Main Update Loop
    # ─────────────────────────────────────────────────────────────────────────
    
    def update(self, dt: float) -> None:
        """
        Main game update tick.
        
        Args:
            dt: Delta time since last update in seconds.
        """
        # Freeze gameplay while objective overlay is active
        if self.objective_display.is_active:
            return

        # Update notification banner (runs independently of gameplay freeze)
        self.notification_banner.update(dt)

        current_time = pg.time.get_ticks()
        
        # Enemy spawning
        self.spawn_enemies(current_time)
        
        # Calculate scroll speed based on player movement
        player_sprite = self.player.sprite
        if player_sprite.is_running:
            self.bg_scroll_speed = self.max_bg_scroll_speed * player_sprite.direction
        else:
            self.bg_scroll_speed = 0

        # Track travel distance
        self.world_distance += self.bg_scroll_speed
        if self.world_distance > self.max_distance_reached:
            self.max_distance_reached = self.world_distance

        # Update world events (distance-triggered)
        self.world_manager.update(self.world_distance)

        # Check level endpoint
        if not self._level_complete and self.world_distance >= self._level_end_distance:
            self._level_complete = True
            self.objective_display.show(
                "You have reached the end of this land. "
                "The undead have been pushed back... for now. "
                "Well fought, warrior!",
                "Level Complete",
            )
        
        # Update systems
        self.update_background(self.bg_scroll_speed)
        self.player_ui.update()
        self.player.update()
        self.obstacle_group.update(dt, self.bg_scroll_speed)
        self.ambient_group.update(dt, self.bg_scroll_speed)
        self.interaction_group.update(dt, self.bg_scroll_speed)
        self.npc_group.update(dt, self.bg_scroll_speed)

        # Check proximity for interaction points
        for point in self.interaction_group:
            point.check_proximity(player_sprite.rect)

        # Check proximity for NPCs
        for npc in self.npc_group:
            npc.check_proximity(player_sprite.rect)

        # Check time/flag triggers
        elapsed = (current_time - self._game_start_ticks) / 1000.0
        self.trigger_manager.update(elapsed)
        pending = self.trigger_manager.get_pending()
        if pending:
            self.objective_display.show(pending.text, pending.title)
        
        # Sync UI with player state
        self.player_ui.current_health = player_sprite.health
        
        # Combat resolution
        self._handle_combat_collisions()
        
        # State transitions
        self._check_game_over()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Rendering
    # ─────────────────────────────────────────────────────────────────────────
    
    def _check_game_over(self) -> None:
        """Check if game over conditions are met and handle transition."""
        player = self.player.sprite
        if player.is_dead and self._game_over_start_time is None:
            self._game_over_start_time = pg.time.get_ticks()
        
        # Wait for the game over delay before transitioning
        if (self._game_over_start_time is not None and 
            pg.time.get_ticks() - self._game_over_start_time >= self._GAME_OVER_DELAY_MS):
            # TODO: Add game over state transition
            print("Game Over!")
            # Reset game over state
            self._game_over_start_time = None
            player.reset()
    
    def draw(self, surface: pg.Surface) -> None:
        """
        Render the game state.
        
        Args:
            surface: Target surface for rendering.
        """
        # Background
        surface.blit(self.bg_image, (self.bg_x1, 0))
        surface.blit(self.bg_image, (self.bg_x2, 0))
        
        # UI layer
        self.player_ui.draw(surface)
        
        # Player
        self.player.sprite.draw(surface)
        
        # Enemies
        for enemy in self.obstacle_group:
            enemy.draw(surface)
            
        # Ambient creatures
        for ambient in self.ambient_group:
            ambient.draw(surface)

        # NPCs
        for npc in self.npc_group:
            npc.draw(surface)

        # Interaction point prompts ("Talk" indicators)
        for point in self.interaction_group:
            point.draw(surface)
        
        # Debug visualization
        if self.debug_mode:
            self._draw_debug_info(surface)

        # Objective overlay (drawn on top of everything)
        self.objective_display.draw(surface)

        # Notification banner (topmost layer)
        self.notification_banner.draw(surface)
    
    def _draw_debug_info(self, surface: pg.Surface) -> None:
        """
        Render debug visualization overlays.
        
        Args:
            surface: Target surface for debug rendering.
        """
        player_sprite = self.player.sprite
        
        # Player bounding rect (blue)
        pg.draw.rect(surface, (0, 100, 255), player_sprite.rect, 2)
        
        # Player attack hitbox (red, when active)
        if player_sprite.should_deal_damage():
            attack_hitbox = player_sprite.get_attack_hitbox()
            if attack_hitbox:
                # Semi-transparent fill
                hitbox_surface = pg.Surface(
                    (attack_hitbox.width, attack_hitbox.height),
                    pg.SRCALPHA,
                )
                hitbox_surface.fill((255, 0, 0, 80))
                surface.blit(hitbox_surface, attack_hitbox.topleft)
                
                # Solid outline
                pg.draw.rect(surface, (255, 0, 0), attack_hitbox, 2)
        
        # Player state info
        self._draw_player_debug(surface, player_sprite)
        
        # Enemy hitboxes and state info
        for sprite in self.obstacle_group:
            # Hitbox (green)
            pg.draw.rect(surface, (0, 255, 0), sprite.rect, 2)
            
            # Skeleton-specific debug info
            if isinstance(sprite, Skeleton):
                self._draw_skeleton_debug(surface, sprite)

        # Distance debug info (top-right)
        zone = self._get_spawn_zone()
        dist_font = pg.font.SysFont("monospace", 18)
        dist_lines = [
            f"Distance: {int(self.world_distance)} / {int(self._level_end_distance)}",
            f"Max reached: {int(self.max_distance_reached)}",
            f"Zone: max_skel={zone['max_skeletons']} delay={zone['delay']}ms",
        ]
        for i, line in enumerate(dist_lines):
            surf = dist_font.render(line, True, (255, 255, 100))
            surface.blit(surf, (surface.get_width() - surf.get_width() - 10, 10 + i * 22))
    
    def _draw_player_debug(
        self,
        surface: pg.Surface,
        player: Player,
    ) -> None:
        """
        Render player-specific debug information.
        
        Displays current state, animation frame, and attack info.
        
        Args:
            surface: Target surface for debug rendering.
            player: Player instance to debug.
        """
        font = pg.font.Font(None, 24)
        
        # State and frame info
        state_text = f"State: {player.state.name}"
        frame_text = f"Frame: {player.current_frame_index}"
        
        # Color based on attack phase
        if player.is_attacking:
            from src.game.entities.player import PlayerState
            from src.game.entities.combat_system import AttackPhase
            
            phase = player.attack_phase
            color = {
                AttackPhase.STARTUP: (100, 100, 255),   # Blue
                AttackPhase.ACTIVE: (255, 50, 50),       # Red
                AttackPhase.RECOVERY: (255, 200, 50),    # Yellow
                AttackPhase.COMPLETE: (128, 128, 128),   # Gray
            }.get(phase, (255, 255, 255))
            
            phase_text = f"Phase: {phase.name}"
            phase_surface = font.render(phase_text, True, color)
            surface.blit(
                phase_surface,
                (player.rect.x, player.rect.top - 55),
            )
        else:
            color = (255, 255, 255)
        
        state_surface = font.render(state_text, True, color)
        frame_surface = font.render(frame_text, True, (200, 200, 200))
        
        surface.blit(state_surface, (player.rect.x, player.rect.top - 40))
        surface.blit(frame_surface, (player.rect.x, player.rect.top - 25))
        
        # Hit frame indicator
        if player.should_deal_damage():
            hit_text = font.render("ACTIVE HIT FRAME!", True, (255, 50, 50))
            surface.blit(
                hit_text,
                (player.rect.centerx - 60, player.rect.top - 70),
            )
    
    def _draw_skeleton_debug(
        self,
        surface: pg.Surface,
        skeleton: Skeleton,
    ) -> None:
        """
        Render skeleton-specific debug information.
        
        Displays current state, animation frame, and hit frame indicators.
        
        Args:
            surface: Target surface for debug rendering.
            skeleton: Skeleton instance to debug.
        """
        font = pg.font.Font(None, 24)
        
        # State and frame info
        state_text = f"State: {skeleton.state.name}"
        frame_text = f"Frame: {skeleton.current_frame_index}"
        
        state_surface = font.render(state_text, True, (255, 255, 255))
        frame_surface = font.render(frame_text, True, (255, 255, 255))
        
        surface.blit(state_surface, (skeleton.rect.x, skeleton.rect.top - 40))
        surface.blit(frame_surface, (skeleton.rect.x, skeleton.rect.top - 25))
        
        # Hit frame indicator (yellow border when in hit frame)
        if skeleton.is_in_hit_frame():
            pg.draw.rect(surface, (255, 255, 0), skeleton.rect, 3)
            
            hit_text = font.render("HIT FRAME!", True, (255, 255, 0))
            surface.blit(
                hit_text,
                (skeleton.rect.centerx - 40, skeleton.rect.top - 55),
            )