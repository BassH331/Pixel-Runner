import pygame as pg
import sys
import os
from unittest.mock import MagicMock

# Add src to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game.entities.fire_wizard import FireWizard, FireWizardState, Fireball
from src.game.entities.player import Player

pg.init()
pg.display.set_mode((1280, 720), pg.HIDDEN)

def run_simulation():
    print("====================================================")
    print("      FIRE WIZARD ADVANCED BEHAVIOR SIMULATION      ")
    print("====================================================")
    
    mock_audio = MagicMock()
    player = Player(100, 500, mock_audio)
    
    # 1. Retreat Verification
    print("\n--- 1. RETREAT VERIFICATION ---")
    boss = FireWizard(
        x=150, 
        y=500, 
        player=player, 
        tier="boss", 
        sprite_root="assets/wizard/",
        custom_scale=4.11,
        custom_health=100.0
    )
    boss._chase_cooldown = 0.0
    boss._attack_cooldown = 10.0  # prevent attacking
    
    print(f"Start: Player x={player.rect.centerx}, Boss x={boss.rect.centerx}, Dist={boss.rect.centerx - player.rect.centerx:.1f}")
    for tick in range(1, 11):
        boss.update(1.0 / 60.0)
        dist = boss.rect.centerx - player.rect.centerx
        state_name = boss.state.name if boss.state else "UNKNOWN"
        print(f"Tick {tick:02d} | Boss x={boss.rect.centerx} (dist={dist:+.1f}) | State={state_name}")
    
    # 2. Attack, Mana Consumption, & Teleport Recharge
    print("\n--- 2. MANA DEPLETION & DBZ TELEPORT RECHARGE ---")
    boss = FireWizard(
        x=300, 
        y=500, 
        player=player, 
        tier="boss", 
        sprite_root="assets/wizard/",
        custom_scale=4.11,
        custom_health=100.0
    )
    boss._chase_cooldown = 0.0
    boss._attack_cooldown = 0.0
    
    # Let's run ticks until boss casts fireballs and depletes mana
    stagnant_detected_tick = 0
    teleport_detected = False
    for tick in range(1, 600):
        old_x = boss.rect.centerx
        boss.update(1.0 / 60.0)
        new_x = boss.rect.centerx
        
        # Check if boss teleported
        if abs(new_x - old_x) > 100:
            print(f"Tick {tick:02d} | TELEPORT DETECTED! Boss jumped from x={old_x} to x={new_x} (dist to player={abs(new_x - player.rect.centerx):.1f})")
            teleport_detected = True
            
        state_name = boss.state.name if boss.state else "UNKNOWN"
        
        # Detect low mana stagnant mode entry
        if boss._is_stagnant and stagnant_detected_tick == 0:
            stagnant_detected_tick = tick
            print(f"Tick {tick:02d} | LOW MANA STAGNERING DETECTED! Boss is stagnant at x={boss.rect.centerx} | Stagnant Timer={boss._stagnant_timer:.1f}")
            
        # If we have been stagnant for 30 ticks, hit the boss to trigger teleport!
        if stagnant_detected_tick > 0 and tick == stagnant_detected_tick + 30 and not teleport_detected:
            print(f"Tick {tick:02d} | Simulating player attack! Calling boss.take_damage(1.0)...")
            boss.take_damage(1.0)
            
        if tick % 50 == 0 or teleport_detected:
            print(f"Tick {tick:02d} | Boss x={boss.rect.centerx} | State={state_name} | Mana={boss._mana:.1f} | Stagnant={boss._is_stagnant} | Recharging={boss._is_recharging}")
            
        if teleport_detected and not boss._is_recharging:
            print(f"Tick {tick:02d} | Mana fully recharged to {boss._mana:.1f}! Teleport recharge cycle complete.")
            break
            
    # 3. Chase Delay Window
    print("\n--- 3. CHASE DELAY WINDOW ---")
    player.rect.centerx = 100
    boss = FireWizard(
        x=300, 
        y=500, 
        player=player, 
        tier="boss", 
        sprite_root="assets/wizard/",
        custom_scale=4.11,
        custom_health=100.0
    )
    # Boss is in IDLE
    boss.set_state(FireWizardState.IDLE, force=True)
    boss._chase_cooldown = 0.0
    boss._attack_cooldown = 10.0  # prevent attacking
    
    # Player runs away (x goes from 100 to 800)
    player.rect.centerx = 800
    print(f"Player ran to x={player.rect.centerx}. Boss x={boss.rect.centerx} | Dist={abs(boss.rect.centerx - player.rect.centerx)}")
    
    # We update the boss. The first update should trigger a 0.8 seconds (48 frames) delay timer.
    # So for 48 frames, the boss should stay in IDLE state.
    has_entered_chase = False
    for frame in range(1, 60):
        boss.update(1.0 / 60.0)
        state_name = boss.state.name if boss.state else "UNKNOWN"
        if state_name == "CHASE" and not has_entered_chase:
            print(f"Frame {frame:02d} | Boss entered CHASE state! Delay window took {frame/60.0:.2f} seconds.")
            has_entered_chase = True
            break
        elif frame % 10 == 0:
            print(f"Frame {frame:02d} | Boss State={state_name} | Delay Timer={boss._chase_delay_timer:.2f}")

    print("\nVerification complete!")

if __name__ == "__main__":
    run_simulation()
