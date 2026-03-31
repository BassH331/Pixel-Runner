import pygame as pg
from v3x_zulfiqar_gideon import V3XCore, V3XManifest
from src.game.states.splash_state import SplashState
from src.game.states.main_menu_state import MainMenuState
from src.game.states.story_state import StoryState
from src.game.states.transformation_cutscene import TransformationCutscene
from src.game.states.game_state import GameState

# --- GLOBAL CONSTANTS ---
BASE_WIDTH, BASE_HEIGHT = 1280, 720

def init_joystick():
    pg.joystick.init()
    if pg.joystick.get_count() > 0:
        joystick = pg.joystick.Joystick(0)
        joystick.init()
        print(f"Joystick detected: {joystick.get_name()}")
        return joystick
    return None

def get_story_panels(width, height):
    """
    Define spotlight sections using percentages (0.0 to 1.0) of the screen.
    This separates the exact layout math from the state logic.
    For example, 0.33 means 33% of the screen.
    """
    panels = [
        # (X_Start, Y_Start, Width, Height)
        # ─ Top Row (Sections 1-3) ──────────────
        (0.00,  0.00,  0.42,  0.58),  # Section 1 - e.g. change 0.33 to 0.40 to make it 40% wide
        (0.42,  0.00,  0.41,  0.58),  # Section 2
        (0.66,  0.00,  0.42,  0.58),  # Section 3
        
        # ─ Bottom Row (Sections 4-7) ───────────
        (0.00,  0.50,  0.25,  0.50),  # Section 4
        (0.25,  0.50,  0.25,  0.50),  # Section 5
        (0.50,  0.50,  0.25,  0.50),  # Section 6
        (0.75,  0.50,  0.25,  0.50),  # Section 7
    ]
    # This automatically converts your percentages into precise screen pixels
    return [(int(x * width), int(y * height), int(w * width), int(h * height)) for x, y, w, h in panels]


STORY_HIGHLIGHT_TIMING = [
    (0.0,  0),   # Section 1
    (10.0, 1),   # Section 2
    (22.0, 2),   # Section 3
    (33.0, 3),   # Section 4
    (43.0, 4),   # Section 5 
    (53.0, 5),   # Section 6 
    (63.0, 6),   # Section 7
    (73.0, -1),  # End highlight
]


def main():
    # ── 1. Ignition Manifest ────────────────────────────────────────────────
    # This is the "Blueprint" of your game. 
    # Assets AND the baton-pass (Game Flow) are both defined here.
    manifest = V3XManifest(
        title="Runner: Guardian of the Star-Fire",
        base_width=BASE_WIDTH,
        base_height=BASE_HEIGHT,
        initial_state=SplashState,
        
        # Game Flow Map (State Routing)
        routes={
            SplashState: MainMenuState,
            MainMenuState: {"PLAY": lambda mgr: StoryState(
                mgr,
                voiceover_delay=1.0,
                spotlight_delay=0.0,
                menu_delay=78,
                highlight_schedule=STORY_HIGHLIGHT_TIMING,
                spotlight_sections=get_story_panels(BASE_WIDTH, BASE_HEIGHT)
            )},
            StoryState: {"NEW_GAME": TransformationCutscene},
            TransformationCutscene: GameState,
        },
        
        # Audio Jukebox
        audio={
            "background_music": "assets/audio/05  MashBeatz- LIFESTYLE INSTRUMENTAL (Visualizer).mp3",
            "game_loop": "assets/audio/game_loop.mp3",
            "jump_grunt": "assets/audio/angry-grunt-103204.mp3",
            "jump": "assets/audio/land2-43790.mp3",
            "smash": "assets/audio/smash.wav",
            "smash_phase_1": "assets/audio/smash.wav",
            "smash_phase_2": "assets/audio/sword-slash-and-swing-185432.mp3",
            "smash_phase_3": "assets/audio/sword-slice-2-393845.mp3",
            "attack_one": "assets/audio/mixkit-quick-knife-slice-cutting-2152.mp3",
            "player_hit": "assets/audio/mixkit-quick-knife-slice-cutting-2152.mp3",
            "thrust": "assets/audio/thrust.wav",
            "footstep": "assets/audio/Dirt Run 3.wav",
            "skeleton_death": "assets/audio/skeletom scream.mp3",
            "player_hurt": "assets/audio/mixkit-fighting-man-voice-of-pain-2173.wav",
            "skeleton_spawn": "assets/audio/whoosh-cinematic-sound-effect-376889.mp3",
            "skeleton_alive": "assets/audio/zombie-noise.mp3",
            "forest": "assets/audio/dark-forest.ogg",
            "bats": "assets/audio/bats.wav",
            "defend_hit": "assets/audio/Sword Blocked 2.wav",
            "defend": "assets/audio/Sword Unsheath 2.wav",
        },
        
        # UI Aesthetics
        theme={
            "buttons": {
                "assets": {
                    "big": ("assets/graphics/UI/PNG/TextBTN_Big.png", "assets/graphics/UI/PNG/TextBTN_Big_Pressed.png"),
                    "medium": ("assets/graphics/UI/PNG/TextBTN_Medium.png", "assets/graphics/UI/PNG/TextBTN_Medium_Pressed.png"),
                    "cancel": ("assets/graphics/UI/PNG/TextBTN_Cancel.png", "assets/graphics/UI/PNG/TextBTN_Cancel_Pressed.png"),
                    "new_start": ("assets/graphics/UI/PNG/TextBTN_New-Start.png", "assets/graphics/UI/PNG/TextBTN_New-Start_Pressed.png"),
                },
                "font_path": "assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf",
            },
            "notifications": {
                "banner_path": "assets/graphics/UI/PNG/IRONY TITLE  Large.png",
                "icons": {
                    "gray": "assets/graphics/UI/PNG/Exclamation_Gray.png",
                    "red": "assets/graphics/UI/PNG/Exclamation_Red.png",
                    "yellow": "assets/graphics/UI/PNG/Exclamation_Yellow.png",
                },
                "font_path": "assets/Colorfiction_HandDrawnFonts/Colorfiction - Gothic - Regular.otf",
            },
            "overlays": {
                "stone_path": "assets/graphics/UI/PNG/UI board Medium  stone.png",
                "parchment_path": "assets/graphics/UI/PNG/UI board Medium  parchment.png",
                "title_font_path": "assets/Colorfiction_HandDrawnFonts/Colorfiction - Gothic - Regular.otf",
                "body_font_path": "assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf",
                "text_color": (60, 40, 20),
            }
        }
    )

    # ── 2. Launch ───────────────────────────────────────────────────────────
    engine = V3XCore() # Auto-scaling
    init_joystick()
    engine.launch(manifest)

if __name__ == "__main__":
    main()