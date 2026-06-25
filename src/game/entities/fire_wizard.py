"""
Fire Wizard boss module with specialized AI and frame-precise spell casting.
"""

from __future__ import annotations

import os
import json
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Final, Optional

import pygame as pg

from v3x_zulfiqar_gideon import AssetManager, Actor, AttackConfig
from .hitbox_registry import HitboxRegistry

if TYPE_CHECKING:
    from src.game.entities.player import Player


class Fireball(pg.sprite.Sprite):
    """A fireball projectile shot by the Fire Wizard boss."""
    
    def __init__(
        self,
        x: int,
        y: int,
        direction: int,
        scale: float,
        damage: float,
        knockback: float,
        player: Player
    ) -> None:
        super().__init__()
        self._player = player
        self.direction = direction
        self.speed = 6.0
        self.damage = damage
        self.knockback = knockback
        
        # Procedural sprite creation with clean glowing visuals
        size = max(16, int(24 * scale))
        self.image = pg.Surface((size, size), pg.SRCALPHA)
        center = size // 2
        # Outer glow
        pg.draw.circle(self.image, (255, 69, 0, 150), (center, center), center)
        # Middle ring
        pg.draw.circle(self.image, (255, 140, 0, 200), (center, center), int(center * 0.7))
        # Inner core
        pg.draw.circle(self.image, (255, 255, 224, 255), (center, center), int(center * 0.4))
        
        self.rect = self.image.get_rect(center=(x, y))
        
        self.is_projectile = True
        self.is_boss = False

    def update(self, dt: Optional[float] = None, scroll_speed: int = 0) -> None:
        if dt is None:
            dt = 1.0 / 60.0
            
        # Move horizontally
        self.rect.x -= scroll_speed
        self.rect.x += int(self.direction * self.speed)
        
        # Destroy if way off screen
        if self.rect.right < -200 or self.rect.left > 2000:
            from src.game.debug.gameplay_tracker import GameplayTracker
            tracker = GameplayTracker.get_instance()
            if tracker and tracker.enabled:
                tracker.log_event("projectile_miss", {
                    "projectile_type": "fireball",
                    "frame": getattr(tracker, "frame_count", 0),
                    "world_distance": getattr(tracker, "last_world_distance", 0.0)
                })
            self.kill()
            return
            
        # Collision detection with player
        if self.rect.colliderect(self._player.rect):
            if not self._player.is_invincible:
                player_health_before = self._player.health
                damage_applied = self._player.take_damage(self.damage)
                if damage_applied:
                    from src.game.debug.gameplay_tracker import GameplayTracker
                    tracker = GameplayTracker.get_instance()
                    if tracker and tracker.enabled:
                        tracker.log_event("projectile_hit", {
                            "projectile_type": "fireball",
                            "frame": getattr(tracker, "frame_count", 0),
                            "world_distance": getattr(tracker, "last_world_distance", 0.0)
                        })
                        tracker.log_event("damage_received", {
                            "attacker": "Fireball",
                            "attacker_is_boss": False,
                            "damage": self.damage,
                            "player_health_before": player_health_before,
                            "player_health_after": self._player.health,
                            "world_distance": getattr(tracker, "last_world_distance", 0.0)
                        })
                    if self.knockback > 0:
                        apply_kb = getattr(self._player, 'apply_knockback', None)
                        if apply_kb:
                            kb_dir = -1 if self.rect.centerx > self._player.rect.centerx else 1
                            apply_kb(self.knockback * kb_dir)
            self.kill()

    def draw(self, surface: pg.Surface) -> None:
        """Render the fireball sprite to the screen."""
        surface.blit(self.image, self.rect)


class FireWizardState(Enum):
    """Enumeration of all possible fire wizard behavioral states."""
    
    DEATH = 0
    HURT = 10
    ATTACK = 20
    CHASE = 30
    IDLE = 40


@dataclass(slots=True)
class StateConfig:
    animation_speed: float = 0.15
    loops: bool = True
    next_state: Optional[FireWizardState] = None
    interruptible: bool = True


