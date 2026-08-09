"""
Environment Manager — Data-driven manager for game backgrounds, sky layers, ground, and audio themes.
"""

from __future__ import annotations

import os
from typing import List, Dict, Any, Optional
import pygame as pg

from v3x_zulfiqar_gideon import AssetManager, Sky


class ParallaxLayer:
    """Represents a single parallax background layer with flexible stretch, scale, and offset controls."""

    def __init__(
        self,
        texture_path: str,
        screen_width: int,
        screen_height: int,
        scroll_ratio: float = 0.2,
        repeat_x: bool = True,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        stretch_fill: bool = False,
        pos_y_offset: int = 0,
    ) -> None:
        self.texture_path = texture_path
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.scroll_ratio = scroll_ratio
        self.repeat_x = repeat_x
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.stretch_fill = stretch_fill
        self.pos_y_offset = pos_y_offset

        raw_texture = AssetManager.get_texture(texture_path)
        if stretch_fill:
            target_width = max(1, int(screen_width * scale_x))
            target_height = max(1, int(screen_height * scale_y))
        else:
            aspect_ratio = raw_texture.get_width() / float(raw_texture.get_height())
            target_height = max(1, int(screen_height * scale_y))
            target_width = max(screen_width, int(target_height * aspect_ratio * scale_x))

        self.image = pg.transform.smoothscale(raw_texture, (target_width, target_height))
        self.width = self.image.get_width()
        self.height = self.image.get_height()

        self.x1: float = 0.0
        self.x2: float = float(self.width)

    def update(self, player_speed: float, dt: float) -> None:
        speed = player_speed * self.scroll_ratio
        self.x1 -= speed * dt
        self.x2 -= speed * dt

        if self.x1 <= -self.width:
            self.x1 = self.x2 + self.width
        if self.x2 <= -self.width:
            self.x2 = self.x1 + self.width

    def draw(self, surface: pg.Surface) -> None:
        if self.stretch_fill:
            y_pos = int(self.pos_y_offset)
        else:
            y_pos = (self.screen_height - self.height) + int(self.pos_y_offset)
        surface.blit(self.image, (int(self.x1), y_pos))
        if self.repeat_x:
            surface.blit(self.image, (int(self.x2), y_pos))


class EnvironmentProp:
    """Represents a sliced prop or tileset object placed into the environment."""

    def __init__(
        self,
        texture_path: str,
        slice_rect: Optional[List[int]] = None,  # [x, y, w, h]
        pos_x: float = 0.0,
        pos_y: float = 0.0,
        scale: float = 1.0,
        layer_index: int = 4,  # Layer Depth Index
        parallax_ratio: float = 1.0,
        flip_x: bool = False,
        flip_y: bool = False,
        is_ground: bool = True,
        collision_type: str = "solid",  # "solid", "platform", "deco"
    ) -> None:
        self.texture_path = texture_path
        self.slice_rect = slice_rect
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.scale = scale
        self.layer_index = layer_index
        self.parallax_ratio = parallax_ratio
        self.flip_x = flip_x
        self.flip_y = flip_y
        self.is_ground = is_ground
        self.collision_type = collision_type

        raw_texture = AssetManager.get_texture(texture_path)
        if slice_rect and len(slice_rect) == 4:
            rx, ry, rw, rh = slice_rect
            rx = max(0, min(rx, raw_texture.get_width() - 1))
            ry = max(0, min(ry, raw_texture.get_height() - 1))
            rw = max(1, min(rw, raw_texture.get_width() - rx))
            rh = max(1, min(rh, raw_texture.get_height() - ry))
            sub_surf = raw_texture.subsurface(pg.Rect(rx, ry, rw, rh))
        else:
            sub_surf = raw_texture

        if flip_x or flip_y:
            sub_surf = pg.transform.flip(sub_surf, flip_x, flip_y)

        if scale != 1.0:
            target_w = max(1, int(sub_surf.get_width() * scale))
            target_h = max(1, int(sub_surf.get_height() * scale))
            self.image = pg.transform.smoothscale(sub_surf, (target_w, target_h))
        else:
            self.image = sub_surf

        self.width = self.image.get_width()
        self.height = self.image.get_height()

    def draw(self, surface: pg.Surface, cam_x: float = 0.0) -> None:
        draw_x = int(self.pos_x - cam_x * self.parallax_ratio)
        draw_y = int(self.pos_y)
        surface.blit(self.image, (draw_x, draw_y))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "texture_path": self.texture_path,
            "slice_rect": self.slice_rect,
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "scale": self.scale,
            "layer_index": self.layer_index,
            "parallax_ratio": self.parallax_ratio,
            "flip_x": self.flip_x,
            "flip_y": self.flip_y,
            "is_ground": self.is_ground,
            "collision_type": self.collision_type,
        }


