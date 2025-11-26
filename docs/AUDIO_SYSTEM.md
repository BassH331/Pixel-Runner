# Audio System Guide

The `AudioManager` class in `src/my_engine/audio_manager.py` provides a robust system for playing sounds and music, including features like spatial audio and channel management.

## Initialization

The `AudioManager` is typically initialized in `main.py` and passed to the `StateManager`.

```python
audio_manager = AudioManager(max_channels=32)
```

## Loading Sounds

You can load sounds individually or from a directory.

```python
# Load single sound
audio_manager.load_sound("jump", "assets/audio/jump.wav")

# Load all from directory
audio_manager.load_sounds_from_directory("assets/audio/")
```

## Playing Sounds

Use `play_sound` to play a loaded sound. It returns a `channel_id` (or `None` if failed).

### Basic Usage
```python
audio_manager.play_sound("jump")
```

### Advanced Usage (Looping, Volume, Priority)
```python
from src.my_engine.audio_manager import SoundPriority

audio_manager.play_sound(
    "background_music", 
    priority=SoundPriority.LOW, 
    volume=0.5, 
    loop=True
)
```

### Spatial Audio
The system supports simple distance-based attenuation. Pass the sound source location and the player's position.

```python
audio_manager.play_sound(
    "enemy_growl",
    location=(enemy.x, enemy.y),
    player_pos=(player.x, player.y)
)
```

## Stopping Sounds

```python
# Stop a specific channel
audio_manager.stop_sound(channel_id)

# Stop all sounds (useful for state transitions)
audio_manager.stop_all_sounds()
```
