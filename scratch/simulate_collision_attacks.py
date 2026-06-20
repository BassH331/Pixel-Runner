import sys
import os
sys.path.insert(0, os.getcwd())

import pygame as pg
pg.init()
pg.display.set_mode((1280, 720))

from unittest.mock import MagicMock
from src.game.entities.fire_wizard import FireWizard, FireWizardState
from src.game.entities.player import Player, PlayerState

def run_attack_simulation():
    print("=========================================================")
    print("        FIRE WIZARD COLLISION & ATTACK SIMULATION        ")
    print("=========================================================")

    # Initialize Player & Boss
    audio_mgr = MagicMock()
    player = Player(x=100, y=600, audio_manager=audio_mgr)
    wizard = FireWizard(x=250, y=600, player=player, tier="boss")

    # Set player to face boss and initiate attack
    player.rect.centerx = 100
    wizard.rect.centerx = 250
    print(f"Player Box: {player.rect}")
    print(f"Wizard Box: {wizard.rect}")
    print(f"Distance: {abs(wizard.rect.centerx - player.rect.centerx)}px")

    # Simulate Player Attack
    print("\n--- 1. Attack in IDLE state ---")
    wizard._health = 100.0
    wizard.set_state(FireWizardState.IDLE, force=True)
    print(f"Boss state BEFORE damage: {wizard.state} (HP: {wizard._health})")
    
    # Player hits
    wizard.take_damage(15.0)
    print(f"Boss state AFTER damage: {wizard.state} (HP: {wizard._health})")

    print("\n--- 2. Attack in CHASE state ---")
    wizard._health = 100.0
    wizard.set_state(FireWizardState.CHASE, force=True)
    print(f"Boss state BEFORE damage: {wizard.state} (HP: {wizard._health})")
    wizard.take_damage(15.0)
    print(f"Boss state AFTER damage: {wizard.state} (HP: {wizard._health})")

    print("\n--- 3. Attack in STAGNANT/EXHAUSTED state ---")
    wizard._health = 100.0
    wizard.set_state(FireWizardState.IDLE, force=True)
    wizard._is_stagnant = True
    wizard._stagnant_timer = 3.0
    wizard._is_recharging = False
    
    print(f"Boss state BEFORE damage: {wizard.state} (HP: {wizard._health})")
    print(f"Stagnant: {wizard._is_stagnant}, Recharging: {wizard._is_recharging}, Pos X: {wizard.rect.centerx}")
    
    # Hit boss
    wizard.take_damage(15.0)
    print(f"Boss state AFTER damage: {wizard.state} (HP: {wizard._health})")
    print(f"Stagnant: {wizard._is_stagnant}, Recharging: {wizard._is_recharging}, Pos X: {wizard.rect.centerx}")
    
    # Tick simulation to let the HURT animation play out (4 frames at 0.15s per frame = 0.6s total)
    print("\n--- Ticking through HURT animation ---")
    for step in range(1, 32):
        wizard.update(0.12)
        frames_cnt = len(wizard.animations[wizard.state]) if wizard.state in wizard.animations else 0
        if step in (1, 5, 10, 15, 20, 25, 26, 27, 28, 29, 30, 31):
            print(f"Tick {step} | State={wizard.state} | FrameIdx={wizard.animation_index:.2f}/{frames_cnt} | Stagnant={wizard._is_stagnant} | Recharging={wizard._is_recharging} | Pos X={wizard.rect.centerx}")

    print("\n--- 4. Attack in RECHARGING/AURA state ---")
    wizard._health = 100.0
    wizard._is_recharging = True
    wizard._is_stagnant = False
    wizard.set_state(FireWizardState.IDLE, force=True)
    
    print(f"Boss state BEFORE damage: {wizard.state} (HP: {wizard._health})")
    wizard.take_damage(15.0)
    print(f"Boss state AFTER damage: {wizard.state} (HP: {wizard._health})")

if __name__ == "__main__":
    run_attack_simulation()
    pg.quit()
