# ECS & Entity Guide

The Entity Component System (`src/my_engine/ecs.py`) provides a flexible way to build game objects.

## The Entity Class

`Entity` inherits from `pygame.sprite.Sprite`. It handles:
- **Rendering**: Draws the image with support for visual offsets.
- **Components**: Manages attached components.
- **Hitboxes**: Advanced collision box manipulation.

### Creating an Entity

```python
class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, "assets/graphics/player.png")
```

### Hitbox Management

The `Entity` class separates the **Visual Image** from the **Collision Hitbox** (`self.rect`).

#### `reduce_hitbox(reduce_w, reduce_h, align='center', offset_y=0)`
Shrinks the hitbox relative to the image size.
- **align='center'**: Shrinks from all sides equally.
- **align='bottom'**: Keeps the bottom edge fixed (essential for platformers to prevent sinking into the ground).

```python
# Example: Make hitbox smaller than sprite, aligned to feet
self.reduce_hitbox(20, 10, align='bottom')
```

#### `set_hitbox_size(width, height)`
Sets the absolute size of the hitbox, keeping it centered.

#### `set_image_offset(x, y)`
Manually adjusts where the image is drawn relative to the hitbox.

## Components

Components add behavior to entities.

```python
class MovementComponent(Component):
    def update(self, dt):
        self.owner.rect.x += 1

# Usage
player = Player(100, 100)
player.add_component(MovementComponent())
```
