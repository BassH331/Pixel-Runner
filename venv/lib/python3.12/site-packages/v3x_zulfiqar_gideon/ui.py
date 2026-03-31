import pygame as pg
import math
from typing import Optional, Callable, Tuple, Dict, Any

class UITheme:
    """Central configuration for UI assets and styles."""
    _config: Dict[str, Any] = {
        "buttons": {
            "assets": {}, # Maps size names (str) to (normal_path, pressed_path)
            "font_path": None,
            "text_color": (255, 255, 255),
            "hover_color": (255, 255, 255),
            "pressed_color": (255, 255, 255),
            "shadow_color": None,
            "font_size": 36
        },
        "notifications": {
            "banner_path": None,
            "icons": {}, # Maps type names (str) to paths
            "font_path": None,
            "font_size": 52,
            "text_color": (255, 255, 255),
            "shadow_color": None
        },
        "overlays": {
            "stone_path": None,
            "parchment_path": None,
            "title_font_path": None,
            "body_font_path": None,
            "text_color": (60, 40, 20),
            "title_color": (45, 25, 10),
            "prompt_color": (100, 75, 50),
            "font_size": 38,
            "title_font_size": 48,
            "prompt_font_size": 28,
            "backdrop_alpha": 140
        }
    }

    @classmethod
    def configure_buttons(cls, assets: Dict[str, Tuple[str, str]], font_path: str, **kwargs):
        cls._config["buttons"]["assets"] = assets
        cls._config["buttons"]["font_path"] = font_path
        cls._config["buttons"].update(kwargs)

    @classmethod
    def configure_notifications(cls, banner_path: str, icons: Dict[str, str], font_path: str, **kwargs):
        cls._config["notifications"]["banner_path"] = banner_path
        cls._config["notifications"]["icons"] = icons
        cls._config["notifications"]["font_path"] = font_path
        cls._config["notifications"].update(kwargs)

    @classmethod
    def configure_overlays(cls, stone_path: str, parchment_path: str, title_font_path: str, body_font_path: str, **kwargs):
        cls._config["overlays"]["stone_path"] = stone_path
        cls._config["overlays"]["parchment_path"] = parchment_path
        cls._config["overlays"]["title_font_path"] = title_font_path
        cls._config["overlays"]["body_font_path"] = body_font_path
        cls._config["overlays"].update(kwargs)

    @classmethod
    def get(cls, component: str) -> Dict[str, Any]:
        return cls._config.get(component, {})

