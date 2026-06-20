import sys
import os
sys.path.insert(0, os.getcwd())

import pygame as pg
pg.init()
# Create a headless screen
pg.display.set_mode((1280, 720))

from unittest.mock import MagicMock
from src.game.entities.fire_wizard import FireWizard
from src.game.entities.player import Player
from src.game.entities.hitbox_registry import HitboxRegistry

def test_sync():
    print("=== TESTING SCALING AND COORDINATE SYNCHRONIZATION ===")
    
    # Check what is in the database for boss:wizard
    key = "boss:wizard"
    try:
        margins = HitboxRegistry.get_margins(key)
        print(f"Database configuration for '{key}':")
        print(f"  Scale: {margins.scale}")
        print(f"  Left: {margins.left}, Right: {margins.right}")
        print(f"  Top: {margins.top}, Bottom: {margins.bottom}")
        print(f"  Ground Offset: {margins.ground_offset}")
    except Exception as e:
        print(f"Failed to get margins for {key}: {e}")
        return

    # Mock player
    player = MagicMock(spec=Player)
    player.rect = pg.Rect(200, 600, 50, 50)
    
    # Let's instantiate FireWizard exactly like in the game
    # Spawn pos in game: spawn_x = 1280 + 200 = 1480, spawn_y = 720 - 70 = 650
    spawn_x = 1480
    spawn_y = 650
    
    wizard = FireWizard(
        x=spawn_x,
        y=spawn_y,
        player=player,
        tier="boss",
        sprite_root="assets/wizard/"
    )
    
    print("\nWizard Instantiation:")
    print(f"  Scale: {wizard.scale}")
    print(f"  Image size: {wizard.image.get_size()}")
    print(f"  Rect initially: {wizard.rect}")
    print(f"  Image offset: {wizard.image_offset}")
    
    # Ground Y in game state spawn handler
    surf = pg.display.get_surface()
    height = surf.get_height() if surf else 720
    wizard._ground_y = height - margins.ground_offset
    print(f"  Ground Y target: {wizard._ground_y}")
    
    # Simulate gravity update
    # In game: self._apply_gravity() -> rect.bottom = _ground_y
    wizard.rect.bottom = wizard._ground_y
    print("\nAfter Gravity/Ground Alignment:")
    print(f"  Rect (Hitbox): {wizard.rect}")
    print(f"  Hitbox Bottom: {wizard.rect.bottom}")
    
    # Let's calculate where the sprite's image is actually blitted on screen:
    # draw_pos = self.rect.topleft - self.image_offset
    draw_pos = wizard.rect.topleft - wizard.image_offset
    print("\nSprite Rendering Calculation:")
    print(f"  Blit draw_pos: {draw_pos}")
    
    # The bottom of the drawn texture:
    texture_height = wizard.image.get_height()
    texture_bottom = draw_pos[1] + texture_height
    print(f"  Drawn Texture Bottom Y: {texture_bottom}")
    
    # The floor Y in the game is the display height minus the player's ground level
    # Player's ground level in database is 34. So player's ground Y is 720 - 34 = 686.
    player_ground_y = 686
    print(f"  Player/World Floor Y: {player_ground_y}")
    
    # Let's see how much the wizard's feet are above/below the floor.
    # The wizard's feet are located at the bottom of the wizard's body in the texture.
    # Visually, the wizard's body bottom is 'bottom' pixels above the texture bottom.
    # So the feet's Y coordinate is: texture_bottom - margins.bottom
    feet_y = texture_bottom - margins.bottom
    print(f"  Wizard Feet visual Y: {feet_y}")
    print(f"  Feet alignment offset from Player Floor Y: {feet_y - player_ground_y} pixels")

    print("\nFrame sizes across all states:")
    for state in wizard.animations:
        frames = wizard.animations[state]
        sizes = [f.get_size() for f in frames]
        print(f"  State {state.name}:")
        print(f"    Count: {len(frames)}")
        print(f"    Unique sizes: {set(sizes)}")

if __name__ == "__main__":
    test_sync()
