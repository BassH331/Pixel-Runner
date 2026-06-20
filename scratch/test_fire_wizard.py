import sys
import os
sys.path.insert(0, os.getcwd())

import pygame as pg
pg.init()
pg.display.set_mode((1280, 720))

from unittest.mock import MagicMock
from src.game.entities.fire_wizard import FireWizard, FireWizardState
from src.game.entities.player import Player

def test_fire_wizard_behavior():
    print("Testing FireWizard implementation...")
    
    # Mock player
    player = MagicMock(spec=Player)
    player.rect = pg.Rect(200, 600, 50, 50)
    
    # Instantiate FireWizard
    wizard = FireWizard(x=500, y=600, player=player, tier="boss")
    
    # 1. Verify initialization
    print(f"Wizard health: {wizard.health}/{wizard.max_health}")
    assert wizard.health == 150.0, "Expected boss HP 150.0"
    assert wizard.state == FireWizardState.IDLE, "Expected starting state IDLE"
    assert wizard.current_attack_config is not None
    assert wizard.current_attack_config.base_damage == 7.5, f"Expected scaled damage 7.5, got {wizard.current_attack_config.base_damage}"
    
    # 2. Test AI decision and transition to Chase/Attack
    # Player is far:
    player.rect.centerx = 1000
    wizard._update_ai()
    assert wizard.state == FireWizardState.CHASE, f"Expected state CHASE, got {wizard.state}"
    
    # Player in attack range:
    player.rect.centerx = 550
    wizard._update_ai()
    assert wizard.state == FireWizardState.ATTACK, f"Expected state ATTACK, got {wizard.state}"
    
    # 3. Test Attack state end transitions and cooldown trigger
    # Simulating attack execution
    assert wizard.current_attack_config is not None
    wizard.attack_state.begin(wizard.current_attack_config)
    assert wizard.attack_state.is_active == True, "AttackState should be active"
    
    # Setting state to IDLE should reset attack state and start cooldown
    wizard.set_state(FireWizardState.IDLE, force=True)
    assert wizard.attack_state.is_active == False, "AttackState should be ended/inactive"
    print(f"Chase cooldown on attack finish: {wizard._chase_cooldown}s")
    assert wizard._chase_cooldown == 1.8, "Chase cooldown should be 1.8 seconds"
    
    # Under cooldown, update_ai must force IDLE state
    player.rect.centerx = 1000
    wizard._update_ai()
    assert wizard.state == FireWizardState.IDLE, f"Under cooldown, state should remain IDLE, got {wizard.state}"
    
    # Update time to elapse cooldown
    wizard.update(dt=1.0)
    assert wizard._chase_cooldown == 0.8, f"Expected remaining cooldown 0.8, got {wizard._chase_cooldown}"
    wizard.update(dt=1.0)
    assert wizard._chase_cooldown == 0.0, f"Expected remaining cooldown 0.0, got {wizard._chase_cooldown}"
    
    # Cooldown elapsed: update_ai should resume chasing/attacking
    wizard._update_ai()
    assert wizard.state == FireWizardState.CHASE, f"Expected state to resume to CHASE, got {wizard.state}"
    
    print("All FireWizard tests passed successfully!")

if __name__ == "__main__":
    test_fire_wizard_behavior()
