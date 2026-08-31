import os
import json
import pytest
import pygame as pg
from unittest.mock import MagicMock

from src.game.systems.shadow_registry import ShadowRegistry, ShadowProfile
from src.game.systems.shadow_renderer import ShadowRenderer


@pytest.fixture(autouse=True)
def init_pygame():
    pg.init()
    if not pg.display.get_surface():
        pg.display.set_mode((100, 100))
    yield
    # Cleanup / reset cache
    ShadowRegistry._cache.clear()
    ShadowRegistry._last_mtime = -1.0


def test_shadow_profile_defaults():
    profile = ShadowProfile()
    assert profile.alpha == 120
    assert profile.squash_ratio == 0.25
    assert profile.y_offset == 0
    assert profile.fade_height == 250.0
    assert profile.ground_snap == 12.0
    assert profile.scale_mult == 1.0


def test_shadow_profile_serialization():
    data = {
        "alpha": 140,
        "squash_ratio": 0.3,
        "y_offset": 5,
        "fade_height": 300.0,
        "ground_snap": 15.0,
        "scale_mult": 1.1,
    }
    profile = ShadowProfile.from_dict(data)
    assert profile.alpha == 140
    assert profile.squash_ratio == 0.3
    assert profile.y_offset == 5
    assert profile.fade_height == 300.0
    assert profile.ground_snap == 15.0
    assert profile.scale_mult == 1.1

    exported = profile.to_dict()
    assert exported == data


def test_shadow_registry_get_profile():
    # Built-in or config key
    player_prof = ShadowRegistry.get_profile("player")
    assert player_prof is not None
    assert player_prof.alpha > 0

    # Non-existent fallback to default
    unknown_prof = ShadowRegistry.get_profile("non_existent_entity_xyz")
    assert unknown_prof is not None
    assert unknown_prof.alpha == ShadowRegistry.get_profile("default").alpha


def test_shadow_renderer_silhouette_generation():
    surf = pg.Surface((60, 60), pg.SRCALPHA)
    surf.fill((255, 0, 0, 255), (10, 10, 40, 40))

    shadow_surf, orig_feet_y, shadow_feet_bottom = ShadowRenderer.get_silhouette_shadow(
        surf, 60, 15, alpha=115
    )

    assert shadow_surf.get_size() == (60, 15)
    assert orig_feet_y == 50
    assert shadow_feet_bottom <= 15

    # Check alpha on center of shadow
    color = shadow_surf.get_at((30, 7))
    assert color[0] == 0 and color[1] == 0 and color[2] == 0
    assert color[3] > 0


def test_shadow_renderer_render_entity_shadow():
    target = pg.Surface((200, 200), pg.SRCALPHA)

    entity = MagicMock()
    entity_surf = pg.Surface((50, 50), pg.SRCALPHA)
    entity_surf.fill((200, 200, 200, 255), (5, 5, 40, 40))
    entity.image = entity_surf
    entity.rect = pg.Rect(50, 50, 50, 50)
    entity.image_offset = None
    entity.visible = True
    entity.is_death_complete = False

    # Render without errors
    ShadowRenderer.render_entity_shadow(target, entity)
    # Check pixels were drawn onto target
    bounding = target.get_bounding_rect()
    assert bounding.width > 0 and bounding.height > 0
