import pygame
import os

class AssetManager:
    _instance = None
    _textures = {}
    _sounds = {}
    _fonts = {}

    @classmethod
    def get_texture(cls, path):
        if path not in cls._textures:
            try:
                cls._textures[path] = pygame.image.load(path).convert_alpha()
            except Exception as e:
                print(f"Error loading texture {path}: {e}")
                # Return a placeholder surface
                surf = pygame.Surface((32, 32))
                surf.fill((255, 0, 255)) # Magenta for missing texture
                return surf
        return cls._textures[path]

    @classmethod
    def get_sound(cls, path):
        if path not in cls._sounds:
            try:
                cls._sounds[path] = pygame.mixer.Sound(path)
            except Exception as e:
                print(f"Error loading sound {path}: {e}")
                return None
        return cls._sounds[path]
    
    @classmethod
    def get_font(cls, path, size):
        key = (path, size)
        if key not in cls._fonts:
            try:
                cls._fonts[key] = pygame.font.Font(path, size)
            except Exception as e:
                print(f"Error loading font {path}: {e}")
                return pygame.font.SysFont("arial", size)
        return cls._fonts[key]

    @classmethod
    def get_animation_frames(cls, directory):
        frames = []
        if not os.path.exists(directory):
            print(f"Error: Directory not found {directory}")
            return frames
            
        try:
            # Sort files to ensure correct animation order
            files = sorted([f for f in os.listdir(directory) if f.endswith('.png') or f.endswith('.jpg')])
            for f in files:
                path = os.path.join(directory, f)
                frames.append(cls.get_texture(path))
        except Exception as e:
            print(f"Error loading animation frames from {directory}: {e}")
            
        return frames

    @classmethod
    def clear(cls):
        cls._textures.clear()
        cls._sounds.clear()
        cls._fonts.clear()
