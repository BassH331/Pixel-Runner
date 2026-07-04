"""
Game state module implementing the main gameplay loop.

This module manages the core game session including entity updates,
collision detection with frame-accurate hit detection, and state transitions.
"""

from __future__ import annotations
import os

from random import randint
from typing import TYPE_CHECKING, Final, Optional, Any
from dataclasses import dataclass

import pygame
import pygame as pg

from src.game.entities.enemy import Enemy
from v3x_zulfiqar_gideon import WorldEventManager, InteractionPoint, WorldLoader, Sky
from src.game.entities.wizard_npc import WizardNPC
from src.game.entities.generic_npc import GenericNPC
from src.game.entities.player import Player
from src.game.entities.skeleton import Skeleton, SkeletonState
from src.game.entities.fire_wizard import FireWizard, FireWizardState
from src.game.entities.green_monster import GreenMonster
from src.game.entities.boss_manager import BossManager
from src.game.ui import PlayerUI, ObjectiveDisplay, ObjectiveTriggerManager, NotificationBanner, TutorialOverlay
from v3x_zulfiqar_gideon import AssetManager, State

if TYPE_CHECKING:
    from v3x_zulfiqar_gideon import StateManager


# ─────────────────────────────────────────────────────────────────────────────
# Default spawn zones — ONLY used when level_1.json has no "spawn_zones" key.
# In normal gameplay, these are overridden by the JSON config.
#
# Each zone says:
#   min_dist / max_dist  — distance range this zone is active in
#   max_skeletons        — max alive at once in this zone
#   delay                — milliseconds between spawns
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULT_SPAWN_ZONES: list[dict] = [
    {"min_dist": 0,    "max_dist": 1000,        "max_skeletons": 2, "delay": 6000},
    {"min_dist": 1000, "max_dist": 3000,        "max_skeletons": 3, "delay": 4000},
    {"min_dist": 3000, "max_dist": 6000,        "max_skeletons": 5, "delay": 3000},
    {"min_dist": 6000, "max_dist": float("inf"), "max_skeletons": 6, "delay": 2000},
]


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
        
        # Gameplay Telemetry Tracker
        from src.game.debug.gameplay_tracker import GameplayTracker
        self.tracker = GameplayTracker()

        # Cloud-aggregated boss difficulty recommendation (fetched async at boss spawn)
        self._pending_difficulty_fetch: Optional[Any] = None
        self._pending_difficulty_boss: Optional[Any] = None

        self._prev_player_state: Optional[Any] = None
        self._prev_boss_state: Optional[Any] = None
        self._prev_entities_ids: set[tuple[int, str, Optional[int]]] = set()
        self._prev_player_health: Optional[float] = None
        self._logged_damage_this_tick: bool = False
        self._fps_clock: pg.time.Clock = pg.time.Clock()
        
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
        self.tutorial_overlay = TutorialOverlay()
        self._show_objective_on_start: bool = True
        self._show_tutorial_on_start: bool = True

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
        self._is_simulating = False
        self._simulation_timer = 0.0
        self._simulation_duration = 5.0

        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--start-dist", type=float, default=None)
        parser.add_argument("--duration", type=float, default=None)
        parser.add_argument("--target-event-id", type=int, default=None)
        args, _ = parser.parse_known_args()

        self._sim_type = "level"
        if args.start_dist is not None:
            self.world_distance = args.start_dist
            self._is_simulating = True
            self._sim_start_distance = args.start_dist
            self._sim_log_counter = 0
            self._show_objective_on_start = False
            self._show_tutorial_on_start = False
            if args.target_event_id is not None:
                self._sim_type = "level"
            else:
                self._sim_type = "wave"
                self._simulation_wave_enemies = []

            # Auto-play player by simulating K_RIGHT, unless a boss is active
            class AutoPlayKeys:
                def __init__(self, state):
                    self.state = state
                def __getitem__(self, key):
                    if key == pg.K_RIGHT:
                        if self.state._is_boss_active():
                            return False
                        return True
                    return False
            pg.key.get_pressed = lambda: AutoPlayKeys(self)  # type: ignore

        if args.duration is not None:
            self._simulation_duration = args.duration

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
        
        default_level = os.path.join("storyline", "prologue_covenant_of_ash.json")
        if not os.path.exists(default_level):
            default_level = os.path.join("game_data", "level_1.json")
        level_path = os.environ.get("GAME_LEVEL_PATH", default_level)
        self.level_data = WorldLoader.load_json(level_path)
        
        if self.level_data:
            from src.game.entities.hitbox_registry import HitboxRegistry
            HitboxRegistry.sync_with_level_config(self.level_data)
            self.BAT_GROUP_MIN_DELAY = self.level_data.get("spawn_rate_min", 5000)
            self.BAT_GROUP_MAX_DELAY = self.level_data.get("spawn_rate_max", 15000)

            # Level metadata
            self._level_name = self.level_data.get("level_name", self._level_name)
            self._level_end_distance = float(self.level_data.get("level_end_distance", self._level_end_distance))

            # Spawn zones — loaded from level_1.json "spawn_zones" array.
            # If the JSON doesn't have spawn_zones, we fall back to
            # _DEFAULT_SPAWN_ZONES (defined below this class).
            #
            # ╔══════════════════════════════════════════════════════╗
            # ║  TO CHANGE SPAWN BEHAVIOUR → edit level_1.json      ║
            # ║  The defaults below are ONLY used if the JSON key   ║
            # ║  "spawn_zones" is missing entirely.                  ║
            # ╚══════════════════════════════════════════════════════╝
            json_zones = self.level_data.get("spawn_zones", None)
            if json_zones:
                # Convert JSON sentinel (99999) to Python infinity for comparisons
                for zone in json_zones:
                    if zone["max_dist"] >= 99999:
                        zone["max_dist"] = float("inf")
                self._spawn_zones = json_zones
            else:
                self._spawn_zones = _DEFAULT_SPAWN_ZONES

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

            # --- Simulation Expected NPCs Setup ---
            self._simulation_npcs = {}
            self._simulation_expected_npcs = {}
            if self._is_simulating:
                from src.game.entities.hitbox_registry import HitboxRegistry
                for event in world_events:
                    etype = event.get("type")
                    if etype in ("npc", "boss"):
                        eid = event["id"]
                        params = event.get("params", {})
                        
                        if etype == "boss":
                            sprite_dir = params.get("sprite_dir", "")
                            folder_name = os.path.basename(sprite_dir.rstrip("/"))
                            npc_key = f"boss:{folder_name.lower()}" if sprite_dir else "boss"
                        elif params.get("npc_type", "generic") == "wizard":
                            npc_key = "wizard_npc"
                        else:
                            sprite_dir = params.get("sprite_dir", "")
                            folder_name = os.path.basename(sprite_dir.rstrip("/"))
                            if folder_name.lower() == "idle":
                                parent_dir = os.path.dirname(sprite_dir.rstrip("/"))
                                folder_name = os.path.basename(parent_dir)
                            npc_key = f"generic_npc_{folder_name.lower()}"
                        
                        margins = HitboxRegistry.get_margins(npc_key)
                        default_scale = margins.scale
                        
                        self._simulation_expected_npcs[eid] = {
                            "id": eid,
                            "type": etype,
                            "title": params.get("title", "NPC" if etype == "npc" else "Boss"),
                            "distance": float(event["distance"]),
                            "scale": float(params.get("scale", default_scale)),
                            "radius": float(params.get("radius", 160.0)),
                            "sprite_dir": params.get("sprite_dir", ""),
                            "registry_key": npc_key
                        }
            # ---------------------------------------

            for event in world_events:
                # Inject event metadata to params
                params = dict(event.get("params", {}))
                params["_event_id"] = event["id"]
                params["_event_distance"] = event["distance"]
                self.world_manager.add_event(
                    id=event["id"],
                    distance=event["distance"],
                    event_type=event["type"],
                    **params
                )
            # Optimize the list after loading
            self.world_manager.finalize()
        else:
            self.BAT_GROUP_MIN_DELAY = 5000
            self.BAT_GROUP_MAX_DELAY = 15000
            self._spawn_zones = _DEFAULT_SPAWN_ZONES
            self._bat_min_count = 3
            self._bat_max_count = 5
    
    def _setup_triggers(self) -> None:
        """Configure time-based and flag-based objective triggers."""

        # Congratulations on first skeleton kill
        self.trigger_manager.add_trigger(
            text="Well done, warrior! The undead fall before your blade. "
                 "Keep moving and stay vigilant for more threats ahead.",
            title="First kill!!",
            trigger_type="flag",
            flag_name="first_kill",
        )

    def _setup_interaction_points(self) -> None:
        """Initial interaction points (none — they spawn by distance now)."""
        pass  # Entities are spawned dynamically in _spawn_world_entities()

    def _get_spawn_zone(self) -> Optional[dict]:
        """Get the current spawn zone based on how far the player has traveled.

        Zones come from level_1.json → "spawn_zones".
        If the JSON didn't have that key, self._spawn_zones was set to
        _DEFAULT_SPAWN_ZONES during __init__.

        Returns the zone where min_dist <= max_distance_reached <= max_dist.
        """
        for zone in reversed(self._spawn_zones):
            min_dist = zone.get("min_dist", 0)
            max_dist = zone.get("max_dist")
            
            if self.max_distance_reached >= min_dist:
                if max_dist is None or self.max_distance_reached <= max_dist:
                    return zone
        return None

    def _setup_world_events(self) -> None:
        """Register handlers for world events. Scheduling is handled via JSON config."""
        self.world_manager.register_handler("interaction", self._handle_interaction_spawn)
        self.world_manager.register_handler("npc", self._handle_npc_spawn)
        self.world_manager.register_handler("enemy_wave", self._handle_enemy_wave)
        self.world_manager.register_handler("boss", self._handle_boss_spawn)

    def _handle_interaction_spawn(self, params: dict) -> None:
        """Handler for 'interaction' events."""
        self.interaction_group.add(InteractionPoint(
            x=self.width + 50,
            y=self.height - 100,
            text=params["text"],
            title=params["title"],
            proximity_radius=params["radius"],
            font_path="assets/graphics/Darinia/Darinia.ttf"
        ))

    def _handle_npc_spawn(self, params: dict) -> None:
        """Handler for 'npc' events.

        Supported npc_types (set in level_1.json → params → npc_type):
        ──────────────────────────────────────────────────────────────
        "wizard"   → uses the dedicated WizardNPC class.
        "generic"  → uses GenericNPC with any sprite folder.
                     Requires "sprite_dir" in params.

        Example JSON for a generic NPC::

            {
                "id": 6, "distance": 5000, "type": "npc",
                "params": {
                    "npc_type": "generic",
                    "sprite_dir": "assets/graphics/Goblin/Idle",
                    "title": "Goblin Scout",
                    "radius": 160,
                    "scale": 2.0,
                    "text": "Watch your back out there..."
                }
            }
        """
        npc_type = params.get("npc_type", "generic")
        
        # Position all NPCs on the ground level (aligned with their config feet position)
        from src.game.entities.hitbox_registry import HitboxRegistry
        if npc_type == "wizard":
            npc_key = "wizard_npc"
        else:
            sprite_dir = params.get("sprite_dir", "")
            folder_name = os.path.basename(sprite_dir.rstrip("/"))
            if folder_name.lower() == "idle":
                parent_dir = os.path.dirname(sprite_dir.rstrip("/"))
                folder_name = os.path.basename(parent_dir)
            npc_key = f"generic_npc_{folder_name.lower()}"

        margins = HitboxRegistry.get_margins(npc_key)
        ground_y = self.height - margins.ground_offset

        if npc_type == "wizard":
            npc = WizardNPC(
                x=self.width + 50,
                y=ground_y,
                text=params["text"],
                title=params["title"],
                scale=params.get("scale"),  # Respect level configuration scale
                proximity_radius=params.get("radius", 160),
            )
            setattr(npc, "event_id", params.get("_event_id"))
            setattr(npc, "event_distance", params.get("_event_distance"))
            self.npc_group.add(npc)
        else:
            # Generic NPC — works with any sprite folder
            npc = GenericNPC(
                x=self.width + 50,
                y=ground_y,
                sprite_dir=params["sprite_dir"],
                text=params["text"],
                title=params.get("title", "NPC"),
                scale=params.get("scale"),  # Respect level configuration scale
                proximity_radius=params.get("radius", 160),
                frame_duration=params.get("frame_duration", 0.15),
            )
            setattr(npc, "event_id", params.get("_event_id"))
            setattr(npc, "event_distance", params.get("_event_distance"))
            self.npc_group.add(npc)

        event_distance = float(params.get("_event_distance", self.world_distance))
        spawn_lead_px = 50
        setattr(npc, "world_x", event_distance + self.width + spawn_lead_px)
        setattr(npc, "spawn_world_distance", self.world_distance)

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
                self.spawn_skeleton(params)

    def _handle_boss_spawn(self, params: dict) -> None:
        """Handler for 'boss' events."""
        player_sprite = self.player.sprite
        if player_sprite is None:
            return

        boss = BossManager.spawn_boss(params, player_sprite, self.width, self.height)
        self.obstacle_group.add(boss)
        self.audio_manager.play_sound("skeleton_spawn")

        # Draw target text banner when boss spawns
        title = params.get("title", "Boss")
        self.notification_banner.show(
            f"WARNING: {title.upper()} APPROACHING!",
            notification="yellow"
        )

        # Kick off a non-blocking fetch for a cloud-aggregated difficulty
        # recommendation. The boss spawns off-screen with several seconds of
        # lead time before the fight starts, giving this time to complete; if
        # it doesn't, the boss just keeps the config it already loaded at
        # construction (see update() for where the result gets applied).
        boss_key = getattr(boss, "boss_key", None)
        if boss_key and hasattr(boss, "apply_config"):
            from src.game.services import DifficultyClient
            self._pending_difficulty_fetch = DifficultyClient.fetch_recommendation_async(boss_key)
            self._pending_difficulty_boss = boss
        if self.tracker.enabled and boss_key:
            self.tracker.set_boss_key(boss_key)

    # ─────────────────────────────────────────────────────────────────────────
    # State Lifecycle
    # ─────────────────────────────────────────────────────────────────────────
    
    def on_enter(self) -> None:
        """Initialize state when entering gameplay."""
        self.audio_manager.stop_all_sounds()
        self.bg_music_channel_id = self.audio_manager.play_sound(
            "game_loop",
            loop=True,
            volume=0.5,
        )
        self.player_ui.start_timer()

        # Show level notification banner on first entry
        if self._show_objective_on_start:
            self.notification_banner.show(self._level_name, notification="yellow")
            self._show_objective_on_start = False

        # Start tutorial on first entry
        if self._show_tutorial_on_start:
            self.tutorial_overlay.start()
            self._show_tutorial_on_start = False
        
    def on_exit(self) -> None:
        """Cleanup when leaving gameplay state."""
        if self.bg_music_channel_id is not None:
            self.audio_manager.stop_sound(self.bg_music_channel_id)
            self.bg_music_channel_id = None
        if self.tracker is not None:
            self.tracker.close()
        
    def handle_event(self, event: pg.event.Event) -> None:
        """
        Process input events.
        
        Args:
            event: Pygame event to process.
        """
        # While tutorial overlay is active, capture its input
        if self.tutorial_overlay.is_active:
            self.tutorial_overlay.handle_event(event)
            return

        # While objective overlay is active, only listen for dismiss input
        if self.objective_display.is_active:
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                self.objective_display.dismiss()
            elif event.type == pg.JOYBUTTONDOWN and event.button == 0:
                self.objective_display.dismiss()
            return

        # Check for interaction input (ENTER / gamepad btn 6).
        # Note: btn 2 is already bound to thrust-attack in Player._process_action_input,
        # so interact must use a different button or pressing it near an NPC would
        # simultaneously open dialogue and swing the sword.
        interact_pressed = (
            (event.type == pg.KEYDOWN and event.key == pg.K_RETURN) or
            (event.type == pg.JOYBUTTONDOWN and event.button == 6)
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
        if zone is not None and current_time >= self.next_skeleton_spawn_time:
            current_skeletons = sum(1 for sprite in self.obstacle_group 
                                 if isinstance(sprite, Skeleton))
            
            required_kills = zone.get("required_kills", 0)
            killed_count = zone.get("killed_count", 0)
            
            if required_kills == 0 or killed_count < required_kills:
                if current_skeletons < zone.get("max_skeletons", 0):
                    self.spawn_skeleton(zone)
                    self.next_skeleton_spawn_time = current_time + zone.get("delay", 6000)
                    print(f"[SPAWN] Skeleton spawned! "
                          f"alive={current_skeletons + 1}/{zone.get('max_skeletons', 0)} "
                          f"delay={zone.get('delay', 6000)}ms "
                          f"dist={int(self.max_distance_reached)} "
                          f"kills={killed_count}/{required_kills if required_kills > 0 else 'inf'}")
    
    def spawn_skeleton(self, zone: Optional[dict] = None) -> None:
        """Spawn a new skeleton at a random position on the right side of the screen."""
        # Calculate spawn position (off-screen right, but not too far)
        spawn_x = self.width + randint(100, 300)
        spawn_y = self.height - 50  # Same as initial spawn height
        
        # Get player sprite from GroupSingle
        player_sprite = self.player.sprite
        if player_sprite is None:
            return  # Can't spawn skeleton without player
            
        sprite_root = None
        behaviour_map = None
        tier = "minion"
        if zone:
            sprite_root = zone.get("sprite_root")
            behaviour_map = zone.get("behaviour_map")
            tier = zone.get("tier", "minion")
            
        # Create and add new skeleton
        skeleton = Skeleton(
            x=spawn_x,
            y=spawn_y,
            player=player_sprite,  # Pass the actual Player instance
            sprite_root=sprite_root,
            behaviour_map=behaviour_map,
            tier=tier
        )
        self.obstacle_group.add(skeleton)
        if zone is not None:
            skeleton.spawn_zone = zone
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
        
        # Wrap background images for infinite scroll, maintaining perfect contiguity
        if scroll_delta > 0:
            if self.bg_x1 <= -self.width:
                self.bg_x1 = self.bg_x2 + self.width
            if self.bg_x2 <= -self.width:
                self.bg_x2 = self.bg_x1 + self.width
        elif scroll_delta < 0:
            if self.bg_x1 >= self.width:
                self.bg_x1 = self.bg_x2 - self.width
            if self.bg_x2 >= self.width:
                self.bg_x2 = self.bg_x1 - self.width
    
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
        
        # (Skeleton spawning is handled by spawn_enemies() — no duplicate spawn here)
    
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
        colliderect = attack_hitbox.colliderect
        try_register_hit = player.try_register_hit
        
        for obstacle in self.obstacle_group:
            # Skip dead enemies
            if getattr(obstacle, "is_dead", False):
                continue
            
            # Skip invincible enemies
            if getattr(obstacle, "is_invincible", False):
                continue
            
            # Get enemy hitbox (prefer .hitbox, fallback to .rect)
            target_hitbox = getattr(obstacle, "low_hitbox", None) or getattr(obstacle, "hitbox", obstacle.rect)
            if target_hitbox is None:
                continue
            
            # Gate 2: Check hitbox collision
            if not colliderect(target_hitbox):
                continue
            
            # Gate 3: Check if already hit this attack (prevent duplicates)
            target_id = getattr(obstacle, "entity_id", None)
            if target_id is None:
                target_id = id(obstacle)
            
            if not try_register_hit(target_id):
                continue
            
            # ─────────────────────────────────────────────────────────────────
            # HIT CONFIRMED - Apply damage and effects
            # ─────────────────────────────────────────────────────────────────
            
            self._apply_player_damage_to_enemy(player, obstacle)
    
    def _apply_player_damage_to_enemy(
        self,
        player: Player,
        enemy: Enemy | Skeleton | FireWizard,
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
        target_health_before = getattr(enemy, "_health", getattr(enemy, "health", 0.0))
        if isinstance(enemy, (Skeleton, FireWizard)):
            enemy.take_damage(damage)
        elif isinstance(enemy, Enemy):
            enemy.take_damage(damage, knockback)
        elif hasattr(enemy, 'take_damage'):
            # Fallback: call take_damage dynamically
            try:
                enemy.take_damage(damage, knockback)  # type: ignore
            except TypeError:
                enemy.take_damage(damage)  # type: ignore
        else:
            # Non-damageable obstacle - just destroy it
            enemy.kill()
            
        if self.tracker.enabled:
            self.tracker.log_event("damage_dealt", {
                "attacker": "player",
                "target": enemy.__class__.__name__,
                "target_is_boss": getattr(enemy, "is_boss", False),
                "damage": damage,
                "target_health_before": target_health_before,
                "target_health_after": getattr(enemy, "_health", getattr(enemy, "health", 0.0)),
                "world_distance": self.world_distance
            })
        
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
        
        if isinstance(enemy, (Skeleton, FireWizard)):
            is_dead = (
                (enemy.state == SkeletonState.DEATH) if isinstance(enemy, Skeleton)
                else (enemy.state == FireWizardState.DEATH)
            )
            if is_dead and not getattr(enemy, "_death_sound_played", False):
                self.audio_manager.play_sound("skeleton_death")
                setattr(enemy, "_death_sound_played", True)
                
                # Check for Boss defeat
                if getattr(enemy, "is_boss", False):
                    if getattr(enemy, "tier", "boss") == "boss":
                        self._level_complete = True
                        self.objective_display.show(
                            f"You have defeated the mighty {getattr(enemy, 'boss_title', 'Boss')}! "
                            "The land is saved, and your name shall be sung in legend. "
                            "Victory is yours!",
                            "Victory Achieved!"
                        )
                    else:
                        self.notification_banner.show(
                            f"VICTORY: {getattr(enemy, 'boss_title', 'Mini-boss').upper()} DEFEATED!",
                            notification="green"
                        )

                # Track zone kills
                zone = getattr(enemy, "spawn_zone", None)
                if zone is not None:
                    zone["killed_count"] = zone.get("killed_count", 0) + 1
                    print(f"[KILL] Skeleton from zone killed! "
                          f"kills={zone['killed_count']}/{zone.get('required_kills', 0)}")
                
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

    def _is_boss_active(self) -> bool:
        """Check if any boss is currently active and alive in the scene."""
        return BossManager.is_boss_active(self.obstacle_group)

    def _manage_skeleton_spawns(self) -> None:
        """Maintain skeleton population within configured limits."""
        zone = self._get_spawn_zone()
        if zone is None:
            return
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
            if isinstance(obstacle, (Skeleton, FireWizard, GreenMonster)):
                self._handle_skeleton_attack(player, obstacle)

    def _handle_skeleton_attack(self, player: Player, skeleton: Skeleton | FireWizard | GreenMonster) -> None:
        """
        Handle skeleton attack collision with frame-precise damage.
        
        Args:
            player: Player sprite instance.
            skeleton: Attacking skeleton/wizard instance.
        """
        # Gate 1: Entity must be in attack state
        state = getattr(skeleton, "state", None)
        if state is None or "ATTACK" not in getattr(state, "name", ""):
            return
        
        # Gate 2: Must be on a hit frame and not already registered
        if not skeleton.should_deal_damage():
            return 
        
        # Gate 3: Check hitbox collision (use skeleton's attack hitbox if available)
        skeleton_hitbox = getattr(skeleton, 'get_attack_hitbox', None)
        if skeleton_hitbox is not None:
            skeleton_hitbox = skeleton_hitbox()
        else:
            skeleton_hitbox = skeleton.rect
            
        if skeleton_hitbox is None or not skeleton_hitbox.colliderect(player.rect):
            return
        
        # Always register the hit attempt to prevent multi-hit exploitation.
        # This ensures the skeleton can't "save" its hit for when i-frames end.
        skeleton.register_hit(id(player))
        
        # Gate 4: Player invincibility check (handled inside take_damage)
        damage = skeleton.get_current_attack_damage()
        player_health_before = player.health
        damage_applied = player.take_damage(damage)
        
        if damage_applied and self.tracker.enabled:
            self.tracker.log_event("damage_received", {
                "attacker": skeleton.__class__.__name__,
                "attacker_is_boss": getattr(skeleton, "is_boss", False),
                "damage": damage,
                "player_health_before": player_health_before,
                "player_health_after": player.health,
                "world_distance": self.world_distance
            })
            self._logged_damage_this_tick = True
            
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
        
        trigger_flash = getattr(player, 'trigger_hit_flash', None)
        if trigger_flash:
            trigger_flash()
            
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
        apply_kb = getattr(player, 'apply_knockback', None)
        if apply_kb:
            apply_kb(force)
        else:
            # Fallback: Direct position offset with screen bounds clamping
            player.rect.x += int(force)
            player.rect.left = max(player.rect.left, 0)
            
            screen_width = pg.display.get_surface().get_width()
            player.rect.right = min(player.rect.right, screen_width)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Main Update Loop
    # ─────────────────────────────────────────────────────────────────────────
    def _write_simulation_report(self) -> None:
        import json
        import os
        from src.game.entities.hitbox_registry import HitboxRegistry
        
        if getattr(self, "_sim_type", "level") == "wave":
            overall_passed = len(self._simulation_wave_enemies) > 0
            
            report_data = {
                "status": "PASSED" if overall_passed else "FAILED",
                "timestamp": pg.time.get_ticks(),
                "duration_ms": self._simulation_timer,
                "start_distance": getattr(self, "_sim_start_distance", 0.0),
                "final_distance": self.world_distance,
                "scroll_speed": self.max_bg_scroll_speed,
                "type": "wave",
                "enemies": self._simulation_wave_enemies
            }
            
            markdown_lines = [
                "# Pixel-Runner Wave Simulation Report",
                "",
                f"**Overall Status:** {'PASSED ✅' if overall_passed else 'FAILED ❌'}",
                f"**Final Distance:** {self.world_distance:.1f}",
                f"**Simulation Duration:** {self._simulation_timer:.1f}ms",
                f"**Dynamic Enemies Spawned:** {len(self._simulation_wave_enemies)}",
                ""
            ]
            
            if not overall_passed:
                markdown_lines.append("## Issues Found")
                markdown_lines.append("1. No dynamic enemies spawned from configured spawn zones during the simulation.")
                markdown_lines.append("")
            
            for enemy in self._simulation_wave_enemies:
                eid = enemy["id"]
                markdown_lines.append(f"### Enemy #{eid} ({enemy['type'].capitalize()})")
                markdown_lines.append(f"- **Spawned at world_distance:** {enemy['spawn_distance']:.1f}m")
                markdown_lines.append(f"- **Initial Screen Position:** ({enemy['initial_x']}, {enemy['initial_y']})")
                
                phy = enemy.get("first_physical_collision")
                if phy:
                    markdown_lines.append(f"- **Physical Collision:** reached at world_distance={phy['world_distance']:.1f}m (Screen: ({phy['screen_x']}, {phy['screen_y']}))")
                else:
                    markdown_lines.append(f"- **Physical Collision:** None (no player collision detected)")
                
                positions = enemy.get("positions", [])
                if positions:
                    markdown_lines.append(f"- **Frames Tracked:** {len(positions)}")
                    samples = []
                    sample_indices = [0, len(positions)//2, len(positions)-1]
                    for si in sample_indices:
                        if 0 <= si < len(positions):
                            samples.append(f"Frame {si}: ({positions[si][0]}, {positions[si][1]})")
                    markdown_lines.append(f"- **Position Samples:** {', '.join(samples)}")
                markdown_lines.append("")
                
            os.makedirs("scratch", exist_ok=True)
            with open("scratch/simulation_report.json", "w") as f:
                json.dump(report_data, f, indent=4)
                
            with open("scratch/simulation_report.md", "w") as f:
                f.write("\n".join(markdown_lines))
                
            print(f"\n{'='*60}")
            print(f"[WAVE SIMULATION REPORT] Status: {report_data['status']}")
            print(f"  Distance: {report_data.get('start_distance', 0):.0f} → {self.world_distance:.0f}")
            print(f"  Duration: {self._simulation_timer:.0f}ms")
            print(f"  Dynamic Enemies Spawned: {len(self._simulation_wave_enemies)}")
            
            if len(self._simulation_wave_enemies) > 0:
                first_enemy = self._simulation_wave_enemies[0]
                print(f"  First Spawned Enemy (Skeleton):")
                print(f"    - Spawned at world_dist: {first_enemy['spawn_distance']:.1f}")
                print(f"    - Initial Screen Position: ({first_enemy['initial_x']}, {first_enemy['initial_y']})")
                phy = first_enemy.get("first_physical_collision")
                if phy:
                    print(f"    - First Physical Collision: world_dist={phy['world_distance']:.1f} (Screen: ({phy['screen_x']}, {phy['screen_y']}))")
                else:
                    print(f"    - First Physical Collision: None detected")
            else:
                print("  ⚠ No dynamic enemies spawned.")
            print(f"{'='*60}")
            return

        report_data = {
            "status": "PASSED",
            "timestamp": pg.time.get_ticks(),
            "duration_ms": self._simulation_timer,
            "start_distance": getattr(self, "_sim_start_distance", 0.0),
            "final_distance": self.world_distance,
            "scroll_speed": self.max_bg_scroll_speed,
            "npcs": []
        }
        
        markdown_lines = [
            "# Pixel-Runner Simulation Report",
            "",
            f"**Final Distance:** {self.world_distance:.1f}",
            f"**Simulation Duration:** {self._simulation_timer:.1f}ms",
            f"**Scroll Speed:** {self.max_bg_scroll_speed} px/frame",
            ""
        ]
        
        overall_passed = True
        issues: list[str] = []
        
        for eid, exp in self._simulation_expected_npcs.items():
            # Load what entity_dimensions.json has for this NPC
            ntype = exp["type"]
            reg_key = exp.get("registry_key", "generic_npc_")
            
            reg_margins = HitboxRegistry.get_margins(reg_key)
            
            npc_res: dict = {
                "id": eid,
                "type": ntype,
                "title": exp["title"],
                "registry_key": reg_key,
                # What level_1.json says (params)
                "json_distance": exp["distance"],
                "json_scale": exp["scale"],
                "json_radius": exp["radius"],
                # What entity_dimensions.json says
                "registry_scale": reg_margins.scale,
                "registry_ground_offset": reg_margins.ground_offset,
                "spawned": False,
                "status": "NOT SPAWNED",
                "issues": []
            }
            
            # === Consistency Check 1: JSON scale vs Registry scale ===
            if abs(exp["scale"] - reg_margins.scale) > 0.01:
                npc_res["issues"].append(
                    f"Scale mismatch: level JSON has {exp['scale']}, "
                    f"entity_dimensions.json has {reg_margins.scale} for '{reg_key}'"
                )
            
            spawned_data = self._simulation_npcs.get(eid)
            if spawned_data:
                npc_res["spawned"] = True
                npc_res["actual_spawn_distance"] = spawned_data["spawn_distance"]
                npc_res["actual_scale"] = spawned_data["actual_scale"]
                npc_res["actual_radius"] = spawned_data["actual_radius"]
                npc_res["actual_width"] = spawned_data["actual_width"]
                npc_res["actual_height"] = spawned_data["actual_height"]
                npc_res["initial_screen_x"] = spawned_data["initial_x"]
                npc_res["initial_screen_y"] = spawned_data["initial_y"]
                npc_res["first_physical_collision"] = spawned_data.get("first_physical_collision")
                npc_res["first_proximity_collision"] = spawned_data.get("first_proximity_collision")
                
                positions = spawned_data["positions"]
                npc_res["total_frames_tracked"] = len(positions)
                
                # === Consistency Check 2: Did the NPC spawn at the right world_distance? ===
                dist_delta = abs(spawned_data["spawn_distance"] - exp["distance"])
                if dist_delta > 20:  # Allow small tolerance for frame timing
                    npc_res["issues"].append(
                        f"Spawn distance mismatch: expected trigger at {exp['distance']}, "
                        f"but first detected at world_distance={spawned_data['spawn_distance']:.1f} "
                        f"(delta={dist_delta:.1f})"
                    )
                
                # === Consistency Check 3: Does actual scale match JSON config? ===
                if abs(spawned_data["actual_scale"] - exp["scale"]) > 0.01:
                    npc_res["issues"].append(
                        f"Runtime scale mismatch: JSON says {exp['scale']}, "
                        f"but NPC spawned with scale={spawned_data['actual_scale']}"
                    )
                
                # === Consistency Check 4: Does actual radius match JSON config? ===
                if abs(spawned_data["actual_radius"] - exp["radius"]) > 0.01:
                    npc_res["issues"].append(
                        f"Runtime radius mismatch: JSON says {exp['radius']}, "
                        f"but NPC spawned with radius={spawned_data['actual_radius']}"
                    )
                
                # === Consistency Check 5: Scrolling behavior ===
                if len(positions) >= 5:
                    moved_left = positions[-1][0] < positions[0][0]
                    if not moved_left:
                        npc_res["issues"].append(
                            f"NPC did not scroll left: start_x={positions[0][0]}, "
                            f"end_x={positions[-1][0]}"
                        )
                    
                    # Calculate actual scroll rate
                    x_delta = positions[0][0] - positions[-1][0]
                    npc_res["total_x_scrolled"] = x_delta
                    npc_res["avg_scroll_per_frame"] = x_delta / len(positions) if positions else 0
                else:
                    # Too few frames to assess scrolling — spawned near timeout boundary
                    npc_res["insufficient_data"] = True

                # === Consistency Check 6: Screen position accuracy ===
                if "world_x" in spawned_data and spawned_data["world_x"] is not None:
                    last_x = positions[-1][0]
                    expected_x = spawned_data["world_x"] - self.world_distance
                    x_error = abs(last_x - expected_x)
                    npc_res["expected_screen_x"] = expected_x
                    npc_res["actual_screen_x"] = last_x
                    npc_res["screen_x_error"] = x_error
                    if x_error > 5:
                        npc_res["issues"].append(
                            f"Screen position mismatch: expected x={expected_x:.1f}, "
                            f"actual x={last_x:.1f}, error={x_error:.1f}"
                        )
                
                # === Position sample: first, middle, last frames ===
                samples = []
                sample_indices = [0, len(positions)//2, len(positions)-1]
                for si in sample_indices:
                    if 0 <= si < len(positions):
                        samples.append({"frame": si, "x": positions[si][0], "y": positions[si][1]})
                npc_res["position_samples"] = samples
                
                # Determine pass/fail
                if npc_res["issues"]:
                    npc_res["status"] = "FAILED"
                    overall_passed = False
                elif npc_res.get("insufficient_data"):
                    npc_res["status"] = "INCONCLUSIVE (too few frames)"
                else:
                    npc_res["status"] = "PASSED"
            else:
                if self.world_distance < exp["distance"]:
                    npc_res["status"] = "SKIPPED (not reached)"
                else:
                    npc_res["status"] = "FAILED"
                    npc_res["issues"].append(
                        f"NPC should have spawned at distance {exp['distance']}, "
                        f"world reached {self.world_distance:.1f} but NPC never appeared"
                    )
                    overall_passed = False
            
            issues.extend(npc_res["issues"])
            report_data["npcs"].append(npc_res)
            
            # Build markdown section
            status_emoji = "✅" if npc_res["status"] == "PASSED" else "❌" if "FAILED" in npc_res["status"] else "⚠️"
            markdown_lines.append(f"### NPC #{eid}: {exp['title']} ({status_emoji} {npc_res['status']})")
            markdown_lines.append(f"- **Registry Key:** `{reg_key}`")
            markdown_lines.append(f"- **Trigger Distance:** JSON={exp['distance']}m | Spawned at={npc_res.get('actual_spawn_distance', 'N/A')}m")
            markdown_lines.append(f"- **Scale:** JSON={exp['scale']} | Registry={reg_margins.scale} | Runtime={npc_res.get('actual_scale', 'N/A')}")
            markdown_lines.append(f"- **Proximity Radius:** JSON={exp['radius']} | Runtime={npc_res.get('actual_radius', 'N/A')}")
            if spawned_data:
                markdown_lines.append(f"- **Image Dimensions:** {npc_res['actual_width']}×{npc_res['actual_height']}")
                markdown_lines.append(f"- **Initial Screen Pos:** ({npc_res['initial_screen_x']}, {npc_res['initial_screen_y']})")
                markdown_lines.append(f"- **Frames Tracked:** {npc_res['total_frames_tracked']}")
                markdown_lines.append(f"- **Total X Scrolled:** {npc_res.get('total_x_scrolled', 'N/A')}px")
                if npc_res.get("first_physical_collision"):
                    phy = npc_res["first_physical_collision"]
                    markdown_lines.append(f"- **Physical Collision:** reached at world_distance={phy['world_distance']:.1f}m (level editor trigger={phy['trigger_distance']}m, delta={phy['delta']:.1f}m)")
                else:
                    markdown_lines.append(f"- **Physical Collision:** None (no bounding box overlap)")
                
                if npc_res.get("first_proximity_collision"):
                    prox = npc_res["first_proximity_collision"]
                    markdown_lines.append(f"- **Proximity Collision:** reached at world_distance={prox['world_distance']:.1f}m (level editor trigger={prox['trigger_distance']}m, delta={prox['delta']:.1f}m)")
                else:
                    markdown_lines.append(f"- **Proximity Collision:** None (no interaction radius overlap)")
                if npc_res.get("position_samples"):
                    markdown_lines.append(f"- **Position Samples:**")
                    for s in npc_res["position_samples"]:
                        markdown_lines.append(f"  - Frame {s['frame']}: ({s['x']}, {s['y']})")
            else:
                markdown_lines.append(f"- **Spawned:** No")
            
            if npc_res["issues"]:
                markdown_lines.append(f"- **⚠ Issues:**")
                for issue in npc_res["issues"]:
                    markdown_lines.append(f"  - {issue}")
            markdown_lines.append("")
            
        if not overall_passed:
            report_data["status"] = "FAILED"
        
        # Summary section
        if issues:
            markdown_lines.insert(2, f"**Overall Status:** FAILED ❌")
            markdown_lines.insert(3, "")
            markdown_lines.insert(4, "## Issues Found")
            for i, issue in enumerate(issues):
                markdown_lines.insert(5 + i, f"{i+1}. {issue}")
            markdown_lines.insert(5 + len(issues), "")
        else:
            markdown_lines.insert(2, f"**Overall Status:** PASSED ✅")
        
        os.makedirs("scratch", exist_ok=True)
        with open("scratch/simulation_report.json", "w") as f:
            json.dump(report_data, f, indent=4)
            
        with open("scratch/simulation_report.md", "w") as f:
            f.write("\n".join(markdown_lines))
            
        print(f"\n{'='*60}")
        print(f"[SIMULATION REPORT] Status: {report_data['status']}")
        print(f"  Distance: {report_data.get('start_distance', 0):.0f} → {self.world_distance:.0f}")
        print(f"  Duration: {self._simulation_timer:.0f}ms")
        for npc in report_data["npcs"]:
            status = npc['status']
            print(f"  NPC #{npc['id']} ({npc['title']}): {status}")
            if npc.get("first_physical_collision"):
                phy = npc["first_physical_collision"]
                print(f"    - Physical Collision: world_dist={phy['world_distance']:.0f} (delta={phy['delta']:.0f})")
            if npc.get("first_proximity_collision"):
                prox = npc["first_proximity_collision"]
                print(f"    - Proximity Collision: world_dist={prox['world_distance']:.0f} (delta={prox['delta']:.0f})")
            if npc.get("issues"):
                for issue in npc["issues"]:
                    print(f"    ⚠ {issue}")
        print(f"{'='*60}")

    def update(self, dt: float) -> None:
        """
        Main game update tick.
        
        Args:
            dt: Delta time since last update in seconds.
        """

        # Freeze gameplay while tutorial or objective overlay is active
        if self.tutorial_overlay.is_active:
            self.tutorial_overlay.update(dt)
            return

        if self.objective_display.is_active:
            return

        # Update notification banner (runs independently of gameplay freeze)
        self.notification_banner.update(dt)

        # Apply a cloud-aggregated difficulty recommendation once it's ready
        # (kicked off in _handle_boss_spawn). Fails silently -- if it's not
        # ready or the fetch failed, the boss just keeps its current config.
        if self._pending_difficulty_fetch is not None:
            if self._pending_difficulty_fetch.is_done():
                result = self._pending_difficulty_fetch.result()
                boss = self._pending_difficulty_boss
                if result is not None and boss is not None and hasattr(boss, "apply_config"):
                    boss.apply_config(result)
                    if hasattr(boss, "_max_mana"):
                        boss._mana = boss._max_mana
                self._pending_difficulty_fetch = None
                self._pending_difficulty_boss = None

        current_time = pg.time.get_ticks()
        
        # Enemy spawning
        self.spawn_enemies(current_time)
        
        # Calculate scroll speed based on player movement
        player_sprite = self.player.sprite
        if player_sprite.is_running and not self._is_boss_active():
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
        for npc in self.npc_group:
            if hasattr(npc, "world_x"):
                npc.rect.x = int(getattr(npc, "world_x") - self.world_distance)
                npc.update(dt, scroll_speed=0)
            else:
                npc.update(dt, scroll_speed=self.bg_scroll_speed)

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
        self.player_ui.distance = self.max_distance_reached
        self.player_ui.current_mana = player_sprite.mana
        self.player_ui.max_mana = player_sprite.max_mana
        self.player_ui.current_stamina = player_sprite.stamina
        self.player_ui.max_stamina = player_sprite.max_stamina
        
        # Combat resolution
        self._handle_combat_collisions()
        
        # State transitions
        self._check_game_over()

        if self._is_simulating:
            self._sim_log_counter += 1
            
            if getattr(self, "_sim_type", "level") == "wave":
                # Track dynamic spawned skeletons (enemies)
                for obstacle in self.obstacle_group:
                    if isinstance(obstacle, Skeleton) and not getattr(obstacle, "is_boss", False):
                        if not getattr(obstacle, "_sim_tracked", False):
                            setattr(obstacle, "_sim_tracked", True)
                            enemy_id = len(self._simulation_wave_enemies) + 1
                            setattr(obstacle, "_sim_id", enemy_id)
                            self._simulation_wave_enemies.append({
                                "id": enemy_id,
                                "type": "skeleton",
                                "spawn_distance": float(self.world_distance),
                                "initial_x": obstacle.rect.x,
                                "initial_y": obstacle.rect.y,
                                "first_physical_collision": None,
                                "positions": []
                            })
                            print(f"[SIM] Dynamic enemy #{enemy_id} (Skeleton) SPAWNED at world_dist={self.world_distance:.0f} screen=({obstacle.rect.x},{obstacle.rect.y})")
                
                # Update positions and collisions for tracked wave enemies
                for obstacle in self.obstacle_group:
                    if isinstance(obstacle, Skeleton) and getattr(obstacle, "_sim_tracked", False):
                        enemy_id = getattr(obstacle, "_sim_id")
                        enemy_data = self._simulation_wave_enemies[enemy_id - 1]
                        
                        if enemy_data["first_physical_collision"] is None:
                            if player_sprite.rect.colliderect(obstacle.rect):
                                enemy_data["first_physical_collision"] = {
                                    "world_distance": float(self.world_distance),
                                    "screen_x": obstacle.rect.x,
                                    "screen_y": obstacle.rect.y
                                }
                                print(f"[SIM] Dynamic enemy #{enemy_id} (Skeleton) PHYSICAL COLLISION at world_dist={self.world_distance:.0f}")
                        
                        enemy_data["positions"].append((obstacle.rect.x, obstacle.rect.y))
                
                # Real-time frame logging for wave mode
                active_enemies = [
                    f"#{getattr(s, '_sim_id')}@({s.rect.x},{s.rect.y})"
                    for s in self.obstacle_group
                    if isinstance(s, Skeleton) and getattr(s, "_sim_tracked", False)
                ]
                print(f"[SIM] frame={self._sim_log_counter} dist={self.world_distance:.0f} player@({player_sprite.rect.x},{player_sprite.rect.y}) | {' '.join(active_enemies)}")
            
            else:
                # 1. Track any NPCs and Bosses currently in the scene
                sim_targets = []
                for npc in self.npc_group:
                    eid = getattr(npc, "event_id", None)
                    if eid is not None:
                        sim_targets.append((npc, "npc"))
                for obstacle in self.obstacle_group:
                    if getattr(obstacle, "is_boss", False):
                        eid = getattr(obstacle, "event_id", None)
                        if eid is not None:
                            sim_targets.append((obstacle, "boss"))

                for target, ttype in sim_targets:
                    eid = getattr(target, "event_id")
                    if eid not in self._simulation_npcs:
                        self._simulation_npcs[eid] = {
                            "id": eid,
                            "type": ttype if ttype == "boss" else ("wizard" if target.__class__.__name__ == "WizardNPC" else "generic"),
                            "title": getattr(target, "title" if ttype == "npc" else "boss_title", "Entity"),
                            "spawn_distance": self.world_distance,
                            "actual_scale": float(getattr(target, "scale", 1.0)),
                            "actual_radius": float(getattr(target, "proximity_radius", 160.0)),
                            "actual_width": target.image.get_width() if target.image else 0,
                            "actual_height": target.image.get_height() if target.image else 0,
                            "initial_x": target.rect.x,
                            "initial_y": target.rect.y,
                            "world_x": getattr(target, "world_x", None),
                            "positions": [],
                            "first_physical_collision": None,
                            "first_proximity_collision": None
                        }
                        # Log spawn event
                        print(f"[SIM] NPC #{eid} '{self._simulation_npcs[eid]['title']}' SPAWNED "
                              f"at world_dist={self.world_distance:.0f} "
                              f"screen=({target.rect.x},{target.rect.y}) "
                              f"scale={self._simulation_npcs[eid]['actual_scale']} "
                              f"radius={self._simulation_npcs[eid]['actual_radius']} "
                              f"img={self._simulation_npcs[eid]['actual_width']}x"
                              f"{self._simulation_npcs[eid]['actual_height']}")
                    
                    # Track collisions in real-time
                    sim_npc = self._simulation_npcs[eid]
                    if sim_npc["first_physical_collision"] is None:
                        if player_sprite.rect.colliderect(target.rect):
                            event_dist = float(getattr(target, "event_distance", 0.0))
                            sim_npc["first_physical_collision"] = {
                                "world_distance": float(self.world_distance),
                                "trigger_distance": event_dist,
                                "delta": float(self.world_distance - event_dist)
                            }
                            print(f"[SIM] NPC #{eid} '{sim_npc['title']}' PHYSICAL COLLISION at world_dist={self.world_distance:.0f} (delta={self.world_distance - event_dist:.0f})")
                    
                    if sim_npc["first_proximity_collision"] is None:
                        if ttype == "npc" and getattr(target, "_in_range", False):
                            event_dist = float(getattr(target, "event_distance", 0.0))
                            sim_npc["first_proximity_collision"] = {
                                "world_distance": float(self.world_distance),
                                "trigger_distance": event_dist,
                                "delta": float(self.world_distance - event_dist)
                            }
                            print(f"[SIM] NPC #{eid} '{sim_npc['title']}' PROXIMITY COLLISION at world_dist={self.world_distance:.0f} (delta={self.world_distance - event_dist:.0f})")
                    
                    # Append coordinate history
                    self._simulation_npcs[eid]["positions"].append((target.rect.x, target.rect.y))
                
                # Real-time log every frame
                npc_info = []
                for target, ttype in sim_targets:
                    eid = getattr(target, "event_id")
                    npc_info.append(f"#{eid}@({target.rect.x},{target.rect.y})")
                print(f"[SIM] frame={self._sim_log_counter} dist={self.world_distance:.0f} player@({player_sprite.rect.x},{player_sprite.rect.y}) | {' '.join(npc_info)}")

                # 2. Check for early exit condition:
                # If we have expected NPCs in range, and all triggered expected NPCs have spawned and are off-screen or dead:
                triggered_expected_eids = [
                    eid for eid, exp in self._simulation_expected_npcs.items()
                    if exp["distance"] <= self.world_distance
                ]
                if triggered_expected_eids:
                    all_spawned = all(eid in self._simulation_npcs for eid in triggered_expected_eids)
                    all_offscreen = False
                    if all_spawned:
                        all_offscreen = True
                        for npc in self.npc_group:
                            eid = getattr(npc, "event_id", None)
                            if eid in triggered_expected_eids:
                                if npc.rect.right >= 0:
                                    all_offscreen = False
                                    break
                        if all_offscreen:
                            for obstacle in self.obstacle_group:
                                eid = getattr(obstacle, "event_id", None)
                                if eid in triggered_expected_eids:
                                    if getattr(obstacle, "is_boss", False):
                                        state = getattr(obstacle, "state", None)
                                        if state != SkeletonState.DEATH and getattr(obstacle, "_health", 0) > 0:
                                            all_offscreen = False
                                            break
                    if all_spawned and all_offscreen:
                        self._write_simulation_report()
                        pg.quit()
                        exit(0)

            # 3. Safety timeout check
            self._simulation_timer += dt
            if self._simulation_timer >= self._simulation_duration * 1000:
                self._write_simulation_report()
                pg.quit()
                exit(0)
                
        # ─────────────────────────────────────────────────────────────────────
        # Telemetry Tracking & Logging System
        # ─────────────────────────────────────────────────────────────────────
        if self.tracker.enabled:
            self.tracker.last_world_distance = self.world_distance
            if getattr(self.tracker, "damage_logged_this_frame", False):
                self._logged_damage_this_tick = True
                self.tracker.damage_logged_this_frame = False
                
            # 1. Update FPS clock
            self._fps_clock.tick()
            fps = self._fps_clock.get_fps()
            
            # 2. Check player state change
            current_player_state = player_sprite.state
            prev_p_state = self._prev_player_state
            if prev_p_state is not None and current_player_state != prev_p_state:
                self.tracker.log_event("player_state_changed", {
                    "old_state": getattr(prev_p_state, "name", "").lower(),
                    "new_state": getattr(current_player_state, "name", "").lower(),
                    "frame": self._frame_count,
                    "world_distance": self.world_distance
                })
            self._prev_player_state = current_player_state
            
            # 3. Check boss state change
            from src.game.entities.boss_manager import BossManager
            boss = BossManager.get_active_boss(self.obstacle_group)
            prev_b_state = self._prev_boss_state
            if boss:
                current_boss_state = boss.state
                if prev_b_state is not None and current_boss_state != prev_b_state:
                    self.tracker.log_event("boss_state_changed", {
                        "old_state": getattr(prev_b_state, "name", "").lower(),
                        "new_state": getattr(current_boss_state, "name", "").lower(),
                        "frame": self._frame_count,
                        "world_distance": self.world_distance
                    })
                self._prev_boss_state = current_boss_state
            else:
                if prev_b_state is not None:
                    self.tracker.log_event("boss_state_changed", {
                        "old_state": getattr(prev_b_state, "name", "").lower(),
                        "new_state": "none",
                        "frame": self._frame_count,
                        "world_distance": self.world_distance
                    })
                    self._prev_boss_state = None
                    
            # 4. Spawns and despawns of entities
            current_entities = {
                (id(e), e.__class__.__name__, getattr(e, "event_id", None))
                for e in list(self.obstacle_group) + list(self.npc_group)
            }
            if self._prev_entities_ids:
                spawned = current_entities - self._prev_entities_ids
                despawned = self._prev_entities_ids - current_entities
                for eid, class_name, event_id in spawned:
                    self.tracker.log_event("entity_spawn", {
                        "entity_id": eid,
                        "type": class_name,
                        "event_id": event_id,
                        "frame": self._frame_count,
                        "world_distance": self.world_distance
                    })
                for eid, class_name, event_id in despawned:
                    self.tracker.log_event("entity_despawn", {
                        "entity_id": eid,
                        "type": class_name,
                        "event_id": event_id,
                        "frame": self._frame_count,
                        "world_distance": self.world_distance
                    })
            self._prev_entities_ids = current_entities
            
            # 5. Check player health changes dynamically (fallback for hazards/projectiles)
            if self._prev_player_health is not None and player_sprite.health < self._prev_player_health:
                if not getattr(self, "_logged_damage_this_tick", False):
                    # Check if any fireball overlaps the player
                    has_fireball = any(
                        e.__class__.__name__ == "Fireball" and e.rect.colliderect(player_sprite.rect)
                        for e in self.obstacle_group
                    )
                    self.tracker.log_event("damage_received", {
                        "attacker": "Fireball" if has_fireball else "Environment",
                        "attacker_is_boss": False,
                        "damage": self._prev_player_health - player_sprite.health,
                        "player_health_before": self._prev_player_health,
                        "player_health_after": player_sprite.health,
                        "world_distance": self.world_distance
                    })
            self._prev_player_health = player_sprite.health
            self._logged_damage_this_tick = False
            
            # 6. Periodic frame sampling
            sample_n = self.tracker.config["sample_every_n_frames"]
            if self._frame_count % sample_n == 0:
                self.tracker.sample_frame(
                    frame=self._frame_count,
                    dt=dt,
                    fps=fps,
                    game_state_name=self.__class__.__name__,
                    player=player_sprite,
                    boss=boss,
                    world_distance=self.world_distance
                )
                
        self._frame_count += 1
    
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
        
        # NPCs (drawn before player so they appear behind)
        for npc in self.npc_group:
            npc.draw(surface)

        # Interaction point prompts ("Talk" indicators)
        for point in self.interaction_group:
            point.draw(surface)

        # Ambient creatures (sorted by scale so further ones are drawn behind closer ones)
        for ambient in sorted(self.ambient_group, key=lambda a: getattr(a, 'depth_scale_factor', 1.0)):
            ambient.draw(surface)

        # Player (drawn after NPCs so player appears in front)
        self.player.sprite.draw(surface)
        
        # Enemies
        for enemy in self.obstacle_group:
            enemy.draw(surface)
        
        # Debug visualization
        if self.debug_mode:
            self._draw_debug_info(surface)

        # Boss Health Bar overlay
        self._draw_boss_health_bar(surface)

        # Objective overlay (drawn on top of everything)
        self.objective_display.draw(surface)

        # Notification banner (topmost layer)
        self.notification_banner.draw(surface)

        # Tutorial overlay (above everything)
        self.tutorial_overlay.draw(surface)

    def _draw_boss_health_bar(self, surface: pg.Surface) -> None:
        """Render a premium boss health bar overlay if a boss is active."""
        BossManager.draw_boss_health_bar(surface, self.obstacle_group, self.width)
    
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
            if isinstance(sprite, (Skeleton, FireWizard)):
                self._draw_skeleton_debug(surface, sprite)

        # Distance debug info (top-right)
        zone = self._get_spawn_zone()
        max_skel = zone["max_skeletons"] if zone else "N/A"
        delay = zone["delay"] if zone else "N/A"
        dist_font = pg.font.SysFont("monospace", 18)
        dist_lines = [
            f"Distance: {int(self.world_distance)} / {int(self._level_end_distance)}",
            f"Max reached: {int(self.max_distance_reached)}",
            f"Zone: max_skel={max_skel} delay={delay}ms",
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
        
        state_text = f"State: {player.state.name if player.state else 'None'}"
        frame_text = f"Frame: {player.current_frame_index}"
        
        # Color based on attack phase
        if player.is_attacking:
            from src.game.entities.player import PlayerState

            # Safe fallback — combat_system module may not exist
            phase = getattr(player, 'attack_phase', None)
            if phase is not None:
                color = (255, 50, 50)    # Red for active attacks
                phase_text = f"Phase: {getattr(phase, 'name', str(phase))}"
            else:
                color = (255, 150, 50)   # Orange fallback
                phase_text = "Phase: ATTACKING"
            
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
        skeleton: Skeleton | FireWizard,
    ) -> None:
        """
        Render skeleton-specific debug information.
        
        Displays current state, animation frame, and hit frame indicators.
        
        Args:
            surface: Target surface for debug rendering.
            skeleton: Skeleton instance to debug.
        """
        font = pg.font.Font(None, 24)
        
        state_text = f"State: {skeleton.state.name if skeleton.state else 'None'}"
        frame_text = f"Frame: {skeleton.current_frame_index}"
        
        state_surface = font.render(state_text, True, (255, 255, 255))
        frame_surface = font.render(frame_text, True, (255, 255, 255))
        
        surface.blit(state_surface, (skeleton.rect.x, skeleton.rect.top - 40))
        surface.blit(frame_surface, (skeleton.rect.x, skeleton.rect.top - 25))
        
        # Hit frame indicator (yellow border when in hit frame)
        if skeleton.is_in_hit_frame():
            pg.draw.rect(surface, (255, 255, 0), skeleton.rect, 3)
            
            # Draw attack range reach (red box)
            if hasattr(skeleton, "get_attack_hitbox"):
                atk_hitbox = skeleton.get_attack_hitbox()
                if atk_hitbox:
                    pg.draw.rect(surface, (255, 0, 0), atk_hitbox, 2)
            
            hit_text = font.render("HIT FRAME!", True, (255, 255, 0))
            surface.blit(
                hit_text,
                (skeleton.rect.centerx - 40, skeleton.rect.top - 55),
            )