class Button:
    """Base clickable button class with support for hover and press states."""
    def __init__(self, x, y, image, hover_image=None, pressed_image=None, scale=1.0, size=None, on_click=None, anchor='center'):
        self.on_click = on_click
        self.anchor = anchor
        self.x = x
        self.y = y
        
        # Base images
        self.base_image = image
        self.base_hover_image = hover_image if hover_image else image
        self.base_pressed_image = pressed_image if pressed_image else self.base_hover_image
        
        # Determine initial size
        if size:
            self.width, self.height = size
        else:
            self.width = int(image.get_width() * scale)
            self.height = int(image.get_height() * scale)

        # Prepare processed images
        self._update_images()
        
        self.rect = self.image.get_rect()
        self._update_position()
        
        self.is_hovered = False
        self.is_pressed = False
        
        # Animation parameters
        self.hover_scale = 1.05
        self.animation_speed = 10
        self.current_scale = 1.0
        
    def _update_images(self):
        self.image_normal = pg.transform.smoothscale(self.base_image, (self.width, self.height))
        self.image_hover = pg.transform.smoothscale(self.base_hover_image, (self.width, self.height))
        self.image_pressed = pg.transform.smoothscale(self.base_pressed_image, (self.width, self.height))
        self.image = self.image_normal

    def _update_position(self):
        if self.anchor == 'center':
            self.rect.center = (self.x, self.y)
        else:
            setattr(self.rect, self.anchor, (self.x, self.y))

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_pressed = True
        
        if event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed and self.is_hovered:
                if self.on_click:
                    self.on_click()
            self.is_pressed = False

    def update(self, dt):
        """dt in milliseconds."""
        mouse_pos = pg.mouse.get_pos()
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        # Scale animation
        target_scale = self.hover_scale if self.is_hovered else 1.0
        dt_sec = dt / 1000.0
        self.current_scale += (target_scale - self.current_scale) * (self.animation_speed * dt_sec)
        
        if self.is_pressed and self.is_hovered:
            self.image = self.image_pressed
        elif self.is_hovered:
            self.image = self.image_hover
        else:
            self.image = self.image_normal

        # Apply scale if significant
        if abs(self.current_scale - 1.0) > 0.001:
            w = int(self.width * self.current_scale)
            h = int(self.height * self.current_scale)
            self.image = pg.transform.smoothscale(self.image, (w, h))
            old_center = self.rect.center
            self.rect = self.image.get_rect(center=old_center)
        else:
            self._update_position()

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class LabelButton(Button):
    """A button that also displays a text label with optional shadows."""
    def __init__(self, x, y, label, font, color=(255,255,255), 
                 hover_color=None, pressed_color=None, shadow_color=None, 
                 shadow_offset=(2,2), **kwargs):
        super().__init__(x, y, **kwargs)
        self.label = label
        self.font = font
        self.color = color
        self.hover_color = hover_color if hover_color else color
        self.pressed_color = pressed_color if pressed_color else color
        self.shadow_color = shadow_color
        self.shadow_offset = shadow_offset
        
        self._render_labels()

    def _render_labels(self):
        self.surf_normal = self._render_string(self.color)
        self.surf_hover = self._render_string(self.hover_color)
        self.surf_pressed = self._render_string(self.pressed_color)

    def _render_string(self, color):
        text = self.font.render(self.label, True, color)
        if self.shadow_color:
            shadow = self.font.render(self.label, True, self.shadow_color)
            surf = pg.Surface((text.get_width() + self.shadow_offset[0], 
                               text.get_height() + self.shadow_offset[1]), pg.SRCALPHA)
            surf.blit(shadow, self.shadow_offset)
            surf.blit(text, (0, 0))
            return surf
        return text

    def draw(self, surface):
        super().draw(surface)
        
        if self.is_pressed and self.is_hovered:
            text_surf = self.surf_pressed
        elif self.is_hovered:
            text_surf = self.surf_hover
        else:
            text_surf = self.surf_normal
            
        # Center text on button
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

class FloatingNotification:
    """A pop-up notification banner that fades in, holds, and fades out."""
    def __init__(self, banner_image, font, y_frac=0.2, 
                 fade_in=0.5, hold=2.0, fade_out=0.5):
        self.banner_image = banner_image
        self.font = font
        self.y_frac = y_frac
        self.fade_in = fade_in
        self.hold = hold
        self.fade_out = fade_out
        
        self.is_active = False
        self.timer = 0.0
        self.text = ""
        self.icon = None
        self.screen_width = pg.display.get_surface().get_width()
        self.screen_height = pg.display.get_surface().get_height()
        
    def show(self, text, icon=None):
        self.text = text
        self.icon = icon
        self.timer = 0.0
        self.is_active = True
        
    def update(self, dt):
        if not self.is_active:
            return
        
        self.timer += dt / 1000.0
        if self.timer >= (self.fade_in + self.hold + self.fade_out):
            self.is_active = False
            
    def draw(self, surface):
        if not self.is_active:
            return
            
        # Calculate alpha
        alpha = 1.0
        if self.timer < self.fade_in:
            alpha = self.timer / self.fade_in
        elif self.timer > (self.fade_in + self.hold):
            alpha = 1.0 - (self.timer - (self.fade_in + self.hold)) / self.fade_out
            
        alpha_int = int(255 * alpha)
        
        # Position
        cx = self.screen_width // 2
        cy = int(self.screen_height * self.y_frac)
        
        # Draw banner
        banner_rect = self.banner_image.get_rect(center=(cx, cy))
        temp_banner = self.banner_image.copy()
        temp_banner.set_alpha(alpha_int)
        surface.blit(temp_banner, banner_rect)
        
        # Draw text
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_surf.set_alpha(alpha_int)
        text_rect = text_surf.get_rect(center=(cx, cy))
        surface.blit(text_surf, text_rect)
        
        # Draw icon if present
        if self.icon:
            icon_rect = self.icon.get_rect(centerx=cx, bottom=banner_rect.top - 10)
            temp_icon = self.icon.copy()
            temp_icon.set_alpha(alpha_int)
            surface.blit(temp_icon, icon_rect)

