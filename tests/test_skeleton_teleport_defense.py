import os
import json
import pytest
import pygame as pg

from src.game.entities.skeleton import Skeleton, SkeletonState, BoneDustEffect
from boss_editor import BOSS_SCHEMAS, SKELETON_CATEGORIES, BossEditorApp


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    if not pg.get_init():
        pg.init()
    if not pg.display.get_init() or not pg.display.get_surface():
        pg.display.init()
        pg.display.set_mode((1280, 720), pg.NOFRAME)
    yield


class MockPlayer:
    """Mock player object for testing detection and dodging."""
    def __init__(self, x=280, y=300, is_attacking=True, facing_left=False, state=None, animation_index=0.0):
        # Position with bottom = y (300)
        self.rect = pg.Rect(x, y - 60, 40, 60)
        self.is_attacking = is_attacking
        self.state = state if state is not None else (20 if is_attacking else 50)
        self.facing_left = facing_left
        self.animation_index = animation_index
        self._is_enhanced = False


def test_bone_dust_effect_lifecycle():
    """Verify BoneDustEffect frame progression and finish condition."""
    frames = [pg.Surface((32, 32)) for _ in range(5)]
    vfx = BoneDustEffect(100, 200, frames, fps=20.0)

    assert not vfx.is_finished
    assert vfx.current_frame == 0
    assert vfx.rect.midbottom == (100, 200)

    # Advance by 1 frame duration (1/20 = 0.05s)
    vfx.update(0.05)
    assert vfx.current_frame == 1
    assert not vfx.is_finished

    # Advance past remaining frames
    vfx.update(0.25)
    assert vfx.is_finished
    assert vfx.current_frame >= 4


def test_skeleton_config_and_bone_dust_frames():
    """Verify skeleton loads bone dust frames and config properties."""
    player = MockPlayer()
    skeleton = Skeleton(400, 300, player, tier="boss")  # type: ignore

    assert hasattr(skeleton, "spidey_sense")
    assert hasattr(skeleton, "teleport_dist_min")
    assert hasattr(skeleton, "teleport_dist_max")
    assert hasattr(skeleton, "teleport_cooldown")
    assert hasattr(skeleton, "teleport_reaction_delay")

    assert skeleton.spidey_sense > 0.0
    assert len(skeleton._bone_dust_frames) > 0
    assert skeleton.teleport_dist_min < skeleton.teleport_dist_max


def test_skeleton_detect_incoming_danger_and_reaction_timer():
    """Verify detection counts down reaction timer when player attacks in danger zone."""
    player = MockPlayer(x=280, y=300, is_attacking=True, facing_left=False)
    skeleton = Skeleton(400, 300, player, tier="boss")  # type: ignore
    skeleton.spidey_sense = 1.0
    skeleton.teleport_reaction_delay = 0.10
    skeleton._teleport_reaction_timer = 0.0
    skeleton._teleport_cooldown_timer = 0.0

    # First detection frame begins reaction timer
    skeleton._detect_incoming_danger(0.03)
    assert skeleton._teleport_reaction_timer > 0.0

    # Advance until reaction delay expires -> triggers teleport disappear phase
    skeleton._detect_incoming_danger(0.12)
    assert skeleton._teleport_cooldown_timer > 0.0
    # Phase 1: Disappear dust explosion spawned first
    assert len(skeleton._active_vfx) == 1
    assert skeleton._is_teleporting
    assert skeleton._teleport_arrival_pending

    # Phase 2: Split-second vanish completes -> materialize and appear dust explosion
    skeleton.update(0.25, scroll_speed=0)
    assert len(skeleton._active_vfx) == 2
    assert not skeleton._is_teleporting


def test_skeleton_teleport_defense_vfx_and_relocation():
    """Verify teleport defense spawns origin bone dust VFX first, then destination bone dust on arrival."""
    player = MockPlayer(x=280, y=300, is_attacking=True, facing_left=False)
    skeleton = Skeleton(400, 300, player, tier="boss")  # type: ignore
    skeleton.spidey_sense = 1.0  # God Mode Flank

    initial_x = skeleton.rect.centerx
    initial_vfx_count = len(skeleton._active_vfx)

    skeleton._trigger_teleport_defense()

    # Step 1: Disappear phase - origin dust only, skeleton in transit
    assert len(skeleton._active_vfx) == initial_vfx_count + 1
    assert skeleton._is_teleporting
    assert skeleton._teleport_arrival_pending

    # Step 2: Advance split second past vanish timer (0.20s)
    skeleton.update(0.25, scroll_speed=0)

    # Step 3: Appear phase - destination dust spawned, skeleton relocated
    assert len(skeleton._active_vfx) == initial_vfx_count + 2
    assert not skeleton._is_teleporting
    # In God Mode, flanks behind player
    assert skeleton.rect.centerx < player.rect.centerx
    assert skeleton.state == SkeletonState.ATTACK
    assert skeleton._teleport_cooldown_timer > 0.0


