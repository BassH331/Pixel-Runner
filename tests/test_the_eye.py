"""
Unit and integration tests for 'The Eye' Story Resource Tree & Dialogue Controller plugin.
Validates Unity-style hierarchical tree construction, dual timeline/entity mapping,
explicit Is Taunt toggling, filtering, persistence with backups, and GUI staging.
"""

import os
import json
import tempfile
import pytest
import pygame as pg

if not pg.get_init():
    pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1440, 880), pg.NOFRAME)

from src.game.systems.the_eye_manager import (
    TheEyePerceptionManager,
    StoryNode,
    SpeechItem,
    TreeItem,
    LEVEL_1_PATH,
    STORYLINE_PATH,
)
from the_eye import TheEyeApp


@pytest.fixture
def isolated_eye_manager():
    """Create isolated PerceptionManager with temporary copies of game data."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_level = os.path.join(tmp_dir, "level_1.json")
        tmp_story = os.path.join(tmp_dir, "storyline_config.json")

        if os.path.exists(LEVEL_1_PATH):
            with open(LEVEL_1_PATH, "r", encoding="utf-8") as src, open(tmp_level, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        else:
            with open(tmp_level, "w", encoding="utf-8") as dst:
                json.dump({"entities": []}, dst)

        if os.path.exists(STORYLINE_PATH):
            with open(STORYLINE_PATH, "r", encoding="utf-8") as src, open(tmp_story, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        else:
            with open(tmp_story, "w", encoding="utf-8") as dst:
                json.dump({"boss_dialogue": {}, "relics": {}}, dst)

        mgr = TheEyePerceptionManager(level_path=tmp_level, storyline_path=tmp_story)
        yield mgr


def test_the_eye_loads_chronological_journey():
    """Verify that all 16 story nodes load in strictly ascending distance order."""
    mgr = TheEyePerceptionManager.get_instance()
    nodes = mgr.get_nodes()
    assert len(nodes) == 16, f"Expected 16 story nodes, found {len(nodes)}"

    prev_dist = -1
    entity_types = set()
    for node in nodes:
        assert node.distance >= prev_dist, f"Distance ordering broken at {node.title}"
        prev_dist = node.distance
        entity_types.add(node.entity_type)

    assert "NPC" in entity_types
    assert "ENEMY" in entity_types
    assert "MINI-BOSS" in entity_types
    assert "BOSS" in entity_types
    assert "RELIC" in entity_types
    assert "LORE" in entity_types


def test_the_eye_unity_timeline_and_entity_trees():
    """Verify Unity-style hierarchical tree building for Timeline and Entity perspectives."""
    mgr = TheEyePerceptionManager.get_instance()

    # 1. Timeline Tree: Root -> Acts -> Milestones -> Entities -> Speeches
    t_root = mgr.build_timeline_tree()
    assert t_root.node_type == "root"
    assert len(t_root.children) == 4  # 4 Acts

    act1 = t_root.children[0]
    assert act1.node_type == "act"
    assert "Act I" in act1.label
    assert len(act1.children) > 0  # Milestones

    milestone1 = act1.children[0]
    assert milestone1.node_type == "milestone"
    assert len(milestone1.children) > 0  # Entity child

    entity1 = milestone1.children[0]
    assert entity1.node_type == "entity"
    assert len(entity1.children) > 0  # Speeches & Taunts

    # 2. Entity Tree: Root -> Entity Categories -> Entities -> Speeches
    e_root = mgr.build_entity_tree()
    assert e_root.node_type == "root"
    assert len(e_root.children) >= 3  # Bosses, NPCs, Enemies, Relics

    cat_bosses = e_root.children[0]
    assert "BOSSES" in cat_bosses.label
    assert len(cat_bosses.children) >= 4  # Gatekeeper, Blood Zombie, Fire Wizard, Dark Ronin


def test_the_eye_flatten_tree_and_taunt_filter():
    """Verify flatten_tree filtering by search query and taunt/dialogue type."""
    mgr = TheEyePerceptionManager.get_instance()
    t_root = mgr.build_timeline_tree()

    # Flatten all
    all_rows = mgr.flatten_tree(t_root, type_filter="ALL")
    assert len(all_rows) > 30

    # Filter Taunts Only
    taunt_rows = mgr.flatten_tree(t_root, type_filter="TAUNT_ONLY")
    speech_taunts = [item for item, _ in taunt_rows if item.node_type == "speech"]
    assert len(speech_taunts) > 0
    for s in speech_taunts:
        assert s.is_taunt is True

    # Filter Dialogue Only
    dialogue_rows = mgr.flatten_tree(t_root, type_filter="DIALOGUE_ONLY")
    speech_dialogues = [item for item, _ in dialogue_rows if item.node_type == "speech"]
    assert len(speech_dialogues) > 0
    for s in speech_dialogues:
        assert s.is_taunt is False

    # Search filter
    search_rows = mgr.flatten_tree(t_root, filter_text="zombie")
    assert any("Zombie" in item.label for item, _ in search_rows)


def test_the_eye_speech_item_crud_and_is_taunt_toggle(isolated_eye_manager):
    """Verify updating text, toggling is_taunt, adding and deleting speeches."""
    mgr = isolated_eye_manager

    # Find a speech item
    bz_speeches = mgr._get_speeches_for_node("node_13_blood_zombie")
    assert len(bz_speeches) > 0
    target_speech = bz_speeches[0]

    # Toggle is_taunt
    orig_taunt = target_speech.is_taunt
    mgr.update_speech(target_speech.speech_id, is_taunt=not orig_taunt)
    assert target_speech.is_taunt == (not orig_taunt)

    # Edit speech text
    mgr.update_speech(target_speech.speech_id, text="A completely customized battle cry.")
    assert target_speech.text == "A completely customized battle cry."

    # Add a new speech item
    new_item = mgr.add_speech_item("node_13_blood_zombie", "Stand fast, runner!", category="combat_taunt", is_taunt=True)
    assert new_item is not None
    assert new_item.speech_id in mgr.speech_items
    assert new_item.is_taunt is True

    # Delete speech item
    del_ok = mgr.delete_speech_item(new_item.speech_id)
    assert del_ok is True
    assert new_item.speech_id not in mgr.speech_items


def test_the_eye_save_and_backup_persistence(isolated_eye_manager):
    """Verify save_perception writes valid JSON and generates automatic backups."""
    mgr = isolated_eye_manager

    # Alter Dark Ronin final boss pre-fight dialogue
    ronin_node = mgr.get_node_by_id("node_15_dark_ronin")
    assert ronin_node is not None
    ronin_node.conversations["pre_fight"] = ["You finally made it to the summit, fledgling."]
    ronin_node.conversations["corruption_high"] = "You are already a hollow husk of Andras."

    success, msg = mgr.save_perception()
    assert success is True
    assert "saved" in msg.lower() or "successfully" in msg.lower()

    # Verify storyline_config was written to disk
    with open(mgr.storyline_path, "r", encoding="utf-8") as f:
        saved_story = json.load(f)

    ronin_saved = saved_story.get("boss_dialogue", {}).get("DarkRonin", {})
    assert ronin_saved["pre_fight"] == ["You finally made it to the summit, fledgling."]
    assert ronin_saved["corruption_variants"]["high"] == "You are already a hollow husk of Andras."

    # Second save generates a backup file
    mgr.save_perception()
    backup_files = [f for f in os.listdir(os.path.dirname(mgr.storyline_path)) if "backup" in f]
    assert len(backup_files) >= 1


def test_the_eye_3d_tree_model_and_projection():
    """Verify 3D tree node construction, golden angle spiral, and perspective projection."""
    mgr = TheEyePerceptionManager.get_instance()
    app = TheEyeApp(headless=True)
    tree_3d = app.tree_3d

    assert len(tree_3d.nodes_3d) > 30
    assert len(tree_3d.branches_3d) > 30
    assert len(tree_3d.stars_3d) > 50

    # Verify root node
    assert "root" in tree_3d.nodes_3d
    root_node = tree_3d.nodes_3d["root"]
    assert root_node.node_type == "trunk"

    # Verify projection
    sx, sy, z_cam = tree_3d.project_3d_point(0.0, 0.0, 0.0)
    assert sx is not None
    assert sy is not None
    assert z_cam > 0

    # Verify 3D camera controls
    orig_yaw = tree_3d.yaw
    tree_3d.yaw += 0.5
    tree_3d.pitch += 0.2
    assert tree_3d.yaw == orig_yaw + 0.5

    tree_3d.reset_camera()
    assert tree_3d.yaw == 0.65


def test_the_eye_gui_smoke_app():
    """Verify that TheEyeApp initializes headlessly, operates 3D tree, toggles is_taunt, and draws."""
    app = TheEyeApp(headless=True)
    assert app.sw == 1440
    assert app.sh == 880
    assert app.running is True

    # Check 3D controls
    assert app.tree_3d is not None
    assert app.tree_2d is not None
    assert app.active_view == "3D_TREE"

    # Update and draw frame
    app.update(0.016)
    app.draw()

    # Switch to 2D TreeView
    app.active_view = "2D_TREEVIEW"
    app.btn_mode_3d.is_active = False
    app.btn_mode_2d.is_active = True
    app.update(0.016)
    app.draw()
    assert app.active_view == "2D_TREEVIEW"

    # Switch back to 3D Tree
    app.active_view = "3D_TREE"
    app.btn_mode_3d.is_active = True
    app.btn_mode_2d.is_active = False
    app.update(0.016)
    app.draw()

    # Select a speech and toggle Is Taunt
    if app.active_speech:
        cur_taunt = app.active_speech.is_taunt
        app.toggle_active_speech_taunt(not cur_taunt)
        assert app.active_speech.is_taunt == (not cur_taunt)

    # Test search filter
    app.search_bar.text = "Blood"
    app.tree_3d.search_text = "Blood"
    app.update(0.016)
    app.draw()

    # Advance frame with simulation
    app.update(0.2)
    app.draw()


def test_the_eye_world_events_save_and_trigger_scheduling(isolated_eye_manager):
    """Verify that editing entities in The Eye updates level_1.json world_events and preserves trigger scheduling."""
    mgr = isolated_eye_manager

    # 1. Verify speech items have trigger scheduling attributes
    for item in mgr.speech_items.values():
        assert hasattr(item, "trigger_type")
        assert hasattr(item, "hold_duration")
        assert hasattr(item, "audio_cue")
        assert item.hold_duration > 0
        assert item.trigger_type in ("distance", "proximity", "combat_taunt", "pre_fight", "death_line", "corruption")

    # 2. Edit Cursed Grimoire dialogue and combat taunts
    grim_node = mgr.get_node_by_id("node_01_grimoire")
    assert grim_node is not None
    grim_node.conversations["primary"] = "The forest hungers for fresh sacrifices."
    grim_node.conversations["combat_taunts"] = ["Taste the ancient ash!"]

    # 3. Save perception
    success, msg = mgr.save_perception()
    assert success is True

    # 4. Verify level_1.json has the updated world_events entry
    with open(mgr.level_path, "r", encoding="utf-8") as f:
        saved_level = json.load(f)

    world_events = saved_level.get("world_events", [])
    grim_event = None
    for ev in world_events:
        if ev.get("params", {}).get("is_magic_book") or str(ev.get("id")) == "10":
            grim_event = ev
            break

    assert grim_event is not None
    assert grim_event["params"]["text"] == "The forest hungers for fresh sacrifices."
    assert grim_event["params"]["combat_taunts"] == ["Taste the ancient ash!"]


def test_the_eye_live_observer_bridge_sync(tmp_path, monkeypatch):
    """Verify TheEyeApp observer bridge synchronizes live state, tracks runner in 3D, and handles disconnects."""
    import time

    live_path = os.path.join("scratch", "the_eye_live_state.json")
    os.makedirs("scratch", exist_ok=True)

    heartbeat_data = {
        "timestamp": time.time(),
        "world_distance": 14250,
        "level_end_distance": 36000,
        "progress_ratio": 14250 / 36000.0,
        "player_health": 85.0,
        "player_max_health": 100.0,
        "corruption": 30.0,
        "total_souls": 450,
        "active_boss": "Ignis, Pyromancer of the Abyss",
        "active_boss_health": 900.0,
        "active_act": "Act III: Threshold of Discord",
        "last_spoken_taunt": {
            "speaker": "Ignis, Pyromancer of the Abyss",
            "text": "Your ashes will feed the eternal flame!",
            "time": time.time(),
        },
    }

    with open(live_path, "w", encoding="utf-8") as f:
        json.dump(heartbeat_data, f)

    app = TheEyeApp(headless=True)
    assert app.is_game_connected is True
    assert app.live_state["world_distance"] == 14250
    assert app.live_state["active_boss"] == "Ignis, Pyromancer of the Abyss"

    # Step frame and render
    app.update(0.016)
    app.draw()

    # Verify runner position was projected in 3D space
    assert app.live_runner_screen_pos is not None
    rx, ry = app.live_runner_screen_pos
    assert isinstance(rx, int) and isinstance(ry, int)

    # Test stale disconnect
    stale_data = dict(heartbeat_data)
    stale_data["timestamp"] = time.time() - 10.0
    with open(live_path, "w", encoding="utf-8") as f:
        json.dump(stale_data, f)

    app._poll_live_game_state()
    assert not app.is_game_connected


def test_the_eye_button_click_animation_and_save_toast():
    """Verify EyeButton press timer, success trigger, and save toast confirmation banner."""
    app = TheEyeApp(headless=True)

    # 1. Test EyeButton click event
    click_event = pg.event.Event(pg.MOUSEBUTTONDOWN, {"button": 1, "pos": (1150, 20)})
    handled = app.btn_save.handle_event(click_event)
    assert handled is True
    assert app.btn_save.pressed_timer == 0.15

    # 2. Advance time and draw frame during press state
    app.update(0.05)
    assert app.btn_save.pressed_timer > 0
    app.draw()

    # 3. Test save_changes triggers button success state and top banner toast
    app.save_changes()
    assert app.btn_save.success_timer > 0
    assert app.btn_save.success_text == "✓ SAVED!"
    assert app.save_toast_timer > 0
    assert "✓ PERCEPTION & DIALOGUE SAVED TO DISK!" in app.save_toast_msg

    # 4. Step frame and render toast banner
    app.update(0.1)
    app.draw()

    # 5. Fast-forward past timers
    app.update(4.0)
    assert app.btn_save.success_timer == 0.0
    assert app.save_toast_timer == 0.0



