import os
import json
import pytest
import pygame as pg

from src.game.entities.skeleton import Skeleton, SkeletonState, BoneDustEffect
from boss_editor import BOSS_SCHEMAS, SKELETON_CATEGORIES, BossEditorApp


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pg.init()
    if not pg.display.get_surface():
        pg.display.set_mode((1, 1), pg.NOFRAME)
    yield
    pg.quit()


class MockPlayer:
    """Mock player object for testing detection and dodging."""
    def __init__(self, x=280, y=300, is_attacking=True, facing_left=False):
        # Position with bottom = y (300)
        self.rect = pg.Rect(x, y - 60, 40, 60)
        self.is_attacking = is_attacking
        self.state = 20  # attack state in PlayerState
        self.facing_left = facing_left


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

    # Advance until reaction delay expires -> triggers teleport
    skeleton._detect_incoming_danger(0.12)
    assert skeleton._teleport_cooldown_timer > 0.0
    assert len(skeleton._active_vfx) >= 2


def test_skeleton_teleport_defense_vfx_and_relocation():
    """Verify teleport defense spawns origin & destination bone dust VFX and repositions skeleton."""
    player = MockPlayer(x=280, y=300, is_attacking=True, facing_left=False)
    skeleton = Skeleton(400, 300, player, tier="boss")  # type: ignore
    skeleton.spidey_sense = 1.0  # God Mode Flank

    initial_x = skeleton.rect.centerx
    initial_vfx_count = len(skeleton._active_vfx)

    skeleton._trigger_teleport_defense()

    # Spawns 2 VFX instances: origin dust shatter and destination dust reform
    assert len(skeleton._active_vfx) == initial_vfx_count + 2
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

    # Minion should retreat further right (away from player approaching from left)
    assert skeleton.rect.centerx > player.rect.centerx + 100
    assert skeleton.state == SkeletonState.IDLE


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