def test_skeleton_iframe_during_teleport():
    """Verify take_damage is ignored when _is_teleporting is True."""
    player = MockPlayer()
    skeleton = Skeleton(400, 300, player, tier="boss")  # type: ignore
    skeleton._is_teleporting = True
    initial_hp = skeleton._health

    taken = skeleton.take_damage(25.0, knockback=(5.0, 0.0))
    assert not taken
    assert skeleton._health == initial_hp


def test_minion_teleport_retreat():
    """Verify minion skeleton teleports away to safety rather than flanking."""
    player = MockPlayer(x=280, y=300, is_attacking=True, facing_left=False)
    skeleton = Skeleton(400, 300, player, tier="minion")  # type: ignore
    skeleton.spidey_sense = 0.25  # Normal dodge

    skeleton._trigger_teleport_defense()
    skeleton.update(0.25, scroll_speed=0)

    # Minion should retreat further right (away from player approaching from left)
    assert skeleton.rect.centerx > player.rect.centerx + 100
    assert skeleton.state in (SkeletonState.IDLE, SkeletonState.CHASE)
    assert skeleton.state != SkeletonState.ATTACK


def test_boss_editor_schemas_and_presets():
    """Verify schemas, categories, and preset files in boss_editor."""
    assert "skeleton" in BOSS_SCHEMAS
    assert "skeleton_minion" in BOSS_SCHEMAS

    skel_schema = BOSS_SCHEMAS["skeleton"]
    slider_keys = [s[0] for s in skel_schema["sliders"]]
    assert "spidey_sense" in slider_keys
    assert "teleport_dist_min" in slider_keys
    assert "teleport_dist_max" in slider_keys
    assert "teleport_cooldown" in slider_keys
    assert "teleport_reaction_delay" in slider_keys

    # Check SKELETON_CATEGORIES
    assert "SPELLS & AI" in SKELETON_CATEGORIES
    assert "MELEE STATS" in SKELETON_CATEGORIES
    assert "spidey_sense" in SKELETON_CATEGORIES["SPELLS & AI"]

    # Check skeleton_presets.json
    preset_path = "game_data/skeleton_presets.json"
    assert os.path.exists(preset_path)
    with open(preset_path, "r") as f:
        presets = json.load(f)
    for slot in ("1", "2", "3"):
        assert slot in presets
        assert "spidey_sense" in presets[slot]
        assert "teleport_dist_min" in presets[slot]


def test_boss_editor_simulation_bone_dust_dodge():
    """Verify boss editor simulation executes Bone Dust dodge and logs appropriately."""
    app = BossEditorApp()
    app.select_boss("skeleton")
    app.mode = "SIMULATION"
    app.sliders["spidey_sense"].val = 1.0  # Force 100% dodge

    initial_x = app.sim_boss_x
    app.simulate_player_attack()

    # Bone dust VFX added for origin and destination
    assert len(app.sim_vfx) == 2
    # Event log recorded the Bone Dust dodge
    assert any("[BONE DUST DODGE]" in log for log in app.sim_events)


def test_skeleton_combo_chaining_in_melee_reach():
    """Verify skeleton immediately chains into follow-up strike when player remains in melee range."""
    # Place player right in front of skeleton
    player = MockPlayer(x=200, y=300, is_attacking=False, facing_left=False)
    skeleton = Skeleton(260, 300, player, tier="minion")  # type: ignore
    skeleton.facing_left = True  # Facing player to the left

    # Begin strike 1
    skeleton._begin_attack(force_anim=1)
    assert skeleton.state == SkeletonState.ATTACK
    assert skeleton._last_attack_type == 1

    # Simulate attack animation progressing to final frame
    anim_len = len(skeleton.animations[SkeletonState.ATTACK])
    skeleton.animation_index = anim_len - 0.05
    # Update skeleton - this triggers completion and combo follow-up
    skeleton.update(dt=0.05, scroll_speed=0)

    # Skeleton should remain in ATTACK state for combo strike 2
    assert skeleton.state == SkeletonState.ATTACK
    assert skeleton._last_attack_type == 2
    assert skeleton._combo_count == 1


def test_skeleton_teleport_never_lands_on_same_spot():
    """Verify skeleton teleport destination is guaranteed to be displaced from origin."""
    player = MockPlayer(x=280, y=300, is_attacking=True, facing_left=False)
    skeleton = Skeleton(400, 300, player, tier="minion")  # type: ignore

    for _ in range(10):
        origin_x = skeleton.rect.centerx
        skeleton._trigger_teleport_defense()
        skeleton.update(0.25, scroll_speed=0)
        dest_x = skeleton.rect.centerx
        # Guaranteed minimum displacement of 140px
        assert abs(dest_x - origin_x) >= 140
        skeleton._teleport_cooldown_timer = 0.0