from .asset_manager import AssetManager

class UIButton:
    """A engine-level button that gets its assets from UITheme."""
    def __init__(self, label: str, x: int, y: int, *, size: str = "big", scale: float = 1.0, 
                 on_click: Optional[Callable[[], None]] = None, font_size: Optional[int] = None):
        cfg = UITheme.get("buttons")
        if not cfg["assets"] or size not in cfg["assets"]:
            raise ValueError(f"Button assets for size '{size}' not configured in UITheme")
        
        normal_path, pressed_path = cfg["assets"][size]
        actual_font_size = font_size if font_size is not None else cfg["font_size"]
        
        self._internal = LabelButton(
            x=x, y=y, label=label,
            font=AssetManager.get_font(cfg["font_path"], actual_font_size),
            image=AssetManager.get_texture(normal_path),
            pressed_image=AssetManager.get_texture(pressed_path),
            scale=scale, on_click=on_click,
            color=cfg["text_color"], hover_color=cfg["hover_color"],
            pressed_color=cfg["pressed_color"], shadow_color=cfg["shadow_color"]
        )

    def handle_event(self, event: pg.event.Event) -> bool:
        return self._internal.handle_event(event) or False

    def update(self, dt: float):
        self._internal.update(dt)

    def draw(self, surface: pg.Surface):
        self._internal.draw(surface)

    def set_label(self, label: str):
        self._internal.label = label
        self._internal._render_labels()

    def set_position(self, x: int, y: int):
        self._internal.x = x
        self._internal.y = y
        self._internal._update_position()

class NotificationBanner(FloatingNotification):
    """A engine-level notification banner that gets its assets from UITheme."""
    def __init__(self, fade_in: float = 0.8, hold: float = 2.0, fade_out: float = 0.8, 
                 scale: float = 1.0, icon_scale: float = 1.0, banner_width_frac: float = 0.45, 
                 y_frac: float = 0.5, font_size: Optional[int] = None):
        cfg = UITheme.get("notifications")
        if not cfg["banner_path"]:
            raise ValueError("Notification banner_path not configured in UITheme")
            
        sw = pg.display.get_surface().get_width()
        raw_banner = AssetManager.get_texture(cfg["banner_path"])
        banner_w = int(sw * banner_width_frac * scale)
        banner_h = int(banner_w * (raw_banner.get_height() / raw_banner.get_width()))
        
        actual_font_size = font_size if font_size is not None else cfg["font_size"]
        
        super().__init__(
            banner_image=pg.transform.smoothscale(raw_banner, (banner_w, banner_h)),
            font=AssetManager.get_font(cfg["font_path"], int(actual_font_size * scale)),
            y_frac=y_frac, fade_in=fade_in, hold=hold, fade_out=fade_out
        )
        
        icon_size = int(banner_h * 1.1 * icon_scale)
        self._icon_imgs = {k: pg.transform.smoothscale(AssetManager.get_texture(p), (icon_size, icon_size)) 
                           for k, p in cfg["icons"].items()}

    def show(self, title: str, notification: str = "gray"):
        super().show(title, icon=self._icon_imgs.get(notification, self._icon_imgs["gray"]))