DEFAULT_LAYER_NAMES = {
    1: "L1: Sky & Far Parallax",
    2: "L2: Mid-Background",
    3: "L3: Ground & Terrain",
    4: "L4: Props & Objects",
    5: "L5: Foreground Foliage"
}

DEFAULT_SCROLL_RATIOS = {
    1: 0.05,
    2: 0.20,
    3: 1.00,
    4: 1.00,
    5: 1.20
}


class EnvironmentManager:
    """Manages dynamic environment layers, sky, parallax backgrounds, stretch modes, and depth-ordered props."""

    def __init__(self, screen_width: int = 1280, screen_height: int = 720, env_config: Optional[Dict[str, Any]] = None) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.parallax_layers: List[ParallaxLayer] = []
        self.layer_stacks: Dict[int, Dict[str, Any]] = {}
        self.props: List[EnvironmentProp] = []
        self.sky: Optional[Sky] = None
        self.bg_music_track: str = "game_loop"
        self.ground_y: int = 686
        self.config: Dict[str, Any] = {}

        self._init_empty_layer_stacks()

        if env_config:
            self.load_config(env_config)
        else:
            self._load_defaults()

    def _init_empty_layer_stacks(self) -> None:
        """Initialize 5 default layer stacks with default ratios."""
        self.layer_stacks = {}
        for l_idx in range(1, 6):
            self.layer_stacks[l_idx] = {
                "name": DEFAULT_LAYER_NAMES[l_idx],
                "texture_path": "",
                "parallax_layer": None,
                "scroll_ratio": DEFAULT_SCROLL_RATIOS[l_idx],
                "repeat_x": True,
                "scale_x": 1.0,
                "scale_y": 1.0,
                "stretch_fill": False,
                "pos_y_offset": 0,
                "visible": True
            }

    def add_layer(self) -> int:
        """Appends a new dynamic layer stack and returns the new layer index."""
        max_idx = max(self.layer_stacks.keys(), default=0)
        new_idx = max_idx + 1
        default_ratio = 1.00  # Default to 1:1 ground scrolling ratio for ground & wall tiles
        self.layer_stacks[new_idx] = {
            "name": f"L{new_idx}: Ground & Objects L{new_idx}",
            "texture_path": "",
            "parallax_layer": None,
            "scroll_ratio": default_ratio,
            "repeat_x": True,
            "scale_x": 1.0,
            "scale_y": 1.0,
            "stretch_fill": False,
            "pos_y_offset": 0,
            "visible": True
        }
        return new_idx

    def delete_layer(self, layer_idx: int) -> bool:
        """Deletes a layer stack and removes props on that layer if more than 1 layer exists."""
        if len(self.layer_stacks) <= 1 or layer_idx not in self.layer_stacks:
            return False
        del self.layer_stacks[layer_idx]
        self.props = [p for p in self.props if p.layer_index != layer_idx]
        return True

    def set_layer_texture(
        self,
        layer_idx: int,
        texture_path: str,
        scroll_ratio: Optional[float] = None,
        scale_x: Optional[float] = None,
        scale_y: Optional[float] = None,
        stretch_fill: Optional[bool] = None,
        pos_y_offset: Optional[int] = None,
    ) -> None:
        """Assigns or updates a parallax background texture for a specific layer index."""
        if layer_idx not in self.layer_stacks:
            self.layer_stacks[layer_idx] = {
                "name": f"L{layer_idx}: Layer {layer_idx}",
                "texture_path": "",
                "parallax_layer": None,
                "scroll_ratio": scroll_ratio if scroll_ratio is not None else 0.5,
                "repeat_x": True,
                "scale_x": 1.0,
                "scale_y": 1.0,
                "stretch_fill": False,
                "pos_y_offset": 0,
                "visible": True
            }

        stack = self.layer_stacks[layer_idx]
        stack["texture_path"] = texture_path
        if scroll_ratio is not None:
            stack["scroll_ratio"] = scroll_ratio
        if scale_x is not None:
            stack["scale_x"] = scale_x
        if scale_y is not None:
            stack["scale_y"] = scale_y
        if stretch_fill is not None:
            stack["stretch_fill"] = stretch_fill
        if pos_y_offset is not None:
            stack["pos_y_offset"] = pos_y_offset

        if texture_path and os.path.exists(texture_path):
            stack["parallax_layer"] = ParallaxLayer(
                texture_path,
                self.screen_width,
                self.screen_height,
                scroll_ratio=stack["scroll_ratio"],
                repeat_x=stack.get("repeat_x", True),
                scale_x=stack.get("scale_x", 1.0),
                scale_y=stack.get("scale_y", 1.0),
                stretch_fill=stack.get("stretch_fill", False),
                pos_y_offset=stack.get("pos_y_offset", 0)
            )
        else:
            stack["parallax_layer"] = None

    def clear_layer_texture(self, layer_idx: int) -> None:
        """Clears the background texture for a specific layer index."""
        if layer_idx in self.layer_stacks:
            self.layer_stacks[layer_idx]["texture_path"] = ""
            self.layer_stacks[layer_idx]["parallax_layer"] = None
        if layer_idx == 1:
            self.sky = None

    def toggle_sky(self, enable: Optional[bool] = None) -> None:
        """Toggles or sets the sky/moon background overlay on/off."""
        if enable is None:
            enable = (self.sky is None)
        if enable:
            self._load_default_sky()
        else:
            self.sky = None

    def _load_default_sky(self) -> None:
        sky_paths = [f"assets/graphics/Clouds 3/{i}.png" for i in range(1, 5)]
        sky_speeds = [0, 0, 20, 40]
        valid_paths = [p for p in sky_paths if os.path.exists(p)]
        if valid_paths:
            self.sky = Sky(self.screen_width, self.screen_height, layer_paths=valid_paths, speeds=sky_speeds[:len(valid_paths)])

    def _load_defaults(self) -> None:
        self._load_default_sky()
        bg_path = "assets/graphics/background images/new_bg_images/bg_image.png"
        if os.path.exists(bg_path):
            self.set_layer_texture(1, bg_path, scroll_ratio=0.10)

    def load_config(self, env_config: Dict[str, Any]) -> None:
        """Parses level JSON environment configuration dictionary."""
        self.config = env_config
        self.parallax_layers.clear()
        self.props.clear()
        self._init_empty_layer_stacks()

        self.bg_music_track = env_config.get("bg_music_track", "game_loop")
        self.ground_y = env_config.get("ground_y", 686)

        # 1. Sky Configuration
        sky_cfg = env_config.get("sky")
        if sky_cfg is not None:
            if isinstance(sky_cfg, dict) and not sky_cfg.get("enabled", True):
                self.sky = None
            else:
                layers = sky_cfg.get("layers", []) if isinstance(sky_cfg, dict) else []
                if layers:
                    valid_paths = []
                    speeds = []
                    for item in layers:
                        path = item.get("path") if isinstance(item, dict) else item
                        speed = item.get("speed", 20) if isinstance(item, dict) else 20
                        if path and os.path.exists(path):
                            valid_paths.append(path)
                            speeds.append(speed)
                    if valid_paths:
                        self.sky = Sky(self.screen_width, self.screen_height, layer_paths=valid_paths, speeds=speeds)
                    else:
                        self.sky = None
                else:
                    self.sky = None
        else:
            if not env_config:
                self._load_default_sky()
            else:
                self.sky = None

        # 2. Layer Stacks Configuration
        saved_stacks = env_config.get("layer_stacks", {})
        if saved_stacks:
            for str_k, sdata in saved_stacks.items():
                try:
                    l_idx = int(str_k)
                    if l_idx not in self.layer_stacks:
                        self.layer_stacks[l_idx] = {
                            "name": sdata.get("name", f"L{l_idx}: Layer {l_idx}"),
                            "texture_path": "",
                            "parallax_layer": None,
                            "scroll_ratio": DEFAULT_SCROLL_RATIOS.get(l_idx, 0.5),
                            "repeat_x": True,
                            "scale_x": 1.0,
                            "scale_y": 1.0,
                            "stretch_fill": False,
                            "pos_y_offset": 0,
                            "visible": True
                        }
                    
                    tpath = sdata.get("texture_path", "")
                    sratio = sdata.get("scroll_ratio", DEFAULT_SCROLL_RATIOS.get(l_idx, 0.5))
                    rx = sdata.get("repeat_x", True)
                    sx = sdata.get("scale_x", 1.0)
                    sy = sdata.get("scale_y", 1.0)
                    sf = sdata.get("stretch_fill", False)
                    pyo = sdata.get("pos_y_offset", 0)
                    vis = sdata.get("visible", True)

                    self.layer_stacks[l_idx]["scroll_ratio"] = sratio
                    self.layer_stacks[l_idx]["repeat_x"] = rx
                    self.layer_stacks[l_idx]["scale_x"] = sx
                    self.layer_stacks[l_idx]["scale_y"] = sy
                    self.layer_stacks[l_idx]["stretch_fill"] = sf
                    self.layer_stacks[l_idx]["pos_y_offset"] = pyo
                    self.layer_stacks[l_idx]["visible"] = vis
                    if tpath:
                        self.set_layer_texture(l_idx, tpath, scroll_ratio=sratio, scale_x=sx, scale_y=sy, stretch_fill=sf, pos_y_offset=pyo)
                except Exception:
                    pass
        else:
            parallax_cfg = env_config.get("parallax_layers", [])
            for idx, layer_info in enumerate(parallax_cfg):
                path = layer_info.get("path")
                if path and os.path.exists(path):
                    ratio = layer_info.get("scroll_ratio", 0.1)
                    l_target = idx + 1
                    self.set_layer_texture(l_target, path, scroll_ratio=ratio)

        # 3. Environment Props
        for pdata in env_config.get("props", []):
            try:
                self.props.append(EnvironmentProp(
                    texture_path=pdata["texture_path"],
                    slice_rect=pdata.get("slice_rect"),
                    pos_x=pdata.get("pos_x", 0.0),
                    pos_y=pdata.get("pos_y", 0.0),
                    scale=pdata.get("scale", 1.0),
                    layer_index=pdata.get("layer_index", 4),
                    parallax_ratio=pdata.get("parallax_ratio", 1.0),
                    flip_x=pdata.get("flip_x", False),
                    flip_y=pdata.get("flip_y", False),
                    is_ground=pdata.get("is_ground", True),
                    collision_type=pdata.get("collision_type", "solid"),
                ))
            except Exception:
                pass

    def get_ground_y_at(self, x: float) -> float:
        """Returns the highest solid ground surface Y coordinate at world position x, falling back to base ground_y."""
        solid_ys = []
        for prop in self.props:
            if getattr(prop, "is_ground", True) and getattr(prop, "collision_type", "solid") in ("solid", "platform"):
                px = prop.pos_x
                pw = prop.width
                if px <= x <= px + pw:
                    solid_ys.append(prop.pos_y)
        if solid_ys:
            return float(min(solid_ys))
        return float(self.ground_y)

    def update(self, dt: float, player_speed: float = 0.0) -> None:
        """Update sky and background parallax layers across all layer stacks."""
        if self.sky:
            self.sky.update(dt)
        for stack in self.layer_stacks.values():
            player_layer = stack.get("parallax_layer")
            if player_layer and stack.get("visible", True):
                player_layer.update(player_speed, dt)

    def draw(self, surface: pg.Surface, cam_x: float = 0.0, max_layer: Optional[int] = None) -> None:
        """Draw sky followed by explicit layers in strict back-to-front depth order."""
        surface.fill((20, 20, 32))

        if self.sky:
            self.sky.draw(surface)

        prop_indices = {p.layer_index for p in self.props}
        all_indices = sorted(set(self.layer_stacks.keys()) | prop_indices)
        if max_layer is not None:
            active_indices = [idx for idx in all_indices if idx <= max_layer]
        else:
            active_indices = all_indices

        for l_idx in active_indices:
            stack = self.layer_stacks.get(l_idx)
            is_visible = stack.get("visible", True) if stack else True
            if not is_visible:
                continue

            if stack:
                player_layer = stack.get("parallax_layer")
                if player_layer:
                    player_layer.draw(surface)

            for prop in self.props:
                if prop.layer_index == l_idx:
                    prop.draw(surface, cam_x=cam_x)

    def to_config_dict(self) -> Dict[str, Any]:
        """Exports current environment configuration dictionary for saving."""
        serialized_stacks = {}
        legacy_parallax = []
        for l_idx, stack in self.layer_stacks.items():
            serialized_stacks[str(l_idx)] = {
                "name": stack["name"],
                "texture_path": stack["texture_path"],
                "scroll_ratio": stack["scroll_ratio"],
                "repeat_x": stack["repeat_x"],
                "scale_x": stack.get("scale_x", 1.0),
                "scale_y": stack.get("scale_y", 1.0),
                "stretch_fill": stack.get("stretch_fill", False),
                "pos_y_offset": stack.get("pos_y_offset", 0),
                "visible": stack.get("visible", True)
            }
            if stack["texture_path"]:
                legacy_parallax.append({
                    "path": stack["texture_path"],
                    "scroll_ratio": stack["scroll_ratio"],
                    "repeat_x": stack["repeat_x"]
                })

        sky_layers = [
            {"path": f"assets/graphics/Clouds 3/{i}.png", "speed": s}
            for i, s in zip(range(1, 5), [0, 0, 20, 40])
            if os.path.exists(f"assets/graphics/Clouds 3/{i}.png")
        ] if self.sky else []

        sky_layers = [
            {"path": f"assets/graphics/Clouds 3/{i}.png", "speed": s}
            for i, s in zip(range(1, 5), [0, 0, 20, 40])
            if os.path.exists(f"assets/graphics/Clouds 3/{i}.png")
        ] if self.sky else []

        return {
            "bg_music_track": self.bg_music_track,
            "ground_y": self.ground_y,
            "sky": {"enabled": self.sky is not None, "layers": sky_layers},
            "layer_stacks": serialized_stacks,
            "parallax_layers": legacy_parallax,
            "props": [p.to_dict() for p in self.props]
        }

    @staticmethod
    def get_environment_folders() -> List[Dict[str, Any]]:
        """Discovers all valid environment asset subfolders under assets/graphics (excluding UI, icons, player, enemies)."""
        exclude_keywords = [
            "250 WARRIOR ICONS", "MAGE ICONS", "free-undead-loot", "icon", "ICONS",
            "font", "KEYS", "UI", "ui", "PS4", "PC", "Gamepad", "gdb-gamepad",
            "Player", "player", "skeleton", "Goblin", "Wizard_NPC", "Necromancer",
            "DarkFantasyEnemies", "Monsters", "audio", "Sound", "VFX", "PIPOYA",
            "Explosion", "MiniBlood", "blood", "shadow_warrior", "Moon_knight"
        ]
        folders: List[Dict[str, Any]] = []
        base_dir = "assets/graphics"
        if os.path.exists(base_dir):
            for root, _, files in os.walk(base_dir):
                if any(ex.lower() in root.lower() for ex in exclude_keywords):
                    continue
                png_files = [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg"))]
                if png_files:
                    rel_dir = os.path.relpath(root).replace("\\", "/")
                    name = os.path.basename(rel_dir) or rel_dir
                    folders.append({
                        "name": name,
                        "path": rel_dir,
                        "count": len(png_files)
                    })
        return sorted(folders, key=lambda x: str(x["name"]))

    @staticmethod
    def get_available_background_packs(search_dir: str = "assets/graphics/background images") -> List[str]:
        """Discovers all available background PNG images under background images root."""
        results: List[str] = []
        if not os.path.exists(search_dir):
            return results

        for root, _, files in os.walk(search_dir):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg")):
                    rel_path = os.path.relpath(os.path.join(root, file)).replace("\\", "/")
                    results.append(rel_path)

        return sorted(results)

    @classmethod
    def get_background_thumbnails(cls, folder_path: Optional[str] = None, thumb_w: int = 160, thumb_h: int = 90) -> List[Dict[str, Any]]:
        """Returns image thumbnails for a specific folder path or all environment background packs."""
        if folder_path and os.path.exists(folder_path) and os.path.isdir(folder_path):
            files = [os.path.join(folder_path, f).replace("\\", "/") for f in sorted(os.listdir(folder_path)) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        else:
            files = cls.get_available_background_packs()

        thumbnails: List[Dict[str, Any]] = []
        for path in files:
            try:
                tex = AssetManager.get_texture(path)
                scaled = pg.transform.smoothscale(tex, (thumb_w, thumb_h))
                name = os.path.basename(path)
                parent = os.path.basename(os.path.dirname(path))
                label = f"{parent}/{name}" if parent else name
                thumbnails.append({
                    "path": path,
                    "name": label,
                    "folder": os.path.dirname(path).replace("\\", "/"),
                    "surface": scaled
                })
            except Exception:
                pass
        return thumbnails


