import pygame as pg
from src.my_engine.state_machine import State
from src.my_engine.asset_manager import AssetManager
from src.game.ui.ui_button import UIButton
from src.my_engine.tts_manager import TTSManager

class StoryState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()
        self.font = AssetManager.get_font('assets/Colorfiction_HandDrawnFonts/Colorfiction - Gothic - Regular.otf', 50)
        
        # Load intro scene panel
        self.scene_image = pg.image.load('assets/scenes/intro_scene.jpg').convert()
        # Scale to fit the screen width while maintaining aspect ratio
        img_w, img_h = self.scene_image.get_size()
        scale = self.width / img_w
        new_h = int(img_h * scale)
        self.scene_image = pg.transform.smoothscale(self.scene_image, (self.width, new_h))
        self.scene_rect = self.scene_image.get_rect(center=(self.width // 2, self.height // 2))
        
        # Story Text
        self.story_paragraphs = [
            "They promised us a golden age. Instead, they gave us the Blight. "
            "In the silence of the burning embers, I realized... prayer was no longer enough.",
            "",
            "",
            "",
            "Then, the heavens seemed to open. A voice like silk whispered a solution. "
            "'A life for a life,' he said. 'A debt to be paid in the currency of darkness.'",
            "",
            "The deal was simple. One thousand Extractions of the Blight. "
            "One thousand souls harvested. Then, and only then, would my village be restored. "
            "My soul was the collateral.",
            "",
            "When I took the scythe, I didn't feel power. I felt a void. "
            "The moment I touched the steel, the weight of the world shifted. "
            "The hunter had become the harvest.",
            "",
            "The Fabricator lied. The more I culled, the more I changed. "
            "I realized I wasn't saving my soul; I was being encased in a living tomb of my own sins.",
            "",
            "One down. Nine-hundred and ninety-nine to go. "
            "But with every swing of the blade, I forget the faces of the people I'm trying to save.",
            "",
            "The thousandth soul will be my end. My only hope now lies in the Sanctuary of the All-Knowing. "
            "I must find the Truth... before the Demon finds me."
        ]
        
        # Generate Audio with deep warrior voice
        full_text = " ".join([p for p in self.story_paragraphs if p])
        self.audio_path = "assets/audio/story1.mp3"
        
        tts_manager = TTSManager()
        tts_manager.configure(voice='en-US-JacobNeura', rate='-1%', pitch='-5Hz', volume='+0%')
        tts_manager.generate_audio(full_text, self.audio_path)
        
        self.narration_channel = None
        
        # Fade & timing
        self.alpha = 0  # Image fades in
        self.fade_speed = 60  # Alpha units per second
        self.elapsed = 0.0
        
        # Continue Button
        self.continue_btn = UIButton(
            "Play",
            x=self.width - 150,
            y=self.height - 100,
            size="big",
            scale=0.8,
            on_click=self.start_game,
        )
        
    def on_enter(self):
        # Play narration
        sound = AssetManager.get_sound(self.audio_path)
        if sound:
            self.narration_channel = sound.play()
            
    def on_exit(self):
        # Stop narration
        if self.narration_channel:
            self.narration_channel.stop()
        
    def start_game(self):
        from .transformation_cutscene import TransformationCutscene
        from .game_state import GameState
        self.manager.set(TransformationCutscene(
            self.manager,
            next_state_factory=lambda: GameState(self.manager),
        ))
        
    def handle_event(self, event):
        self.continue_btn.handle_event(event)
        
    def update(self, dt):
        
        dt_sec = dt / 1000.0
        self.elapsed += dt_sec
        
        # Fade in the scene image
        if self.alpha < 255:
            self.alpha = min(255, self.alpha + self.fade_speed * dt_sec)
        
    def draw(self, surface):
        # Black background
        surface.fill((0, 0, 0))
        
        # Draw scene panel with fade-in
        if self.alpha >= 255:
            surface.blit(self.scene_image, self.scene_rect)
        else:
            temp = self.scene_image.copy()
            temp.set_alpha(int(self.alpha))
            surface.blit(temp, self.scene_rect)
        
        # Draw continue button
        self.continue_btn.draw(surface)