class ParchmentDisplay:
    """Full-screen overlay that shows text on a parchment board."""
    def __init__(
        self,
        parchment_scale: float = 0.55,
        stone_scale: float = 0.59,
        line_spacing: int = 8,
        prompt_text: str = "[ Press SPACE to continue ]",
        pad_x_frac: float = 0.12,
        pad_y_top_frac: float = 0.15,
        pad_y_bottom_frac: float = 0.20,
    ) -> None:
        cfg = UITheme.get("overlays")
        if not cfg["parchment_path"]:
            raise ValueError("ParchmentDisplay assets not configured in UITheme")

        self._cfg = cfg
        self._line_spacing = line_spacing
        self._prompt_text = prompt_text
        self._pad_y_bottom_frac = pad_y_bottom_frac

        display_info = pg.display.Info()
        self._screen_w = display_info.current_w
        self._screen_h = display_info.current_h

        # Load and scale elements
        raw_stone = AssetManager.get_texture(cfg["stone_path"])
        sw = int(self._screen_w * stone_scale)
        sh = int(sw * (raw_stone.get_height() / raw_stone.get_width()))
        self._stone = pg.transform.smoothscale(raw_stone, (sw, sh))
        self._stone_rect = self._stone.get_rect(center=(self._screen_w // 2, self._screen_h // 2))

        raw_parch = AssetManager.get_texture(cfg["parchment_path"])
        pw = int(self._screen_w * parchment_scale)
        ph = int(pw * (raw_parch.get_height() / raw_parch.get_width()))
        self._parchment = pg.transform.smoothscale(raw_parch, (pw, ph))
        self._parch_rect = self._parchment.get_rect(center=(self._screen_w // 2, self._screen_h // 2))

        # Pre-compute text area
        self._text_x = self._parch_rect.x + int(pw * pad_x_frac)
        self._text_y = self._parch_rect.y + int(ph * pad_y_top_frac)
        self._text_max_w = pw - int(pw * pad_x_frac * 2)
        self._text_max_h = ph - int(ph * (pad_y_top_frac + pad_y_bottom_frac))

        # Fonts
        self._font = AssetManager.get_font(cfg["body_font_path"], cfg["font_size"])
        self._title_font = AssetManager.get_font(cfg["title_font_path"], cfg["title_font_size"])
        self._prompt_font = AssetManager.get_font(cfg["body_font_path"], cfg["prompt_font_size"])

        self._backdrop = pg.Surface((self._screen_w, self._screen_h), pg.SRCALPHA)
        self._backdrop.fill((0, 0, 0, cfg["backdrop_alpha"]))

        self._active: bool = False
        self._title: str = ""
        self._wrapped_lines: Tuple[pg.Surface, ...] = ()
        self._prompt_surface: Optional[pg.Surface] = None

    @property
    def is_active(self) -> bool: return self._active

    def show(self, text: str, title: str = "Objective") -> None:
        self._active = True
        self._title = title
        self._wrapped_lines = tuple(self._wrap_text(text, self._font, self._text_max_w, self._cfg["text_color"]))
        self._prompt_surface = self._prompt_font.render(self._prompt_text, True, self._cfg["prompt_color"])

    def dismiss(self) -> None: self._active = False

    def draw(self, surface: pg.Surface) -> None:
        if not self._active: return
        surface.blit(self._backdrop, (0, 0))
        surface.blit(self._stone, self._stone_rect)
        surface.blit(self._parchment, self._parch_rect)

        title_surf = self._title_font.render(self._title, True, self._cfg["title_color"])
        title_x = self._parch_rect.centerx - title_surf.get_width() // 2
        title_y = self._text_y
        surface.blit(title_surf, (title_x, title_y))

        y = title_y + title_surf.get_height() + self._line_spacing * 2
        for line_surf in self._wrapped_lines:
            if y + line_surf.get_height() > self._text_y + self._text_max_h: break
            lx = self._text_x + (self._text_max_w - line_surf.get_width()) // 2
            surface.blit(line_surf, (lx, y))
            y += line_surf.get_height() + self._line_spacing

        if self._prompt_surface:
            px = self._parch_rect.centerx - self._prompt_surface.get_width() // 2
            py = self._parch_rect.bottom - int(self._parch_rect.height * self._pad_y_bottom_frac * 0.6)
            alpha = 160 + int(95 * abs(((pg.time.get_ticks() // 8) % 200 - 100) / 100))
            self._prompt_surface.set_alpha(alpha)
            surface.blit(self._prompt_surface, (px, py))

    @staticmethod
    def _wrap_text(text: str, font: pg.font.Font, max_width: int, color: Tuple[int, int, int]) -> list[pg.Surface]:
        words = text.split(); lines: list[pg.Surface] = []; current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if font.size(test)[0] <= max_width: current_line = test
            else:
                if current_line: lines.append(font.render(current_line, True, color))
                current_line = word
        if current_line: lines.append(font.render(current_line, True, color))
        return lines
