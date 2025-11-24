# 🚀 PixelEngine: The Framework for Legends

**Stop writing spaghetti code. Start building worlds.**

Welcome to **PixelEngine**, the lightweight, high-octane framework designed to take your Pygame projects from "messy loop" to "masterpiece". We handle the boring stuff (asset loading, state management, entity logic) so you can focus on what matters: **THE GAME**.

---

## 🧠 The Brain: State Machine

Forget `if game_state == "menu":`. Our **Stack-Based State Machine** lets you layer your game like a delicious cake.

### How it Works
- **Push**: Add a state on top (e.g., Pause Menu). The game underneath freezes but stays in memory.
- **Pop**: Remove the top state. The game resumes exactly where you left off.
- **Set**: Wipe the slate clean and start fresh (e.g., Main Menu -> Game Level).

### Code Snippet
```python
from src.my_engine.state_machine import State

class MyCoolState(State):
    def on_enter(self):
        print("Hello World!")

    def update(self, dt):
        if player_died:
            # Switch to Game Over screen
            self.manager.set(GameOverState(self.manager))
    
    def draw(self, surface):
        surface.blit(my_image, (0, 0))
```

---

## 🎨 The Vault: Asset Manager

Loading images inside your game loop? **Illegal.** 🚫
The **AssetManager** is your lazy-loading best friend. It loads textures and sounds once, caches them, and serves them up instantly.

### Features
- **Automatic Caching**: Never load the same file twice.
- **Error Handling**: Missing file? We show a placeholder instead of crashing.
- **One-Liner Access**:

```python
from src.my_engine.asset_manager import AssetManager

# Get a texture (returns a Surface)
player_img = AssetManager.get_texture("assets/hero.png")

# Play a sound (returns a Channel)
AssetManager.get_sound("assets/boom.wav").play()
```

---

## 👻 The Soul: Entities (ECS-Lite)

Inheritance is so 2005. Composition is the future.
Our **Entity** class gives you a powerful base to build anything from a hero to a floating platform.

### Creating an Entity
```python
from src.my_engine.ecs import Entity

class Zombie(Entity):
    def __init__(self, x, y):
        # Auto-loads image and sets rect!
        super().__init__(x, y, "assets/zombie.png")
        
    def update(self, dt):
        self.rect.x -= 1 # Brains...
        super().update(dt)
```

---

## 🛠️ Quick Start Guide

1. **Initialize the Engine**:
   ```python
   from src.my_engine.state_machine import StateManager
   
   state_manager = StateManager()
   state_manager.push(IntroState(state_manager))
   ```

2. **Run the Loop**:
   ```python
   while True:
       # ... handle events ...
       state_manager.update(dt)
       state_manager.draw(screen)
   ```

3. **Profit.** 💸

---

*Built with ❤️ by the Pixel-Runner Team.*