class FireWizard(Actor):
    """
    A Fire Wizard boss with unique spell casting animations, frame-precise hitboxes,
    and balanced AI that gives the player space to maneuver.
    """
    
    # Class-level attack configuration (immutable)
    # The active hit frames cover the entire blazing duration (frames 2 to 7)
    # and allow multiple hits to match the continuous fire blaze visual.
    ATTACK_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset({2, 3, 4, 5, 6, 7}),
        base_damage=2.5,
        knockback_force=7.0,
        max_hits_per_target=3,
    )
    
    STATE_CONFIGS: Final[dict[Enum, StateConfig]] = {
        FireWizardState.IDLE: StateConfig(0.12),
        FireWizardState.CHASE: StateConfig(0.15),
        FireWizardState.ATTACK: StateConfig(0.12, loops=False, next_state=FireWizardState.IDLE, interruptible=False),
        FireWizardState.HURT: StateConfig(0.15, loops=False, next_state=FireWizardState.IDLE, interruptible=False),
        FireWizardState.DEATH: StateConfig(0.15, loops=False, interruptible=False),
    }

    def __init__(
        self,
        x: int,
        y: int,
        player: Player,
        tier: str = "boss",
        sprite_root: Optional[str] = None,
        behaviour_map: Optional[dict[str, str]] = None,
        custom_scale: Optional[float] = None,
        custom_health: Optional[float] = None,
    ) -> None:
        super().__init__(x, y)
        
        self._player: Player = player
        self.state_configs = self.STATE_CONFIGS
        self.tier = tier
        
        # Chase and attack cooldowns to prevent constant "tailing" and give player space to run
        self._chase_cooldown: float = 0.0
        self._attack_cooldown: float = 0.0
        self._has_spawned_attack_effect: bool = False
        
        # Mana and charging system properties loaded from config if exists
        self._max_mana: float = 100.0
        self._spell_mana_cost: float = 35.0
        self._stagnant_duration: float = 3.0
        self._teleport_dist_min: int = 380
        self._teleport_dist_max: int = 450
        self._mana_recharge_rate: float = 50.0
        self._chase_delay_duration: float = 0.8
        self._attack_cooldown_min: float = 1.2
        self._attack_cooldown_max: float = 2.0
        self._spidey_sense: float = 0.0
        
        config_path = "game_data/boss_wizard_config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    self._max_mana = float(config.get("max_mana", 100.0))
                    self._spell_mana_cost = float(config.get("spell_mana_cost", 35.0))
                    self._stagnant_duration = float(config.get("stagnant_duration", 3.0))
                    self._teleport_dist_min = int(config.get("teleport_dist_min", 380))
                    self._teleport_dist_max = int(config.get("teleport_dist_max", 450))
                    self._mana_recharge_rate = float(config.get("mana_recharge_rate", 50.0))
                    self._chase_delay_duration = float(config.get("chase_delay_duration", 0.8))
                    self._attack_cooldown_min = float(config.get("attack_cooldown_min", 1.2))
                    self._attack_cooldown_max = float(config.get("attack_cooldown_max", 2.0))
                    self._spidey_sense = float(config.get("spidey_sense", 0.0))
            except Exception as e:
                print(f"[WARNING] Error loading wizard config: {e}")
                
        self._mana: float = self._max_mana
        self._is_recharging: bool = False
        self._is_stagnant: bool = False
        self._stagnant_timer: float = 0.0
        self._chase_delay_timer: float = 0.0
        self._chase_delay_active: bool = False
        self._teleport_flash_timer: float = 0.0
        self._teleport_after_hurt: bool = False
        
        # Load margins and scale
        key = f"boss:{os.path.basename(sprite_root.rstrip('/'))}" if sprite_root else "boss"
        margins = HitboxRegistry.get_margins(key)
        
        # Determine scale: registry priority -> custom_scale priority -> default margins scale
        registry_scale = None
        try:
            if HitboxRegistry.has_custom_margins(key):
                registry_scale = margins.scale
        except Exception:
            pass
            
        self.scale = registry_scale if registry_scale is not None else (custom_scale if custom_scale is not None else margins.scale)
        
        # 1. Load animations from assets/wizard
        self.animations[FireWizardState.IDLE] = self._load_frames(
            "assets/wizard/Idle/wizard_idle{}.png", 8
        )
        self.animations[FireWizardState.CHASE] = self._load_frames(
            "assets/wizard/Move/wizard_run{}.png", 8
        )
        self.animations[FireWizardState.ATTACK] = self._load_frames(
            "assets/wizard/Attack/wizard_atk1{}.png", 8
        )
        self.animations[FireWizardState.HURT] = self._load_frames(
            "assets/wizard/Take Hit/wizard_hit{}.png", 4
        )
        self.animations[FireWizardState.DEATH] = self._load_frames(
            "assets/wizard/Death/wizard_death{}.png", 5
        )
        
        # 2. Scale configurations based on boss/elite tier
        damage_scale = 1.0
        knockback_scale = 1.0
        
        if self.tier == "boss":
            self._max_health = custom_health if custom_health is not None else 150.0
            self._speed = 3.0
            damage_scale = 3.0
            knockback_scale = 1.5
        elif self.tier == "elite":
            self._max_health = custom_health if custom_health is not None else 60.0
            self._speed = 2.8
            damage_scale = 1.6
            knockback_scale = 1.2
        else:
            self._max_health = custom_health if custom_health is not None else 30.0
            self._speed = 2.4
            
        self._health: float = self._max_health
        
        self.current_attack_config = AttackConfig(
            hit_frames=self.ATTACK_CONFIG.hit_frames,
            base_damage=self.ATTACK_CONFIG.base_damage * damage_scale,
            knockback_force=self.ATTACK_CONFIG.knockback_force * knockback_scale,
        )
        
        # Initial state setup
        self.set_state(FireWizardState.IDLE)
        if self.state in self.animations:
            self.image = self.animations[self.state][0]
        self.rect: pg.Rect = self.image.get_rect(midbottom=(x, y))
        
        # Hitbox adjustment from margins registry
        self.adjust_hitbox_sides(left=margins.left, right=margins.right, top=margins.top, bottom=margins.bottom)
        
        # Movement and physics
        self._gravity: float = 0.0
        surf = pg.display.get_surface()
        height = surf.get_height() if surf else 720
        self._ground_y: int = height - margins.ground_offset
        
        # AI bounds
        self._detection_range: int = 3000 if self.tier == "boss" else 1000
        self._attack_range: int = 120  # Wizard cast range is longer
        self._vertical_tolerance: int = 500 if self.tier == "boss" else 100
        self.spawn_zone: Optional[dict] = None
        
    def _load_frames(
        self,
        path_pattern: str,
        count: int,
    ) -> list[pg.Surface]:
        """Load and scale animation frames."""
        frames: list[pg.Surface] = []
        for i in range(count):
            path = path_pattern.format(i)
            try:
                frame = AssetManager.get_texture(path)
                original_size = frame.get_size()
                scaled_size = (
                    int(original_size[0] * self.scale),
                    int(original_size[1] * self.scale),
                )
                scaled_frame = pg.transform.scale(frame, scaled_size)
                frames.append(scaled_frame)
            except (FileNotFoundError, pg.error) as e:
                print(f"Warning: Failed to load frame {i} from '{path}': {e}")
                
        if not frames:
            raise RuntimeError(f"Failed to load any frames from pattern: {path_pattern}")
        return frames
    
    @property
    def health(self) -> float: return self._health
    @property
    def max_health(self) -> float: return self._max_health
    @property
    def entity_id(self) -> int: return id(self)
    @property
    def is_dead(self) -> bool: return self.state == FireWizardState.DEATH
    @property
    def current_frame_index(self) -> int: return int(self.animation_index)

    def is_in_hit_frame(self) -> bool:
        return self.attack_state.is_hit_frame_active()

    def should_deal_damage(self) -> bool:
        return self.attack_state.is_hit_frame_active()

    def register_hit(self, target_id: int = 0) -> bool:
        return self.attack_state.try_register_hit(target_id)

    def try_register_hit(self, target_id: int) -> bool:
        return self.attack_state.try_register_hit(target_id)

    def get_current_attack_damage(self) -> float:
        return self.attack_state.get_current_damage()

    def get_current_attack_knockback(self) -> float:
        return self.attack_state.config.knockback_force if self.attack_state.config else 0.0

    def get_attack_hitbox(self) -> Optional[pg.Rect]:
        """Return a magic blast spell reach hitbox extending in front of the wizard."""
        if not self.should_deal_damage():
            return None
        # Mathematically aligned to the visual fire blast asset size (55x45 frame pixels)
        hitbox_w = int(55 * self.scale)
        hitbox_h = int(45 * self.scale)
        if self.facing_left:
            hitbox_x = self.rect.left - hitbox_w
        else:
            hitbox_x = self.rect.right
        hitbox_y = self.rect.centery - hitbox_h // 2
        return pg.Rect(hitbox_x, hitbox_y, hitbox_w, hitbox_h)

    def set_state(self, new_state: Enum, force: bool = False) -> None:
        old_state = self.state
        super().set_state(new_state, force=force)
        
        # When finishing/interrupting an attack, ensure the attack state resets
        # and give the player some space/breathing room to run.
        if old_state == FireWizardState.ATTACK and self.state != FireWizardState.ATTACK:
            self.attack_state.end()
            self._chase_cooldown = 1.8  # 1.8 seconds cooldown before chasing again

        if new_state == FireWizardState.ATTACK:
            self._has_spawned_attack_effect = False

        if new_state not in (FireWizardState.IDLE, FireWizardState.CHASE):
            self._chase_delay_timer = 0.0
            self._chase_delay_active = False

    def update(self, dt: Optional[float] = None, scroll_speed: int = 0) -> None:
        if dt is None:
            dt_sec = 1.0 / 60.0
        elif dt > 0.5:
            dt_sec = dt / 1000.0
        else:
            dt_sec = dt

        self.rect.x -= scroll_speed
        
        self._apply_gravity()
        
        # Decrement cooldowns and timers
        if self._chase_cooldown > 0.0:
            self._chase_cooldown = max(0.0, self._chase_cooldown - dt_sec)
        if self._attack_cooldown > 0.0:
            self._attack_cooldown = max(0.0, self._attack_cooldown - dt_sec)
        if self._chase_delay_timer > 0.0:
            self._chase_delay_timer = max(0.0, self._chase_delay_timer - dt_sec)
        if self._teleport_flash_timer > 0.0:
            self._teleport_flash_timer = max(0.0, self._teleport_flash_timer - dt_sec)
        if self._stagnant_timer > 0.0:
            self._stagnant_timer = max(0.0, self._stagnant_timer - dt_sec)
            if self._stagnant_timer <= 0.0:
                if self._is_stagnant:
                    self._trigger_teleport_recharge()
            
        # Mana recharge logic
        if self._is_recharging:
            self._mana = min(self._max_mana, self._mana + self._mana_recharge_rate * dt_sec)
            if self._mana >= self._max_mana:
                self._is_recharging = False
            
        # Spawn fireball projectile on frame 4 of attack animation
        if self.state == FireWizardState.ATTACK and not self._has_spawned_attack_effect:
            if int(self.animation_index) == 4:
                self._has_spawned_attack_effect = True
                self._spawn_fireball()
                self._mana = max(0.0, self._mana - self._spell_mana_cost)
            
        self._update_ai()
        
        super().update(dt_sec)
        
        if self._teleport_after_hurt and self.state == FireWizardState.IDLE:
            self._teleport_after_hurt = False
            self._trigger_teleport_recharge()
            
        # Apply teleport transparency/glow effect
        if self._teleport_flash_timer > 0.0:
            alpha = 100 if int(self._teleport_flash_timer * 30) % 2 == 0 else 200
            self.image.set_alpha(alpha)
        else:
            self.image.set_alpha(255)
        
        # Clean up once death animation is fully finished
        if self.state == FireWizardState.DEATH and int(self.animation_index) >= len(self.animations[FireWizardState.DEATH]) - 1:
            self.kill()

    def _spawn_fireball(self) -> None:
        direction = -1 if self.facing_left else 1
        spawn_x = self.rect.left if self.facing_left else self.rect.right
        spawn_y = self.rect.centery
        
        from src.game.debug.gameplay_tracker import GameplayTracker
        tracker = GameplayTracker.get_instance()
        if tracker and tracker.enabled:
            tracker.log_event("spell_cast", {
                "spell_type": "fireball",
                "frame": getattr(tracker, "frame_count", 0),
                "world_distance": getattr(tracker, "last_world_distance", 0.0)
            })
            
        damage = self.current_attack_config.base_damage if self.current_attack_config else 2.5
        knockback = self.current_attack_config.knockback_force if self.current_attack_config else 7.0
        
        fireball = Fireball(
            x=spawn_x,
            y=spawn_y,
            direction=direction,
            scale=self.scale,
            damage=damage,
            knockback=knockback,
            player=self._player
        )
        for group in self.groups():
            group.add(fireball)  # type: ignore

    def _trigger_teleport_recharge(self) -> None:
        """Instantly teleport away from the player to recharge mana."""
        if self._player is None:
            return
            
        player_rect = self._player.rect
        dist_offset = random.randint(self._teleport_dist_min, self._teleport_dist_max)
        
        # Teleport to the opposite side of the player
        if self.rect.centerx > player_rect.centerx:
            target_x = player_rect.centerx + dist_offset
        else:
            target_x = player_rect.centerx - dist_offset
            
        # Clamp to screen boundaries
        target_x = max(50, min(1200, target_x))
        
        self.rect.centerx = target_x
        self.rect.bottom = self._ground_y
        self._gravity = 0.0
        
        self._is_recharging = True
        self._is_stagnant = False
        self._stagnant_timer = 0.0
        self._teleport_flash_timer = 0.6
        self._chase_cooldown = 2.0
        self.set_state(FireWizardState.IDLE, force=True)

    def take_damage(self, amount: float = 0.5) -> None:
        if self.state in (FireWizardState.HURT, FireWizardState.DEATH):
            return
            
        # Check Spidey Sense dodge probability
        if self._spidey_sense > 0.0 and random.random() < self._spidey_sense:
            print(f"[SPIDEY SENSE] Dodged player attack! (Setting: {self._spidey_sense:.2f})")
            if self._spidey_sense >= 0.8:
                # GOD MODE: know all moves and how to counter!
                # Teleport behind the player and counter-attack immediately
                if self._player is not None:
                    player_rect = self._player.rect
                    if self._player.facing_left:
                        target_x = player_rect.centerx + 180
                        self.facing_left = True
                    else:
                        target_x = player_rect.centerx - 180
                        self.facing_left = False
                        
                    target_x = max(50, min(1200, target_x))
                    self.rect.centerx = target_x
                    self.rect.bottom = self._ground_y
                    self._gravity = 0.0
                    
                    # Recharge enough mana to cast counter spell
                    self._mana = max(self._mana, self._spell_mana_cost)
                    self._teleport_flash_timer = 0.6
                    self._chase_cooldown = 1.0
                    
                    # Trigger immediate counter attack
                    self._has_spawned_attack_effect = False
                    self.set_state(FireWizardState.ATTACK, force=True)
                    self._attack_cooldown = random.uniform(self._attack_cooldown_min, self._attack_cooldown_max)
                    print("[SPIDEY SENSE] COUNTER-ATTACK INITIATED!")
                    return
            else:
                # Standard spidey sense: teleport away to safety
                self._trigger_teleport_recharge()
                return
            
        self._health = max(0, self._health - amount)
        self.attack_state.end()
        
        # If stagnant, taking damage triggers hurt animation, then teleport retreat to recharge
        if self._is_stagnant and self._health > 0:
            self.set_state(FireWizardState.HURT, force=True)
            self._teleport_after_hurt = True
            return
            
        if self._health <= 0:
            self.set_state(FireWizardState.DEATH, force=True)
        else:
            self.set_state(FireWizardState.HURT, force=True)
            
    def _update_ai(self) -> None:
        if self._player is None or self.state in (FireWizardState.HURT, FireWizardState.DEATH):
            return
            
        if self.state == FireWizardState.ATTACK:
            return
            
        # If mana is low, trigger stagnant/exhausted phase
        if self._mana < self._spell_mana_cost and not self._is_recharging and not self._is_stagnant:
            self._is_stagnant = True
            self._stagnant_timer = self._stagnant_duration
            self.set_state(FireWizardState.IDLE, force=True)
            return
            
        # If stagnant, remain in IDLE
        if self._is_stagnant:
            self.set_state(FireWizardState.IDLE)
            return
            
        # If in chase cooldown or actively recharging, keep idling
        if self._chase_cooldown > 0.0 or self._is_recharging:
            self.set_state(FireWizardState.IDLE)
            return
            
        player_rect = self._player.rect
        dist_x = self.rect.centerx - player_rect.centerx
        abs_dist_x = abs(dist_x)
        dist_y = abs(self.rect.centery - player_rect.centery)
        
        # Check if in ranged attack zone and attack is off cooldown (needs at least spell_mana_cost mana)
        if dist_y < self._vertical_tolerance:
            if 120 <= abs_dist_x <= 260 and self._attack_cooldown <= 0.0 and self._mana >= self._spell_mana_cost:
                self._chase_delay_timer = 0.0
                self._chase_delay_active = False
                self._begin_attack()
                return
                
        # If player runs away, allow a brief window to run before pursuing (similar to skeletons)
        if abs_dist_x > 260:
            if self.state == FireWizardState.IDLE and not self._chase_delay_active:
                self._chase_delay_timer = self._chase_delay_duration  # Configured grace window
                self._chase_delay_active = True
                
        if self._chase_delay_active:
            if self._chase_delay_timer > 0.0:
                self.set_state(FireWizardState.IDLE)
                return
            else:
                self._chase_delay_active = False
            
        # Handle movement updates
        self.set_state(FireWizardState.CHASE)
        self._chase_player(player_rect)
            
    def _begin_attack(self) -> None:
        # Lock direction to face player at the start of attack
        self.facing_left = (self.rect.centerx > self._player.rect.centerx)
        self.set_state(FireWizardState.ATTACK)
        # Configured cooldown between spells
        self._attack_cooldown = random.uniform(self._attack_cooldown_min, self._attack_cooldown_max)
        
    def _chase_player(self, player_rect: pg.Rect) -> None:
        dist_x = self.rect.centerx - player_rect.centerx
        abs_dist_x = abs(dist_x)
        
        # Smart retreating: if player gets too close, back away to keep distance!
        if abs_dist_x < 120:
            retreat_speed = self._speed * 1.3
            if dist_x > 0:
                # Wizard is to the right of player, move right
                self.rect.x += int(retreat_speed)
                self.facing_left = True  # Keep facing the player
            else:
                # Wizard is to the left of player, move left
                self.rect.x -= int(retreat_speed)
                self.facing_left = False  # Keep facing the player
        # If player is too far, advance to get into casting range
        elif abs_dist_x > 260:
            if dist_x > 0:
                self.rect.x -= int(self._speed)
                self.facing_left = True
            else:
                self.rect.x += int(self._speed)
                self.facing_left = False
        # If in the sweet spot but attack is on cooldown, stand ground & face player
        else:
            self.facing_left = (dist_x > 0)
            self.set_state(FireWizardState.IDLE)
            
    def _apply_gravity(self) -> None:
        self._gravity += 1.0
        self.rect.y += int(self._gravity)
        if self.rect.bottom >= self._ground_y:
            self.rect.bottom = self._ground_y
            self._gravity = 0.0
            
    def _apply_frame(self) -> None:
        pass

    def draw(self, surface: pg.Surface) -> None:
        super().draw(surface)
        if (self._health < self._max_health or self._mana < self._max_mana) and self.state != FireWizardState.DEATH:
            self._draw_health_bar(surface)
            
    def _draw_health_bar(self, surface: pg.Surface) -> None:
        bar_width: int = 40
        bar_height: int = 5
        bar_x: int = self.rect.centerx - bar_width // 2
        bar_y: int = self.rect.top - 15
        
        # Red health bar
        pg.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        health_ratio = self._health / self._max_health
        pg.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, int(bar_width * health_ratio), bar_height))
        
        # Blue mana bar
        mana_y = bar_y + bar_height + 2
        pg.draw.rect(surface, (50, 50, 50), (bar_x, mana_y, bar_width, 3))
        mana_ratio = max(0.0, self._mana / self._max_mana)
        pg.draw.rect(surface, (0, 191, 255), (bar_x, mana_y, int(bar_width * mana_ratio), 3))
        
        # Draw charging cyan aura if actively recharging
        if self._is_recharging:
            glow_radius = int(24 * self.scale + 6 * random.random())
            pg.draw.circle(surface, (0, 191, 255), self.rect.center, glow_radius, 2)
