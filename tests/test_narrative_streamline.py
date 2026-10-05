import unittest
import os
import pygame as pg

from v3x_zulfiqar_gideon import EventBus, UITheme
from src.game.ui.player_ui import PlayerUI
from src.game.systems.corruption_manager import CorruptionManager
from src.game.systems.whisperer_system import WhispererSystem
from src.game.entities.generic_npc import GenericNPC


class TestNarrativeStreamline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        if not pg.get_init():
            pg.init()
        if not pg.display.get_surface():
            pg.display.set_mode((1280, 720), pg.NOFRAME)

    def test_hud_streamlined_to_four_core_bars(self):
        """Verify HUD has 4 core bars (Health, Mana, Stamina, Corruption) and no 5th soul harvest bar."""
        ui = PlayerUI()
        self.assertEqual(ui.health_bar_pos, (20, 15))
        self.assertEqual(ui.mana_bar_pos, (20, 65))
        self.assertEqual(ui.stamina_bar_pos, (20, 115))
        self.assertEqual(ui.corruption_bar_pos, (20, 165))
        # Relic icon sits cleanly below corruption
        self.assertGreaterEqual(ui.relic_icon_pos[1], ui.corruption_bar_pos[1] + 60)

        # Render on surface to verify zero draw errors
        surf = pg.Surface((1280, 720))
        ui.draw(surf)

    def test_corruption_bar_tier_rendering(self):
        """Verify corruption bar transitions properly across pure, tainted, and void states."""
        bus = EventBus()
        config = {
            "corruption_events": {"enemy_kill": 10.0}
        }
        cm = CorruptionManager(bus, config)
        ui = PlayerUI()
        ui.corruption_manager = cm

        surf = pg.Surface((1280, 720))

        # 1. Pure tier (0%)
        ui._draw_corruption_bar(surf, 0)
        self.assertEqual(cm.corruption_level, "pure")

        # 2. Tainted tier (45%)
        cm.add(45.0)
        self.assertEqual(cm.corruption_level, "tainted")
        ui._draw_corruption_bar(surf, 0)

        # 3. Void tier (95%)
        cm.add(50.0)
        self.assertEqual(cm.corruption_level, "void")
        ui._draw_corruption_bar(surf, 0)

    def test_whisperer_system_cooldown_and_priority_milestones(self):
        """Verify WhispererSystem enforces 45s ambient cooldown but forces narrative milestones."""
        bus = EventBus()
        config = {
            "whisperer_barks": {
                "andras": {
                    "on_kill": [{"text": "First kill.", "corruption_range": [0, 100]}],
                    "on_threshold_crossed": [{"text": "Seal broken.", "corruption_range": [0, 100]}],
                    "on_relic": [{"text": "Claim the relic.", "corruption_range": [0, 100]}]
                }
            }
        }
        cm = CorruptionManager(bus, {})
        cm.add(75.0)  # Andras dominant

        fired_barks = []
        class MockSideNotification:
            def show(self, text, title=None, icon=None, hold=8.0):
                fired_barks.append((title, text))

        mock_side = MockSideNotification()
        ws = WhispererSystem(bus, cm, config, side_notification=mock_side)
        self.assertEqual(ws.COOLDOWN, 45.0)

        # 1. First ambient bark fires
        ws._try_bark("on_kill", force=False)
        self.assertEqual(len(fired_barks), 1)
        self.assertEqual(fired_barks[-1][1], "First kill.")

        # 2. Second ambient bark within cooldown is blocked
        ws._try_bark("on_kill", force=False)
        self.assertEqual(len(fired_barks), 1)  # blocked by 45s cooldown

        # 3. High-impact narrative milestone forces past cooldown
        ws._try_bark("on_threshold_crossed", force=True)
        self.assertEqual(len(fired_barks), 2)
        self.assertEqual(fired_barks[-1][1], "Seal broken.")

    def test_npc_corruption_mirror_dialogue(self):
        """Verify NPCs adapt their dialogue dynamically as the player's corruption grows."""
        dialogue = {
            "default": "Stay back.",
            "corruption_variants": {
                "low": "You look pure.",
                "mid": "You are turning.",
                "high": "You are a monster."
            }
        }
        npc = GenericNPC(
            x=100,
            y=100,
            sprite_dir="assets/graphics/Wizard_NPC",
            text="Stay back.",
            dialogue=dialogue
        )

        # Low corruption (15%)
        self.assertEqual(npc.get_dialogue(corruption_level=15.0), "You look pure.")

        # Mid corruption (50%)
        self.assertEqual(npc.get_dialogue(corruption_level=50.0), "You are turning.")

        # High corruption (85%)
        self.assertEqual(npc.get_dialogue(corruption_level=85.0), "You are a monster.")


if __name__ == "__main__":
    unittest.main()
