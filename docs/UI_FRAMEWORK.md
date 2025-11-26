# UI Framework Guide

This guide explains how to use the new UI framework to add buttons and screens to your game.

## The Button Class

The `Button` class is located in `src/my_engine/ui.py`. It handles:
- **Images**: Normal and Hover states.
- **Scaling**: Smooth hover animations.
- **Events**: Click detection.

### Constructor

```python
Button(x, y, image, hover_image=None, scale=1.0, on_click=None)
```

- **x, y**: Top-left position of the button.
- **image**: The Pygame surface for the button (normal state).
- **hover_image**: (Optional) The Pygame surface for the hover state.
- **scale**: Base scale of the button (e.g., 1.0 for original size, 2.0 for double).
- **on_click**: A function to call when the button is clicked.

## How to Add Buttons to a State

### 1. Load Assets
In your state's `__init__` or a helper method like `create_buttons`, load your images using `AssetManager`.

```python
# Load images
play_img = AssetManager.get_texture("assets/graphics/ui/PlayBtn.png")
play_hover = AssetManager.get_texture("assets/graphics/ui/PlayClick.png")
```

### 2. Create Button Instance
Create the button and add it to a list (e.g., `self.buttons`).

```python
# Define a callback function
def start_game():
    print("Game Started!")

# Create button
start_btn = Button(
    x=100, 
    y=200, 
    image=play_img, 
    hover_image=play_hover, 
    scale=1.5, 
    on_click=start_game
)

self.buttons.append(start_btn)
```

### 3. Handle Events
In your state's `handle_event` method, pass the event to each button.

```python
def handle_event(self, event):
    for btn in self.buttons:
        btn.handle_event(event)
```

### 4. Update and Draw
In `update` and `draw`, call the corresponding methods on your buttons.

```python
def update(self, dt):
    for btn in self.buttons:
        btn.update(dt)

def draw(self, surface):
    for btn in self.buttons:
        btn.draw(surface)
```

## Background Alignment
To align a background image, use `pygame.transform.smoothscale` to fit the screen dimensions.

```python
# In __init__
self.bg_image = AssetManager.get_texture("path/to/bg.png")
self.bg_image = pg.transform.smoothscale(self.bg_image, (self.width, self.height))

# In draw
surface.blit(self.bg_image, (0, 0))
```
