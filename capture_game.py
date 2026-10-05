"""
capture_game.py — Headless screenshot sweep for Pixel Runner.

Captures:
  - Story state (prologue screen)
  - Main menu
  - Gameplay base frame (ground alignment, HUD)
  - HUD with corruption bar active (simulated kills)
  - HUD with relic strip partially filled
  - Cinematic overlay (Andras bark)
  - 60 consecutive live gameplay frames (1-second burst)
  - Boss encounter freeze frame
  - Relic reveal panel

All output goes to  screenshots/  relative to this script.
Run from inside Pixel-Runner/:
    python capture_game.py
"""

import os, sys, pathlib

# ── headless display ──────────────────────────────────────────────────────────
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["GAME_LEVEL_PATH"] = "game_data/level_1.json"

import pygame as pg
pg.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
pg.init()
try:
    pg.mixer.init()
except Exception:
    pass

SCREEN_W, SCREEN_H = 1280, 720
screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
pg.display.set_caption("capture")

OUT = pathlib.Path("screenshots")
OUT.mkdir(exist_ok=True)

n = [0]
def save(label: str):
    n[0] += 1
    path = OUT / f"{n[0]:03d}_{label}.png"
    pg.image.save(screen, str(path))
    print(f"  saved  {path.name}")

# ── V3X bootstrap ─────────────────────────────────────────────────────────────
from v3x_zulfiqar_gideon import (
    UITheme, StateManager, AudioManager, AssetManager
)

UITheme.configure_buttons(
    assets={
        "big":       ("assets/graphics/UI/PNG/TextBTN_Big.png",
                      "assets/graphics/UI/PNG/TextBTN_Big_Pressed.png"),
        "medium":    ("assets/graphics/UI/PNG/TextBTN_Medium.png",
                      "assets/graphics/UI/PNG/TextBTN_Medium_Pressed.png"),
        "cancel":    ("assets/graphics/UI/PNG/TextBTN_Cancel.png",
                      "assets/graphics/UI/PNG/TextBTN_Cancel_Pressed.png"),
        "new_start": ("assets/graphics/UI/PNG/TextBTN_New-Start.png",
                      "assets/graphics/UI/PNG/TextBTN_New-Start_Pressed.png"),
    },
    font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf",
)
UITheme.configure_notifications(
    banner_path="assets/graphics/UI/PNG/IRONY TITLE  Large.png",
    icons={
        "gray":   "assets/graphics/UI/PNG/Exclamation_Gray.png",
        "red":    "assets/graphics/UI/PNG/Exclamation_Red.png",
        "yellow": "assets/graphics/UI/PNG/Exclamation_Yellow.png",
    },
    font_path="assets/font/Abaddon Bold.ttf",
)
UITheme.configure_overlays(
    stone_path="assets/graphics/UI/PNG/UI board Medium  stone.png",
    parchment_path="assets/graphics/UI/PNG/UI board Medium  parchment.png",
    title_font_path="assets/font/Abaddon Bold.ttf",
    body_font_path="assets/graphics/Darinia/Darinia.ttf",
    text_color=(60, 40, 20),
    font_size=32,
    backdrop_alpha=170,
)

audio_manager = AudioManager()
state_manager  = StateManager(audio_manager=audio_manager)

DT = 1000.0 / 60.0  # 16.67 ms fixed step

def tick(state, n_frames=1):
    for _ in range(n_frames):
        state.update(DT)

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Story state — prologue text
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1] Story state …")
from src.game.states.story_state import StoryState
story = StoryState(state_manager)
tick(story, 5)
story.draw(screen)
save("story_opening")

tick(story, 30)
story.draw(screen)
save("story_text_typing")

# skip to end of text
try:
    story.anim_renderer.skip_to_end()
    story.is_text_complete = True
except Exception:
    pass
tick(story, 10)
story.draw(screen)
save("story_text_complete")

# ─────────────────────────────────────────────────────────────────────────────
# 2.  Main menu
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2] Main menu …")
from src.game.states.main_menu_state import MainMenuState
menu = MainMenuState(state_manager)
tick(menu, 10)
menu.draw(screen)
save("main_menu")

# ─────────────────────────────────────────────────────────────────────────────
# 3.  GameState — cold start (no corruption, clean HUD)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3] GameState cold start …")
from src.game.states.game_state import GameState
game = GameState(state_manager)

# warm up — let world and entities settle
tick(game, 10)
game.draw(screen)
save("gameplay_cold_hud")

# 10 more frames — player idle
tick(game, 10)
game.draw(screen)
save("gameplay_idle")

# ─────────────────────────────────────────────────────────────────────────────
# 4.  Simulate kills → raise corruption → screenshot corruption bar + vignette
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] Corruption ramp …")
cm = game.corruption_manager

# Small corruption — just appears
cm.add(10)
game.draw(screen)
save("corruption_10_bar_visible")

# Tainted threshold (>33)
cm.add(25)   # total ~35
game.draw(screen)
save("corruption_35_tainted")

# Corrupted threshold (>66)
cm.add(33)   # total ~68
game.draw(screen)
save("corruption_68_corrupted_vignette")

# Void threshold (>90)
cm.add(25)   # total ~93
game.draw(screen)
save("corruption_93_void")

# reset to mid for rest of captures
cm._value = 45.0

# ─────────────────────────────────────────────────────────────────────────────
# 5.  Relic HUD strip — simulate 3 relics collected
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5] Relic strip …")
rm = game.relic_manager
rm._collected = ["shattered_gauntlet", "tainted_sigil", "vial_of_void_blood"]
game.draw(screen)
save("relic_strip_3_collected")

