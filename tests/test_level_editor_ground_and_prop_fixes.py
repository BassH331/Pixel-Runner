import os
import sys
import json
import pytest
import pygame as pg

if not pg.get_init():
    pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1280, 720), pg.NOFRAME)

from v3x_zulfiqar_gideon import UITheme, AssetManager
from src.game.systems.environment_manager import EnvironmentManager, EnvironmentProp
from level_editor import App


def test_prop_default_collision_deco():
    """Verify that newly created props default to deco and is_ground=False."""
    prop = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 32, 32],
        pos_x=100.0,
        pos_y=200.0,
    )
    assert prop.collision_type == "deco"
    assert prop.is_ground is False


def test_prop_explicit_solid_is_ground():
    """Verify that props explicitly set to solid or platform default is_ground to True."""
    p_solid = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 32, 32],
        pos_x=100.0,
        pos_y=200.0,
        collision_type="solid",
    )
    assert p_solid.collision_type == "solid"
    assert p_solid.is_ground is True

    p_plat = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 32, 32],
        pos_x=100.0,
        pos_y=200.0,
        collision_type="platform",
    )
    assert p_plat.collision_type == "platform"
    assert p_plat.is_ground is True


def test_get_ground_y_at_layer_isolation():
    """Verify that props on non-gameplay layers (e.g. layer 9, or parallax != 1.0) do NOT pollute ground height."""
    env = EnvironmentManager(1280, 720, env_config={"ground_y": 568})
    # Add a prop on layer 9 with parallax 1.0 that was accidentally solid
    p_airborne_l9 = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 32, 32],
        pos_x=100.0,
        pos_y=200.0,
        layer_index=9,
        parallax_ratio=1.0,
        collision_type="solid",
        is_ground=True,
    )
    env.props.append(p_airborne_l9)

    # get_ground_y_at should ignore layer 9 and return ground_y (568.0)
    assert env.get_ground_y_at(105.0) == 568.0


def test_get_ground_y_at_current_y_ceiling_isolation():
    """Verify that a high platform above entity's head is not treated as ground when entity is on the road."""
    env = EnvironmentManager(1280, 720, env_config={"ground_y": 568})
    p_bridge = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 100, 32],
        pos_x=50.0,
        pos_y=200.0,
        layer_index=6,
        parallax_ratio=1.0,
        collision_type="solid",
        is_ground=True,
    )
    env.props.append(p_bridge)

    # When entity is standing on the road (current_y = 568.0), ground should be 568.0
    gy_on_road = env.get_ground_y_at(75.0, current_y=568.0)
    assert gy_on_road == 568.0

    # When entity jumps onto the bridge (current_y = 200.0), ground should be 200.0
    gy_on_bridge = env.get_ground_y_at(75.0, current_y=200.0)
    assert gy_on_bridge == 200.0


def test_level_editor_slicer_creates_deco_prop():
    """Verify that slicing a prop on L4 (props) defaults to deco collision and L3 defaults to solid."""
    app = App()
    app.active_idx = 0
    app.level_files = ["game_data/level_1.json"]
    app.load(0)
    app.go5()

    # On L4 (Props & Objects), newly added props are decorative
    app.active_layer_filter = 4
    initial_count = len(app.env_mgr.props)
    app._on_select_prop_from_slicer("assets/graphics/background images/new_bg_images/bg_image.png", [0, 0, 32, 32])
    assert len(app.env_mgr.props) == initial_count + 1

    newly_added = app.env_mgr.props[-1]
    assert newly_added.collision_type == "deco"
    assert newly_added.is_ground is False

    # On L3 (Ground & Terrain), newly added props are solid
    app.active_layer_filter = 3
    app._on_select_prop_from_slicer("assets/graphics/background images/new_bg_images/bg_image.png", [0, 0, 32, 32])
    terrain_prop = app.env_mgr.props[-1]
    assert terrain_prop.collision_type == "solid"
    assert terrain_prop.is_ground is True


def test_level_editor_level_manager_modal_event_delegation():
    """Verify that _h5 delegates events to level_mgr_modal when open."""
    app = App()
    app.active_idx = 0
    app.level_files = ["game_data/level_1.json"]
    app.load(0)
    app.go5()

    modal_handled = []
    class DummyModal:
        def on(self, ev):
            modal_handled.append(ev)

    app.level_mgr_modal = DummyModal()
    dummy_ev = pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(100, 100))
    app._h5(dummy_ev)

    assert len(modal_handled) == 1
    assert modal_handled[0] == dummy_ev


def test_environment_prop_animated_frame_discovery_and_loop():
    """Verify that EnvironmentProp discovers multi-frame sequences and loops them."""
    prop = EnvironmentProp(
        texture_path="assets/graphics/Props/spr_FirePlace_strip_frames/frame_005.png",
        slice_rect=[13, 27, 41, 37],
        pos_x=5801.0,
        pos_y=284.0,
        scale=1.0,
        anim_speed=0.1,
    )
    assert len(prop.frames) == 6
    assert prop.frame_idx == 0

    # Test update advances frames
    prop.update(0.1)
    assert prop.frame_idx == 1

    prop.update(0.5)
    # 1 + 5 = 6 -> loops back to 0
    assert prop.frame_idx == 0


def test_environment_manager_updates_animated_props():
    """Verify that EnvironmentManager.update advances all animated props."""
    env = EnvironmentManager(1280, 720)
    prop = EnvironmentProp(
        texture_path="assets/graphics/Props/spr_FirePlace_strip_frames/frame_000.png",
        slice_rect=[13, 27, 41, 37],
        pos_x=5801.0,
        pos_y=284.0,
        anim_speed=0.1,
    )
    env.props.append(prop)
    assert prop.frame_idx == 0

    env.update(0.1, player_speed=0.0)
    assert prop.frame_idx == 1

