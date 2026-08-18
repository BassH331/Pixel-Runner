from unittest.mock import MagicMock
import pygame as pg

pg.init()
if not pg.mixer.get_init():
    pg.mixer.init()

from v3x_zulfiqar_gideon import EventBus, DamageDealt, DamageReceived, EntityDied, AudioManager


def test_audio_manager_event_bus_registration():
    bus = EventBus()
    audio = AudioManager()
    audio.play_sound = MagicMock()

    audio.register_events(bus)

    # 1. DamageDealt -> plays collision SFX
    audio.sound_library["collision_player_skeleton"] = MagicMock()
    bus.emit(DamageDealt(attacker=MagicMock(), target=MagicMock(), amount=10.0, knockback=10.0))
    audio.play_sound.assert_called_with("collision_player_skeleton")

    # 2. DamageReceived -> plays defend SFX
    audio.play_sound.reset_mock()
    audio.sound_library["collision_player_defend"] = MagicMock()
    bus.emit(DamageReceived(target=MagicMock(), attacker=MagicMock(), amount=15.0, health_remaining=80.0))
    audio.play_sound.assert_called_with("collision_player_defend")

    # 3. EntityDied -> plays soul_harvest SFX
    audio.play_sound.reset_mock()
    audio.sound_library["soul_harvest"] = MagicMock()
    bus.emit(EntityDied(entity=MagicMock(), killer=MagicMock(), position=(100, 200)))
    audio.play_sound.assert_called_with("soul_harvest")