rm._collected = ["shattered_gauntlet", "tainted_sigil", "vial_of_void_blood",
                  "hollowed_ledger_page", "candoras_tear", "amalgam_core"]
game.draw(screen)
save("relic_strip_all_6_collected")

rm._collected = []

# ─────────────────────────────────────────────────────────────────────────────
# 6.  Cinematic overlay — Andras bark (Speaker.ANDRAS tint)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6] Cinematic overlay — Andras …")
from src.game.systems.custom_events import Speaker

overlay = game.cinematic_narrative_overlay
try:
    overlay.show_bark(
        "You are mine now. In all but name.",
        speaker=Speaker.ANDRAS
    )
    tick(game, 5)   # let typewriter start
    game.draw(screen)
    save("cinematic_andras_bark")

    tick(game, 30)  # more typing
    game.draw(screen)
    save("cinematic_andras_bark_typing")
except Exception as e:
    print(f"   overlay error: {e}")

# Moon Knight bark
try:
    overlay.show_bark(
        "I will not abandon you. Even now.",
        speaker=Speaker.MOON_KNIGHT
    )
    tick(game, 5)
    game.draw(screen)
    save("cinematic_moon_knight_bark")
except Exception as e:
    print(f"   moon knight error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 7.  Relic reveal panel — push RelicRevealState
# ─────────────────────────────────────────────────────────────────────────────
print("\n[7] Relic reveal panel …")
try:
    from src.game.states.relic_reveal_state import RelicRevealState
    relic_data = {
        "name": "Candora's Tear",
        "subtitle": "The Angel's Light",
        "lore": "A single crystallised tear from Candora's messenger. It burns cold in your palm. Something in you remembers what warmth felt like before the pact."
    }
    reveal = RelicRevealState("candoras_tear", relic_data)
    reveal.manager = state_manager
    # Simulate manager reference so draw works
    tick_fn = getattr(reveal, 'on_enter', None)
    if tick_fn:
        tick_fn()
    for _ in range(20):
        reveal.update(DT)
    reveal.draw(screen)
    save("relic_reveal_candoras_tear_typing")

    # skip to full text
    for _ in range(120):
        reveal.update(DT)
    reveal.draw(screen)
    save("relic_reveal_candoras_tear_full")
except Exception as e:
    print(f"   relic reveal error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 8.  Boss encounter dialogue freeze — simulate BossEncounterManager state
# ─────────────────────────────────────────────────────────────────────────────
print("\n[8] Boss encounter dialogue …")
try:
    bem = game.boss_encounter_manager
    # Simulate the Fire Wizard encounter at mid corruption
    cm._value = 45.0

    class _FakeBoss:
        ai_frozen = False
        is_boss = True
        def apply_corruption_scaling(self, v): pass

    fake_boss = _FakeBoss()
    bem.begin_encounter("FireWizard", fake_boss)
    # advance through freeze phase
    bem.update(600)   # >0.5s freeze
    bem.update(100)   # enter dialogue, show first line
    tick(game, 5)
    game.draw(screen)
    save("boss_encounter_fire_wizard_low_corruption")

    # high corruption variant
    cm._value = 80.0
    bem2 = game.boss_encounter_manager.__class__(
        game.event_bus,
        game.corruption_manager,
        game._storyline_cfg,
        game.cinematic_narrative_overlay,
        ["GreenMonster", "Gatekeeper", "BloodZombie", "FireWizard", "DarkRonin"]
    )
    bem2.begin_encounter("DarkRonin", fake_boss)
    bem2.update(600)
    bem2.update(100)
    tick(game, 5)
    game.draw(screen)
    save("boss_encounter_dark_ronin_high_corruption")
except Exception as e:
    print(f"   boss encounter error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 9.  60-frame live gameplay burst (≈ 1 real second at 60fps)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[9] 60-frame live gameplay burst …")
cm._value = 20.0
rm._collected = []
# Close any active overlay
try:
    game.cinematic_narrative_overlay.deactivate()
except Exception:
    pass

for i in range(60):
    game.update(DT)
    game.draw(screen)
    save(f"live_frame_{i+1:02d}")

# ─────────────────────────────────────────────────────────────────────────────
# 10. Ending state — all three endings
# ─────────────────────────────────────────────────────────────────────────────
print("\n[10] Ending states …")
try:
    from src.game.states.ending_state import EndingState, EndingType

    endings_cfg = game._storyline_cfg.get("endings", {})

    for etype, key, corruption in [
        (EndingType.DARK,      "dark",      85.0),
        (EndingType.LIGHT,     "light",     15.0),
        (EndingType.AMBIGUOUS, "ambiguous", 50.0),
    ]:
        edata = endings_cfg.get(key, {})
        estate = EndingState(etype, edata, corruption)
        estate.manager = state_manager
        try:
            on_enter = getattr(estate, 'on_enter', None)
            if on_enter:
                on_enter()
        except Exception:
            pass
        # advance through fade_in and into title phase
        for _ in range(120):
            estate.update(DT)
        estate.draw(screen)
        save(f"ending_{key}_title")

        # advance into lines phase
        for _ in range(200):
            estate.update(DT)
        estate.draw(screen)
        save(f"ending_{key}_lines")
except Exception as e:
    print(f"   ending error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n✓  Done. {n[0]} screenshots saved to ./{OUT}/")
pg.quit()
