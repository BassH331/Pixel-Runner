import pygame as pg
from sys import exit
from src.my_engine.state_machine import StateManager
from src.my_engine.asset_manager import AssetManager
from src.my_engine.audio_manager import AudioManager, SoundPriority
from src.game.states.intro_state import IntroState

# --- GLOBAL CONSTANTS ---
BASE_WIDTH, BASE_HEIGHT = 1280, 720

def init_joystick():
    pg.joystick.init()
    if pg.joystick.get_count() > 0:
        joystick = pg.joystick.Joystick(0)
        joystick.init()
        print(f"Joystick detected: {joystick.get_name()}")
        return joystick
    else:
        print("No joystick detected")
        return None

def setup_display():
    info = pg.display.Info()
    display_width, display_height = info.current_w, info.current_h
    
    width_scale = display_width / BASE_WIDTH
    height_scale = display_height / BASE_HEIGHT
    scale_factor = min(width_scale, height_scale) * 0.999
    width = int(BASE_WIDTH * scale_factor)
    height = int(BASE_HEIGHT * scale_factor)
    
    screen = pg.display.set_mode((width, height), pg.RESIZABLE)
    pg.display.set_caption("Runner: Guardian of the Star-Fire")
    return screen, width, height

def main():
    # Initialize Pygame and display
    pg.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    pg.init()
    pg.mixer.set_num_channels(32)
    joystick = init_joystick()
    screen, width, height = setup_display()
    clock = pg.time.Clock()
    
    # Initialize Managers
    audio_manager = AudioManager()
    # Load sounds
    audio_manager.load_sound(
        "background_music",
        "assets/audio/game_loop.mp3",
    )
    audio_manager.load_sound(
        "jump_grunt",
        "assets/audio/angry-grunt-103204.mp3",
    )
    audio_manager.load_sound(
        "jump",
        "assets/audio/land2-43790.mp3",
    )
    audio_manager.load_sound("smash", "assets/audio/smash.wav")
    audio_manager.load_sound(
        "smash_phase_1",
        "assets/audio/smash.wav",
    )
    audio_manager.load_sound(
        "smash_phase_2",
        "assets/audio/sword-slash-and-swing-185432.mp3",
    )
    audio_manager.load_sound(
        "smash_phase_3",
        "assets/audio/sword-slice-2-393845.mp3",
    )
    audio_manager.load_sound(
        "attack_one",
        "assets/audio/mixkit-quick-knife-slice-cutting-2152.mp3",
    )
    audio_manager.load_sound(
        "player_hit",
        "assets/audio/mixkit-quick-knife-slice-cutting-2152.mp3",
    )
    audio_manager.load_sound("thrust", "assets/audio/thrust.wav")
    audio_manager.load_sound(
        "footstep",
        "assets/audio/st3-footstep-sfx-323056.mp3",
    )
    audio_manager.load_sound(
        "skeleton_death",
        "assets/audio/skeletom scream.mp3",
    )
    audio_manager.load_sound(
        "player_hurt",
        "assets/audio/mixkit-fighting-man-voice-of-pain-2173.wav",
    )
    audio_manager.load_sound(
        "skeleton_spawn",
        "assets/audio/whoosh-cinematic-sound-effect-376889.mp3",
    )
    audio_manager.load_sound(
        "skeleton_alive",
        "assets/audio/zombie-noise.mp3",
    )
    audio_manager.load_sound("forest", "assets/audio/dark-forest.ogg")
    audio_manager.load_sound("bats", "assets/audio/bats.wav")
    
    state_manager = StateManager()
    state_manager.audio_manager = audio_manager # Attach audio manager
    
    # Start with Main Menu
    from src.game.states.splash_state import SplashState
    state_manager.push(SplashState(state_manager))
    
    # Play initial music
    audio_manager.play_sound(
        "background_music",
        priority=SoundPriority.LOW,
        volume=0.6,
        loop=True
    )
    
    while True:
        # Event Handling
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                exit()
            
            # Pass event to current state
            state_manager.handle_event(event)
            
        # Update
        state_manager.update(clock.get_time())
        audio_manager.update()
        
        # Draw
        state_manager.draw(screen)
        pg.display.update()
        
        clock.tick(60)

if __name__ == "__main__":
    main()