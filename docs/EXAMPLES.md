# Engine Quick Start Examples

Here are simple, copy-pasteable examples for using each system in the engine.

## 1. UI Framework (Buttons)

**Goal:** Create a "Start Game" button.

```python
from src.my_engine.ui import Button
from src.my_engine.asset_manager import AssetManager

class MyMenuState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.buttons = []
        
        # 1. Load Images
        img = AssetManager.get_texture("assets/ui/start_btn.png")
        hover = AssetManager.get_texture("assets/ui/start_btn_hover.png")
        
        # 2. Create Button
        btn = Button(
            x=100, y=200, 
            image=img, 
            hover_image=hover, 
            on_click=self.start_game
        )
        self.buttons.append(btn)

    def start_game(self):
        print("Button Clicked!")

    def handle_event(self, event):
        # 3. Pass Events
        for btn in self.buttons:
            btn.handle_event(event)

    def update(self, dt):
        # 4. Update Animations
        for btn in self.buttons:
            btn.update(dt)

    def draw(self, surface):
        # 5. Draw
        for btn in self.buttons:
            btn.draw(surface)
```

## 2. Audio System

**Goal:** Play background music and a sound effect.

```python
# Assuming 'self.audio_manager' is available in your State

# 1. Play Music (Looping)
# Returns a channel ID (e.g., 0)
music_channel = self.audio_manager.play_sound("forest_theme", loop=True, volume=0.5)

# 2. Play Sound Effect (One-shot)
self.audio_manager.play_sound("jump_sfx")

# 3. Stop Music
self.audio_manager.stop_sound(music_channel)

# 4. Stop Everything (e.g., on Game Over)
self.audio_manager.stop_all_sounds()
```

## 3. State Machine

**Goal:** Switch from Menu to Game.

```python
# In MenuState.py
def start_game(self):
    from .game_state import GameState
    # 'set' replaces the current state (Menu) with the new one (Game)
    self.manager.set(GameState(self.manager))

# In GameState.py
def pause_game(self):
    from .pause_state import PauseState
    # 'push' adds the Pause state on TOP of the Game state
    self.manager.push(PauseState(self.manager))
```

## 4. Asset Manager

**Goal:** Load an image and a font without worrying about duplicates.

```python
from src.my_engine.asset_manager import AssetManager

# 1. Get Texture (Image)
player_image = AssetManager.get_texture("assets/graphics/player.png")

# 2. Get Font (size 32)
score_font = AssetManager.get_font("assets/fonts/main_font.ttf", 32)

# 3. Use them
surface.blit(player_image, (0, 0))
text = score_font.render("Score: 100", True, (255, 255, 255))
```

## 5. ECS (Entities)

**Goal:** Create a Player entity with a smaller hitbox.

```python
from src.my_engine.ecs import Entity

class Player(Entity):
    def __init__(self, x, y):
        # 1. Initialize with image path
        super().__init__(x, y, "assets/graphics/player.png")
        
        # 2. Refine Hitbox (Optional)
        # Shrink hitbox by 20px width and 10px height
        # Align to bottom so feet stay on ground
        self.reduce_hitbox(20, 10, align='bottom')

# Usage
player = Player(100, 300)
player.draw(screen)
```
