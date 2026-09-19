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

