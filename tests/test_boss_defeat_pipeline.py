import unittest
from unittest.mock import MagicMock, patch
import os
import pygame as pg

from v3x_zulfiqar_gideon import EventBus, GameEvent, StateManager, AudioManager, UITheme
from v3x_zulfiqar_gideon.event_bus import EntityDied
from src.game.systems.custom_events import RelicDropped
from src.game.states.game_state import GameState


class TestBossDefeatPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        if not pg.get_init():
            pg.init()
        if not pg.display.get_surface():
            pg.display.set_mode((1280, 720), pg.NOFRAME)

        UITheme.configure_buttons(
            assets={
                "big": ("dummy_big", "dummy_big_p"),
                "medium": ("dummy_med", "dummy_med_p"),
                "cancel": ("dummy_cancel", "dummy_cancel_p"),
                "new_start": ("dummy_new", "dummy_new_p"),
            },
            font_path="assets/font/Abaddon Bold.ttf"
        )
        UITheme.configure_notifications(
            banner_path="assets/graphics/UI/PNG/IRONY TITLE  Large.png",
            icons={"gray": "dummy_gray", "red": "dummy_red", "yellow": "dummy_yellow"},
            font_path="assets/font/Abaddon Bold.ttf"
        )
        UITheme.configure_overlays(
            stone_path="assets/graphics/UI/PNG/UI board Medium  stone.png",
            parchment_path="assets/graphics/UI/PNG/UI board Medium  parchment.png",
            title_font_path="assets/font/Abaddon Bold.ttf",
            body_font_path="assets/graphics/Darinia/Darinia.ttf",
        )

    def test_event_bus_reentrancy_no_deadlock(self):
        """Verify EventBus handles recursive/nested emit calls without deadlocking."""
        bus = EventBus()
        call_log = []

        class EventA(GameEvent):
            pass

        class EventB(GameEvent):
            pass

        def on_event_a(evt):
            call_log.append("enter_a")
            # Recursive emit from inside an active event handler
            bus.emit(EventB())
            call_log.append("exit_a")

        def on_event_b(evt):
            call_log.append("event_b")

        bus.subscribe(EventA, on_event_a)
        bus.subscribe(EventB, on_event_b)

        # This will deadlock if EventBus uses threading.Lock instead of threading.RLock
        bus.emit(EventA())

        self.assertEqual(call_log, ["enter_a", "event_b", "exit_a"])

    def test_mini_boss_defeat_pipeline(self):
        """Verify defeating a mini-boss completes relic emit, save, and update cleanly."""
        audio_mgr = AudioManager()
        sm = StateManager(audio_manager=audio_mgr)
        game_state = GameState(sm)
        sm.push(game_state)
        game_state.on_enter()

        # Create dummy mini-boss
        from src.game.entities.green_monster import GreenMonster
        boss = GreenMonster(x=500, y=500, player=game_state.player.sprite)
        boss.tier = "mini_boss"
        boss.is_boss = True
        boss.boss_title = "The Green Monster"
        game_state.obstacle_group.add(boss)

        death_event = EntityDied(
            entity=boss,
            killer=game_state.player.sprite,
            position=(500.0, 500.0),
            soul_value=50,
            is_boss=True,
            tier="mini_boss",
            spawn_zone=None
        )

        # Emitting EntityDied must not deadlock on relic drop
        game_state.event_bus.emit(death_event)

        # Check relic was queued
        self.assertTrue(len(game_state.relic_manager._pending_drops) > 0 or
                        "shattered_gauntlet" in game_state.relic_manager._collected)

        # Step 5 frames of update & draw to ensure no state machine or overlay crashes
        screen = pg.display.get_surface()
        for _ in range(5):
            sm.update(1.0 / 60.0)
            sm.draw(screen)

    def test_player_fall_death_does_not_sys_exit(self):
        """Verify falling off world grid inflicts lethal damage instead of hard sys.exit."""
        audio_mgr = AudioManager()
        sm = StateManager(audio_manager=audio_mgr)
        game_state = GameState(sm)
        sm.push(game_state)
        game_state.on_enter()

        player = game_state.player.sprite
        game_state.tutorial_overlay._active = False
        game_state.environment_manager.get_ground_y_at = lambda *a, **kw: None
        player.set_ground_y(None)
        player.rect.top = game_state.height + 300  # Below world grid

        # This should execute without calling sys.exit()
        game_state.update(1.0 / 60.0)
        self.assertTrue(player.is_dead)

    def test_relic_reveal_interactive_dismiss_gamepad_and_keyboard(self):
        """Verify relic reveal overlay dismisses via gamepad and keyboard without killing GameState lifecycle."""
        audio_mgr = AudioManager()
        sm = StateManager(audio_manager=audio_mgr)
        game_state = GameState(sm)
        sm.push(game_state)
        game_state.on_enter()

        # Collect a relic directly
        game_state.relic_manager._collect_relic("vial_of_void_blood", 12.0)
        self.assertIsNotNone(game_state.relic_reveal_overlay)
        self.assertTrue(game_state.relic_reveal_overlay.is_active)

        # GameState must still be active on top of SM stack (not destroyed or exited)
        self.assertIs(sm.stack[-1], game_state)
        self.assertIsNotNone(game_state.tracker)

        # Draw frame with active relic reveal overlay
        screen = pg.display.get_surface()
        game_state.draw(screen)

        # 1. Test gamepad button dismissal (A button / button 0)
        joy_event = pg.event.Event(pg.JOYBUTTONDOWN, button=0, instance_id=0)
        game_state.handle_event(joy_event)

        # Must be cleanly dismissed
        self.assertTrue(game_state.relic_reveal_overlay is None or not game_state.relic_reveal_overlay.is_active)

        # 2. Collect second relic and test keyboard dismissal ([SPACE])
        game_state.relic_manager._collect_relic("hollowed_ledger_page", 6.0)
        self.assertIsNotNone(game_state.relic_reveal_overlay)
        self.assertTrue(game_state.relic_reveal_overlay.is_active)

        key_event = pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE, mod=0)
        game_state.handle_event(key_event)

        # Must be cleanly dismissed
        self.assertTrue(game_state.relic_reveal_overlay is None or not game_state.relic_reveal_overlay.is_active)

        # Further game_state updates must proceed normally
        game_state.update(1.0 / 60.0)
        game_state.draw(screen)


if __name__ == "__main__":
    unittest.main()
