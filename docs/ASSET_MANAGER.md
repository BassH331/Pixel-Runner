# Asset Manager Guide

The `AssetManager` (`src/my_engine/asset_manager.py`) is a singleton utility for loading and caching game assets. It prevents loading the same file multiple times, improving performance.

## Supported Assets
- **Textures** (Images)
- **Sounds**
- **Fonts**

## Usage

You do not need to instantiate `AssetManager`. Use its static methods directly.

### Loading Textures
Returns a `pygame.Surface`.

```python
image = AssetManager.get_texture("assets/graphics/player.png")
```

### Loading Sounds
Returns a `pygame.mixer.Sound`.

```python
sound = AssetManager.get_sound("assets/audio/jump.wav")
```

### Loading Fonts
Returns a `pygame.font.Font`. You must specify the size.

```python
# Caches based on (path, size) tuple
font = AssetManager.get_font("assets/fonts/Pixeltype.ttf", 32)
```

## Error Handling
If an asset fails to load:
- **Textures**: Returns a magenta placeholder square (visual indicator of missing asset).
- **Sounds**: Returns `None`.
- **Fonts**: Returns the system default font (Arial).
