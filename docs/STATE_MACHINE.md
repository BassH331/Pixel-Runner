# State Machine Guide

The State Machine system (`src/my_engine/state_machine.py`) manages the flow of the game, allowing you to switch between different screens (States) like the Menu, Game, and Pause screens.

## The State Class

All game screens must inherit from the `State` class.

```python
from src.my_engine.state_machine import State

class MyCustomState(State):
    def __init__(self, manager):
        super().__init__(manager)
        
    def on_enter(self):
        print("Entered State")
        
    def on_exit(self):
        print("Exited State")
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            pass
            
    def update(self, dt):
        pass
        
    def draw(self, surface):
        pass
```

## The State Manager

The `StateManager` holds a stack of states. The state at the top of the stack is the active one.

### Key Methods

- **`push(state)`**: Adds a new state to the top of the stack. The previous state is paused (its `on_exit` is called).
- **`pop()`**: Removes the current state. The previous state becomes active again (its `on_enter` is called).
- **`set(state)`**: Clears the entire stack and sets the new state as the only active one. Useful for switching from Menu to Game.

### Example Usage

```python
# In main.py
state_manager = StateManager()
state_manager.push(MainMenuState(state_manager))

# Inside a State (e.g., MainMenuState)
def start_game(self):
    # Switch to GameState
    self.manager.set(GameState(self.manager))
    
def open_settings(self):
    # Overlay SettingsState on top
    self.manager.push(SettingsState(self.manager))
```
