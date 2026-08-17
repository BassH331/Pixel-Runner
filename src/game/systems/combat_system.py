"""
CombatSystem — Decoupled combat processing system.

Handles player-to-enemy hit detection, enemy-to-player damage, environmental hazards,
knockback application, and combat event emission.
"""

from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING, Any

import pygame as pg

from src.game.entities.enemy import Enemy
from src.game.entities.skeleton import Skeleton
from src.game.entities.fire_wizard import FireWizard
from src.game.entities.green_monster import GreenMonster
from src.game.effects.vfx_manager import VisualEffectManager
from v3x_zulfiqar_gideon import DamageDealt, DamageReceived, EntityDied

if TYPE_CHECKING:
    from src.game.entities.player import Player
    from src.game.states.game_state import GameState


class CombatSystem:
    """Decoupled combat resolution system for GameState."""

    def __init__(self, game_state: GameState) -> None:
        self.game = game_state

    def process_combat(self) -> None:
        """Process all combat interactions for the current frame tick."""
        player_sprite = self.game.player.sprite
        if not player_sprite or player_sprite.is_dead:
            return

        # 1. Player attacks against enemies
        self.process_player_attacks(player_sprite)

        # 2. Enemy attacks against player
        self.process_enemy_attacks(player_sprite)

    def process_player_attacks(self, player: Player) -> None:
        """Process player attacks against all active obstacles."""
        if not player.should_deal_damage():
            return

        attack_hitbox = player.get_attack_hitbox()
        if attack_hitbox is None:
            return

        colliderect = attack_hitbox.colliderect
        try_register_hit = player.try_register_hit

        for obstacle in self.game.obstacle_group:
            if getattr(obstacle, "is_dead", False) or getattr(obstacle, "is_invincible", False):
                continue

            target_hitbox = getattr(obstacle, "low_hitbox", None) or getattr(obstacle, "hitbox", obstacle.rect)
            if target_hitbox is None or not colliderect(target_hitbox):
                continue

            target_id = getattr(obstacle, "entity_id", None) or id(obstacle)
            if not try_register_hit(target_id):
                continue

            self._apply_player_damage_to_enemy(player, obstacle)

    def _apply_player_damage_to_enemy(self, player: Player, enemy: Any) -> None:
        damage = player.get_current_attack_damage()
        knockback = player.get_attack_knockback(enemy.rect.center)

        target_health_before = getattr(enemy, "_health", getattr(enemy, "health", 0.0))
        if isinstance(enemy, (Skeleton, FireWizard, Enemy)) or hasattr(enemy, 'take_damage'):
            try:
                enemy.take_damage(damage, knockback)
            except TypeError:
                enemy.take_damage(damage)
        else:
            enemy.kill()

        target_health_after = getattr(enemy, "_health", getattr(enemy, "health", 0.0))

        VisualEffectManager.spawn_hit_vfx(enemy.rect.centerx, enemy.rect.centery, entity=enemy)

        # Impact camera trigger
        is_boss = getattr(enemy, "is_boss", False)
        tier = getattr(enemy, "tier", "minion")
        target_tier = "boss" if (is_boss or tier == "boss") else ("elite" if tier == "elite" else "minion")

        midpoint_x = (player.rect.centerx + enemy.rect.centerx) // 2
        midpoint_y = (player.rect.centery + enemy.rect.centery) // 2
        self.game.trippy_zoom.trigger(
            focal_x=midpoint_x,
            focal_y=midpoint_y,
            intensity=damage / 25.0,
            target_tier=target_tier,
        )

        if self.game.tracker.enabled:
            self.game.tracker.log_event("damage_dealt", {
                "attacker": "player",
                "target": enemy.__class__.__name__,
                "target_is_boss": getattr(enemy, "is_boss", False),
                "damage": damage,
                "target_health_before": target_health_before,
                "target_health_after": target_health_after,
                "world_distance": self.game.world_distance
            })

        # Emit DamageDealt event via EventBus
        kb_mag = math.hypot(knockback[0], knockback[1]) if isinstance(knockback, tuple) else float(knockback)
        self.game.event_bus.emit(DamageDealt(
            attacker=player,
            target=enemy,
            amount=damage,
            knockback=kb_mag,
            target_health_before=target_health_before,
            target_health_after=target_health_after,
            is_boss=is_boss,
            target_tier=target_tier
        ))

        # Audio feedback & collision logging
        from src.game.audio import CombatCollisionLogger
        enemy_type = "boss" if isinstance(enemy, FireWizard) else str(getattr(enemy, "name", "enemy")).lower()
        enemy_id = getattr(enemy, "id", f"enemy_{id(enemy)}")
        is_dead = getattr(enemy, "is_dead", False)

        if is_dead and not getattr(enemy, "_death_sound_played", False):
            setattr(enemy, "_death_sound_played", True)
        elif not is_dead:
            CombatCollisionLogger.get_instance().log_collision(
                attacker="player",
                defender=enemy_type,
                defender_id=enemy_id,
                action="hit",
                defender_state="alive"
            )

        if is_dead and not getattr(enemy, "_death_event_emitted", False):
            setattr(enemy, "_death_event_emitted", True)
            soul_values = self.game._soul_harvest_config.get("soul_values", {})
            soul_reward = 0

            if getattr(enemy, "is_boss", False):
                boss_soul_value = getattr(enemy, "soul_value", 0)
                if boss_soul_value == "remaining":
                    remaining = self.game.player_ui.soul_harvest_target - self.game.player_ui.current_soul_total
                    soul_reward = max(0, remaining)
                elif isinstance(boss_soul_value, (int, float)) and boss_soul_value > 0:
                    soul_reward = int(boss_soul_value)
                else:
                    tier_val = getattr(enemy, "tier", "boss")
                    if tier_val == "boss":
                        soul_reward = soul_values.get("final_boss_remaining", 0)
                        if soul_reward is True:
                            remaining = self.game.player_ui.soul_harvest_target - self.game.player_ui.current_soul_total
                            soul_reward = max(0, remaining)
                    else:
                        soul_reward = soul_values.get("elite_boss", 150)
            else:
                tier_val = getattr(enemy, "tier", "minion")
                soul_reward = soul_values.get(f"skeleton_{tier_val}", soul_values.get("skeleton_minion", 5))

            self.game.event_bus.emit(EntityDied(
                entity=enemy,
                killer=player,
                position=(float(enemy.rect.centerx), float(enemy.rect.centery)),
                soul_value=soul_reward,
                is_boss=getattr(enemy, "is_boss", False),
                tier=getattr(enemy, "tier", "boss" if getattr(enemy, "is_boss", False) else "minion"),
                spawn_zone=getattr(enemy, "spawn_zone", None)
            ))

        self.game.score += self.game._SCORE_PER_HIT

    def process_enemy_attacks(self, player: Player) -> None:
        """Process enemy attacks against player."""
        if player.is_invincible:
            return

        for obstacle in self.game.obstacle_group:
            if isinstance(obstacle, (Skeleton, FireWizard, GreenMonster)):
                self._handle_skeleton_attack(player, obstacle)

    def _handle_skeleton_attack(self, player: Player, skeleton: Any) -> None:
        if self.game.is_interacting:
            return

        state = getattr(skeleton, "state", None)
        if state is None or "ATTACK" not in getattr(state, "name", ""):
            return

        if not skeleton.should_deal_damage():
            return

        skeleton_hitbox = getattr(skeleton, 'get_attack_hitbox', None)
        skeleton_hitbox = skeleton_hitbox() if skeleton_hitbox is not None else skeleton.rect

        if skeleton_hitbox is None or not skeleton_hitbox.colliderect(player.rect):
            return

        skeleton.register_hit(id(player))

        damage = skeleton.get_current_attack_damage()
        player_health_before = player.health
        damage_applied = player.take_damage(damage)
        player_health_after = player.health

        if damage_applied or player_health_after < player_health_before or damage > 0:
            VisualEffectManager.spawn_hit_vfx(
                player.rect.centerx,
                player.rect.centery,
                entity=player,
                target_entity=player,
            )

        if damage_applied and self.game.tracker.enabled:
            self.game.tracker.log_event("damage_received", {
                "attacker": skeleton.__class__.__name__,
                "attacker_is_boss": getattr(skeleton, "is_boss", False),
                "damage": damage,
                "player_health_before": player_health_before,
                "player_health_after": player.health,
                "world_distance": self.game.world_distance
            })
            self.game._logged_damage_this_tick = True

        if not damage_applied:
            return

        self.game.event_bus.emit(DamageReceived(
            target=player,
            attacker=skeleton,
            amount=damage,
            health_remaining=player.health,
            attacker_type=skeleton.__class__.__name__
        ))

        from src.game.audio import CombatCollisionLogger
        enemy_type = "boss" if isinstance(skeleton, FireWizard) else str(getattr(skeleton, "name", "skeleton")).lower()
        CombatCollisionLogger.get_instance(self.game.audio_manager).log_collision(
            attacker=enemy_type,
            defender="player",
            defender_id=getattr(skeleton, "id", f"skeleton_{id(skeleton)}"),
            action="hit",
            defender_state="alive"
        )

        knockback = skeleton.get_current_attack_knockback()
        if knockback > 0:
            knockback_direction = -1 if skeleton.rect.centerx > player.rect.centerx else 1
            self._apply_knockback_to_player(player, knockback * knockback_direction)

        trigger_flash = getattr(player, 'trigger_hit_flash', None)
        if trigger_flash:
            trigger_flash()

    def check_environmental_hazards(self) -> None:
        """Detect collision between Player and environmental hazard props (e.g. spikes, traps)."""
        player_sprite = self.game.player.sprite
        if not player_sprite or player_sprite.is_invincible or getattr(player_sprite, "health", 1) <= 0:
            return

        for prop in self.game.environment_manager.props:
            if getattr(prop, "collision_type", "solid") == "hazard":
                draw_x = int(prop.pos_x - self.game.world_distance * prop.parallax_ratio)
                draw_y = int(prop.pos_y)
                prop_rect = pg.Rect(draw_x, draw_y, prop.width, prop.height)

                if player_sprite.rect.colliderect(prop_rect):
                    damage = 15.0
                    damage_applied = player_sprite.take_damage(damage)
                    if damage_applied:
                        VisualEffectManager.spawn_hit_vfx(
                            player_sprite.rect.centerx,
                            player_sprite.rect.centery,
                            entity=player_sprite,
                            target_entity=player_sprite,
                        )
                        if self.game.tracker.enabled:
                            self.game.tracker.log_event("damage_received", {
                                "attacker": f"HazardSpike_{os.path.basename(prop.texture_path)}",
                                "attacker_is_boss": False,
                                "damage": damage,
                                "health_remaining": player_sprite.health,
                                "world_distance": float(self.game.world_distance),
                            })
                        print(f"[HAZARD SPIKE] Player hit environmental hazard '{os.path.basename(prop.texture_path)}'! Dealt {damage} damage.")
                        break

        if hasattr(self.game, 'score'):
            self.game.score = max(0, self.game.score - 5)

    def _apply_knockback_to_player(self, player: Player, force: float) -> None:
        """Apply horizontal knockback force to the player."""
        apply_kb = getattr(player, 'apply_knockback', None)
        if apply_kb:
            apply_kb(force)
        else:
            player.rect.x += int(force)
            player.rect.left = max(player.rect.left, 0)
            screen_width = pg.display.get_surface().get_width()
            player.rect.right = min(player.rect.right, screen_width)