def test_skeleton_multiple_teleports_after_cooldown():
    """Verify skeleton can teleport multiple times during combat after cooldown expires."""
    player = MockPlayer(x=280, y=300, is_attacking=True, facing_left=False)
    skeleton = Skeleton(400, 300, player, tier="boss")  # type: ignore
    skeleton.spidey_sense = 1.0
    skeleton.teleport_reaction_delay = 0.02
    skeleton.teleport_cooldown = 0.5
    skeleton._teleport_cooldown_timer = 0.0

    # First teleport: triggers disappear phase (1 VFX)
    skeleton._detect_incoming_danger(0.05)
    assert skeleton._teleport_cooldown_timer > 0.0
    assert len(skeleton._active_vfx) == 1

    # Advance time past vanish window (appear phase -> 2 VFX)
    skeleton.update(dt=0.25, scroll_speed=0)
    assert len(skeleton._active_vfx) == 2

    # Advance time past cooldown and past VFX duration
    skeleton.update(dt=0.6, scroll_speed=0)
    assert skeleton._teleport_cooldown_timer == 0.0

    # Second attack: Player turns to face the skeleton
    player.facing_left = (player.rect.centerx > skeleton.rect.centerx)
    player.is_attacking = True

    # Second teleport triggered by player attack (disappear phase -> 1 active VFX)
    skeleton._detect_incoming_danger(0.05)
    assert skeleton._teleport_cooldown_timer > 0.0
    assert len(skeleton._active_vfx) == 1

    # Advance time to complete arrival
    skeleton.update(dt=0.25, scroll_speed=0)
    assert len(skeleton._active_vfx) == 2


def test_skeleton_is_invincible_property():
    """Verify is_invincible returns True during teleportation and hurt/death states."""
    player = MockPlayer()
    skeleton = Skeleton(400, 300, player, tier="boss")  # type: ignore

    assert not skeleton.is_invincible
    skeleton._is_teleporting = True
    assert skeleton.is_invincible

    skeleton._is_teleporting = False
    skeleton.set_state(SkeletonState.HURT)
    assert skeleton.is_invincible

    skeleton.set_state(SkeletonState.DEATH)
    assert skeleton.is_invincible

    skeleton.set_state(SkeletonState.IDLE, force=True)
    assert not skeleton.is_invincible


def test_skeleton_detect_and_dodge_all_attack_types_at_distance():
    """Verify skeleton detects all attack types (W, E, F, Q) at extended distances."""
    attack_cases = [
        # (name, state_val, test_dist, anim_idx)
        ("ATTACK_POWER (W)", 22, 380, 0.0),
        ("ATTACK_SMASH (E)", 21, 320, 0.0),
        ("ATTACK_THRUST (Q)", 20, 300, 0.0),
        ("SPECIAL_ATTACK (F)", 23, 320, 15.0),
    ]

    for name, state_val, dist, anim_idx in attack_cases:
        player = MockPlayer(x=200, y=300, is_attacking=True, facing_left=False, state=state_val, animation_index=anim_idx)
        skeleton = Skeleton(200 + dist, 300, player, tier="boss")  # type: ignore
        skeleton.spidey_sense = 1.0
        skeleton.teleport_reaction_delay = 0.08
        skeleton._teleport_reaction_timer = 0.0
        skeleton._teleport_cooldown_timer = 0.0

        # Run detection: should recognize threat at this distance (> 180px)
        skeleton._detect_incoming_danger(0.02)
        assert skeleton._teleport_reaction_timer > 0.0, f"Failed to detect danger for {name} at distance {dist}px"

        # Advance reaction timer to trigger teleport defense
        skeleton._detect_incoming_danger(0.10)
        assert skeleton._teleport_cooldown_timer > 0.0, f"Failed to trigger teleport for {name} at distance {dist}px"


def test_skeleton_omni_directional_power_attack_detection():
    """Verify skeleton detects 360-spin Power Attack even when positioned behind the player."""
    # Player is at x=300, facing left (looking away from skeleton at x=450)
    player = MockPlayer(x=300, y=300, is_attacking=True, facing_left=True, state=22)
    skeleton = Skeleton(450, 300, player, tier="boss")  # type: ignore
    skeleton.spidey_sense = 1.0
    skeleton.teleport_reaction_delay = 0.08
    skeleton._teleport_reaction_timer = 0.0

    # Skeleton is behind the player (dist=150px); Power Attack is omni-directional
    skeleton._detect_incoming_danger(0.02)
    assert skeleton._teleport_reaction_timer > 0.0, "Skeleton failed to detect Power Attack from behind"

