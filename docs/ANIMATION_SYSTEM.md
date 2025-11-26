# Animation System

The Animation System provides a reusable way to handle sprite animations.

## `Animation` Class

Represents a single animation sequence.

### Usage
```python
from src.my_engine.animation import Animation

# Create an animation
frames = [img1, img2, img3]
anim = Animation(frames, frame_duration=0.1, loop=True)

# Update
anim.update(dt) # dt in seconds

# Get current frame
current_image = anim.get_frame()
```

## `Animator` Class

Manages multiple animations for an entity (state machine for animations).

### Usage
```python
from src.my_engine.animation import Animator

animator = Animator()
animator.add("idle", idle_anim)
animator.add("run", run_anim)

# Set active animation
animator.set("run")

# Update
animator.update(dt)

# Get current frame
image = animator.get_frame()
```
