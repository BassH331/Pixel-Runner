import json
import os

class LevelLoader:
    def __init__(self, base_path="game_data"):
        self.base_path = base_path

    def load_level(self, level_name):
        path = os.path.join(self.base_path, level_name)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Error loading level {level_name}: {e}")
            return None
