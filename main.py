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
    audio_manager.load_sound("background_music", "assets/audio/music.ogg")
    audio_manager.load_sound("jump", "assets/audio/jump.wav")
    audio_manager.load_sound("smash", "assets/audio/smash.wav")
    audio_manager.load_sound("thrust", "assets/audio/thrust.wav")
    audio_manager.load_sound("forest", "assets/audio/dark-forest.ogg")
    audio_manager.load_sound("bats", "assets/audio/bats.wav")
    
    state_manager = StateManager()
    state_manager.audio_manager = audio_manager # Attach audio manager
    
    # Start with Main Menu
    from src.game.states.main_menu_state import MainMenuState
    state_manager.push(MainMenuState(state_manager))
    
    # Play initial music
    audio_manager.play_sound(
        "background_music",
        priority=SoundPriority.LOW,
        volume=0.3,
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