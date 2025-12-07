import pygame as pg

class Animation:
    def __init__(self, frames, frame_duration=0.2, loop=True):
        """
        Args:
            frames (list): List of pygame.Surface images.
            frame_duration (float): Time in seconds per frame.
            loop (bool): Whether to loop the animation.
        """
        self.frames = frames
        self.frame_duration = frame_duration
        self.loop = loop
        self.current_frame_index = 0
        self.timer = 0
        self.finished = False

    def update(self, dt):
        """
        Args:
            dt (float): Time delta in seconds.
        """
        if not self.frames or self.finished:
            return

        self.timer += dt
        if self.timer >= self.frame_duration:
            self.timer = 0
            self.current_frame_index += 1
            
            if self.current_frame_index >= len(self.frames):
                if self.loop:
                    self.current_frame_index = 0
                else:
                    self.current_frame_index = len(self.frames) - 1
                    self.finished = True

    def get_frame(self):
        if not self.frames:
            return None
        return self.frames[self.current_frame_index]
    
    def reset(self):
        self.current_frame_index = 0
        self.timer = 0
        self.finished = False

class Animator:
    def __init__(self):
        self.animations = {}
        self.current_animation = None
        self.current_name = ""
        self.flip_x = False
        
    def add(self, name, animation):
        self.animations[name] = animation
        if not self.current_animation:
            self.set(name)
            
    def set(self, name):
        if name in self.animations and self.current_name != name:
            self.current_name = name
            self.current_animation = self.animations[name]
            self.current_animation.reset()
            
    def update(self, dt):
        if self.current_animation:
            self.current_animation.update(dt)
            
    def get_frame(self):
        if self.current_animation:
            frame = self.current_animation.get_frame()
            if frame and self.flip_x:
                return pg.transform.flip(frame, True, False)
            return frame
        return None
