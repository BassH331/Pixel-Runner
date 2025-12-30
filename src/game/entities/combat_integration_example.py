"""
Combat System Integration Example

This module demonstrates how to integrate the frame-based combat system
into your game loop. It shows the proper pattern for processing player
attacks against enemy entities.

Key Integration Points:
─────────────────────────────────────────────────────────────────────────────

1. COLLISION DETECTION
   The game loop (or collision manager) is responsible for checking
   collisions between the player's attack hitbox and enemy hitboxes.

2. HIT REGISTRATION
   Use player.try_register_hit(enemy_id) to prevent duplicate hits.
   This returns True only if the hit should be processed.

3. DAMAGE APPLICATION
   Apply damage through the target's take_damage() method after
   a hit is registered.

4. DEBUG VISUALIZATION
   Use player.draw_debug_hitboxes() during development to visualize
   active hitboxes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame as pg

if TYPE_CHECKING:
    from player import Player
    from enemy import Enemy  # Your enemy base class


class CombatManager:
    """
    Manages combat interactions between entities.
    
    This is a centralized system that processes all combat interactions
    each frame. It handles:
    - Player attacks against enemies
    - Enemy attacks against player
    - Hit effects and knockback application
    
    Usage:
        combat_manager = CombatManager()
        
        # In game loop:
        combat_manager.process_player_attacks(player, enemies)
        combat_manager.process_enemy_attacks(player, enemies)
    """
    
    def __init__(self) -> None:
        """Initialize the combat manager."""
        self._debug_mode: bool = False
    
    def enable_debug(self, enabled: bool = True) -> None:
        """Enable or disable debug visualization."""
        self._debug_mode = enabled
    
    def process_player_attacks(
        self,
        player: Player,
        enemies: list[Enemy],
    ) -> list[int]:
        """
        Process player attacks against all enemies.
        
        This method checks if the player can deal damage this frame,
        then processes collisions against all enemies and applies
        damage to those that are hit.
        
        Args:
            player: The player entity.
            enemies: List of enemy entities to check against.
            
        Returns:
            List of enemy IDs that were hit this frame.
            
        Example:
            >>> hit_ids = combat_manager.process_player_attacks(player, enemies)
            >>> for enemy_id in hit_ids:
            ...     spawn_hit_particles(enemy_id)
        """
        hit_enemy_ids: list[int] = []
        
        # Early exit if player can't deal damage
        if not player.should_deal_damage():
            return hit_enemy_ids
        
        # Get the active attack hitbox
        attack_hitbox = player.get_attack_hitbox()
        if attack_hitbox is None:
            return hit_enemy_ids
        
        # Check each enemy
        for enemy in enemies:
            # Skip dead enemies
            if enemy.is_dead:
                continue
            
            # Skip if enemy is invincible
            if enemy.is_invincible:
                continue
            
            # Check collision with enemy's hitbox
            if not attack_hitbox.colliderect(enemy.hitbox):
                continue
            
            # Try to register the hit (prevents duplicates)
            if not player.try_register_hit(enemy.entity_id):
                continue
            
            # Hit confirmed! Apply damage and knockback
            damage = player.get_current_attack_damage()
            knockback = player.get_attack_knockback(enemy.rect.center)
            
            # Apply to enemy (your enemy class should handle this)
            enemy.take_damage(damage, knockback)
            
            hit_enemy_ids.append(enemy.entity_id)
        
        return hit_enemy_ids
    
    def process_player_attacks_batch(
        self,
        player: Player,
        enemies: list[Enemy],
    ) -> None:
        """
        Alternative: Use the built-in batch processor.
        
        This uses player.process_attack_collisions() which handles
        the entire collision pipeline internally.
        
        Args:
            player: The player entity.
            enemies: List of enemy entities.
        """
        # Build target list
        targets = [
            (enemy.entity_id, enemy.hitbox)
            for enemy in enemies
            if not enemy.is_dead and not enemy.is_invincible
        ]
        
        # Process all collisions at once
        hits = player.process_attack_collisions(targets)
        
        # Apply results
        for hit in hits:
            enemy = self._find_enemy_by_id(enemies, hit.target_id)
            if enemy:
                enemy.take_damage(hit.damage, hit.knockback)
    
    def process_enemy_attacks(
        self,
        player: Player,
        enemies: list[Enemy],
    ) -> bool:
        """
        Process enemy attacks against the player.
        
        Mirrors the player attack logic but for enemy->player damage.
        
        Args:
            player: The player entity.
            enemies: List of enemy entities.
            
        Returns:
            True if player was hit this frame.
        """
        # Player can't be hit if invincible or dead
        if player.is_invincible or player.is_dead:
            return False
        
        for enemy in enemies:
            if enemy.is_dead:
                continue
            
            # Check if enemy can deal damage
            if not enemy.should_deal_damage():
                continue
            
            # Get enemy's attack hitbox
            attack_hitbox = enemy.get_attack_hitbox()
            if attack_hitbox is None:
                continue
            
            # Check collision with player
            if not attack_hitbox.colliderect(player.hitbox):
                continue
            
            # Try to register hit (enemy needs same system)
            if not enemy.try_register_hit(player.entity_id):
                continue
            
            # Apply damage to player
            damage = enemy.get_current_attack_damage()
            if player.take_damage(damage):
                return True
        
        return False
    
    def _find_enemy_by_id(
        self,
        enemies: list[Enemy],
        entity_id: int,
    ) -> Enemy | None:
        """Find enemy by entity ID."""
        for enemy in enemies:
            if enemy.entity_id == entity_id:
                return enemy
        return None
    
    def draw_debug(
        self,
        surface: pg.Surface,
        player: Player,
        enemies: list[Enemy],
    ) -> None:
        """
        Draw debug visualization for all combat hitboxes.
        
        Args:
            surface: Surface to draw on.
            player: The player entity.
            enemies: List of enemy entities.
        """
        if not self._debug_mode:
            return
        
        # Draw player attack hitbox (red)
        player.draw_debug_hitboxes(surface)
        
        # Draw enemy attack hitboxes (orange)
        for enemy in enemies:
            if hasattr(enemy, 'draw_debug_hitboxes'):
                enemy.draw_debug_hitboxes(surface)


# ─────────────────────────────────────────────────────────────────────────────
# Example Game Loop Integration
# ─────────────────────────────────────────────────────────────────────────────


def example_game_loop():
    """
    Example showing combat system integration in a game loop.
    
    This is pseudocode demonstrating the integration pattern.
    """
    # Initialize pygame and create window
    pg.init()
    screen = pg.display.set_mode((1280, 720))
    clock = pg.time.Clock()
    
    # Create game entities (pseudocode)
    # player = Player(x=100, y=500, audio_manager=audio)
    # enemies = [Skeleton(x=600, y=500), Skeleton(x=800, y=500)]
    
    # Create combat manager
    combat_manager = CombatManager()
    combat_manager.enable_debug(True)  # Enable during development
    
    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # Delta time in seconds
        
        # Handle events
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
        
        # ─────────────────────────────────────────────────────────────────────
        # UPDATE PHASE
        # ─────────────────────────────────────────────────────────────────────
        
        # Update player (handles input, physics, animation)
        # player.update(dt)
        
        # Update enemies
        # for enemy in enemies:
        #     enemy.update(dt)
        
        # ─────────────────────────────────────────────────────────────────────
        # COMBAT PHASE - Process all attacks
        # ─────────────────────────────────────────────────────────────────────
        
        # Process player attacks against enemies
        # hit_enemy_ids = combat_manager.process_player_attacks(player, enemies)
        
        # Optional: Spawn hit effects for each hit
        # for enemy_id in hit_enemy_ids:
        #     spawn_hit_effect(get_enemy_position(enemy_id))
        
        # Process enemy attacks against player
        # player_hit = combat_manager.process_enemy_attacks(player, enemies)
        
        # Optional: Screen shake on player hit
        # if player_hit:
        #     camera.shake(intensity=5, duration=0.2)
        
        # ─────────────────────────────────────────────────────────────────────
        # RENDER PHASE
        # ─────────────────────────────────────────────────────────────────────
        
        screen.fill((30, 30, 40))
        
        # Draw entities
        # player.draw(screen)
        # for enemy in enemies:
        #     enemy.draw(screen)
        
        # Draw debug hitboxes (development only)
        # combat_manager.draw_debug(screen, player, enemies)
        
        pg.display.flip()
    
    pg.quit()


# ─────────────────────────────────────────────────────────────────────────────
# Alternative: Simple Integration Pattern
# ─────────────────────────────────────────────────────────────────────────────


def simple_combat_check(player, enemies):
    """
    Minimal integration pattern without a CombatManager.
    
    Use this if you prefer inline combat processing.
    """
    # Check if player is attacking and on a hit frame
    if player.should_deal_damage():
        hitbox = player.get_attack_hitbox()
        
        if hitbox:
            for enemy in enemies:
                # Check collision
                if hitbox.colliderect(enemy.hitbox):
                    # Register hit (prevents duplicate damage)
                    if player.try_register_hit(enemy.entity_id):
                        # Get damage for current frame
                        damage = player.get_current_attack_damage()
                        
                        # Get knockback vector
                        knockback = player.get_attack_knockback(
                            enemy.rect.center
                        )
                        
                        # Apply to enemy
                        enemy.take_damage(damage, knockback)


# ─────────────────────────────────────────────────────────────────────────────
# Debug Visualization Helper
# ─────────────────────────────────────────────────────────────────────────────


class CombatDebugRenderer:
    """
    Advanced debug visualization for combat system.
    
    Provides detailed visual feedback during development:
    - Attack hitboxes with phase coloring
    - Hit frame indicators
    - Damage numbers
    - Knockback vectors
    """
    
    # Colors for different attack phases
    COLORS = {
        "startup": (100, 100, 255),    # Blue
        "active": (255, 50, 50),        # Red
        "recovery": (255, 200, 50),     # Yellow
        "hitbox": (255, 0, 0, 128),     # Semi-transparent red
        "hurt_box": (0, 255, 0, 128),   # Semi-transparent green
    }
    
    @classmethod
    def draw_player_combat_state(
        cls,
        surface: pg.Surface,
        player,
        font: pg.font.Font,
    ) -> None:
        """
        Draw comprehensive combat debug info for player.
        
        Args:
            surface: Surface to draw on.
            player: Player entity.
            font: Font for text rendering.
        """
        # Draw attack hitbox if active
        if player.should_deal_damage():
            hitbox = player.get_attack_hitbox()
            if hitbox:
                # Create semi-transparent surface for hitbox
                hitbox_surface = pg.Surface(
                    (hitbox.width, hitbox.height),
                    pg.SRCALPHA
                )
                hitbox_surface.fill((255, 0, 0, 100))
                surface.blit(hitbox_surface, hitbox.topleft)
                
                # Draw hitbox outline
                pg.draw.rect(surface, (255, 0, 0), hitbox, 2)
        
        # Draw attack phase indicator
        if player.is_attacking:
            phase = player.attack_phase
            phase_text = f"Phase: {phase.name}"
            
            # Color based on phase
            from combat_system import AttackPhase
            color = {
                AttackPhase.STARTUP: cls.COLORS["startup"],
                AttackPhase.ACTIVE: cls.COLORS["active"],
                AttackPhase.RECOVERY: cls.COLORS["recovery"],
                AttackPhase.COMPLETE: (128, 128, 128),
            }.get(phase, (255, 255, 255))
            
            text_surface = font.render(phase_text, True, color)
            surface.blit(
                text_surface,
                (player.rect.centerx - text_surface.get_width() // 2,
                 player.rect.top - 30)
            )
            
            # Draw frame indicator
            frame_text = f"Frame: {player.current_frame_index}"
            frame_surface = font.render(frame_text, True, (255, 255, 255))
            surface.blit(
                frame_surface,
                (player.rect.centerx - frame_surface.get_width() // 2,
                 player.rect.top - 50)
            )
    
    @classmethod
    def draw_damage_number(
        cls,
        surface: pg.Surface,
        position: tuple[int, int],
        damage: float,
        font: pg.font.Font,
        is_critical: bool = False,
    ) -> None:
        """
        Draw floating damage number.
        
        Args:
            surface: Surface to draw on.
            position: Position to draw at.
            damage: Damage value to display.
            font: Font for text rendering.
            is_critical: Whether this was a critical hit.
        """
        color = (255, 255, 0) if is_critical else (255, 255, 255)
        text = f"{int(damage)}!" if is_critical else str(int(damage))
        
        text_surface = font.render(text, True, color)
        
        # Center on position
        rect = text_surface.get_rect(center=position)
        surface.blit(text_surface, rect)


if __name__ == "__main__":
    print("Combat System Integration Example")
    print("=" * 50)
    print()
    print("This module provides:")
    print("  - CombatManager: Centralized combat processing")
    print("  - CombatDebugRenderer: Visual debugging tools")
    print("  - Integration patterns for your game loop")
    print()
    print("Key methods on Player:")
    print("  - should_deal_damage() → Check if damage can be dealt")
    print("  - get_attack_hitbox() → Get collision rect")
    print("  - try_register_hit(id) → Register hit on target")
    print("  - get_current_attack_damage() → Get frame damage")
    print("  - get_attack_knockback(pos) → Get knockback vector")
