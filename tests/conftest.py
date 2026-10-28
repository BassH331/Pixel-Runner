import os
import pytest
import pygame as pg

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DISABLE_TELEMETRY"] = "1"

@pytest.fixture(scope="session", autouse=True)
def init_headless_pygame():
    """Ensure headless SDL video driver, font system, and display surface are initialized for all tests."""
    pg.init()
    pg.font.init()
    try:
        pg.mixer.init()
    except Exception:
        pass
    screen = pg.display.set_mode((1280, 720))
    try:
        from v3x_zulfiqar_gideon import UITheme
        UITheme.configure_overlays(
            stone_path="assets/graphics/UI/PNG/UI board Medium  stone.png",
            parchment_path="assets/graphics/UI/PNG/UI board Medium  parchment.png",
            title_font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Gothic - Regular.otf",
            body_font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf",
            text_color=(60, 40, 20),
        )
    except Exception:
        pass
    yield
    pg.quit()

@pytest.fixture(autouse=True)
def reset_asset_manager_font_cache():
    """Reset font cache between test runs to avoid stale C pointers across pg.quit/pg.init cycles."""
    try:
        from v3x_zulfiqar_gideon import AssetManager
        AssetManager.clear()
    except Exception:
        pass
    if not pg.font.get_init():
        try:
            pg.font.init()
        except Exception:
            pass
    yield
    try:
        from v3x_zulfiqar_gideon import AssetManager
        AssetManager.clear()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def reset_hitbox_registry_cache():
    """Ensure HitboxRegistry in-memory cache is pristine across all test boundaries."""
    try:
        from src.game.entities.hitbox_registry import HitboxRegistry
        HitboxRegistry._cached_config = {}
        HitboxRegistry._rollback_checkpoint = {}
    except Exception:
        pass
    yield
    try:
        from src.game.entities.hitbox_registry import HitboxRegistry
        HitboxRegistry._cached_config = {}
        HitboxRegistry._rollback_checkpoint = {}
    except Exception:
        pass


