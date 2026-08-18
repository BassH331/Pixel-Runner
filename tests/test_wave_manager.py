from src.game.systems.wave_manager import WaveManager


def test_wave_manager_initialization():
    wm = WaveManager()
    assert len(wm.spawn_zones) >= 1
    assert wm.bat_min_count == 3
    assert wm.bat_max_count == 5


def test_wave_manager_load_level_config():
    wm = WaveManager()
    level_data = {
        "spawn_rate_min": 4000,
        "spawn_rate_max": 12000,
        "bat_spawn": {"min_count": 2, "max_count": 4},
        "spawn_zones": [
            {"min_dist": 0, "max_dist": 2000, "max_skeletons": 4, "delay": 5000},
            {"min_dist": 2000, "max_dist": 99999, "max_skeletons": 8, "delay": 2000}
        ]
    }

    wm.load_level_config(level_data)
    assert wm.bat_min_delay == 4000
    assert wm.bat_max_delay == 12000
    assert wm.bat_min_count == 2
    assert wm.bat_max_count == 4
    assert len(wm.spawn_zones) == 2
    assert wm.spawn_zones[1]["max_dist"] == float("inf")


def test_wave_manager_active_zones_filtering():
    wm = WaveManager()
    wm.spawn_zones = [
        {"min_dist": 0, "max_dist": 1000, "name": "zone_1"},
        {"min_dist": 1000, "max_dist": 3000, "name": "zone_2"},
        {"min_dist": 3000, "max_dist": float("inf"), "name": "zone_3"},
    ]

    # At distance 500 -> zone_1 active
    active_500 = wm.get_active_spawn_zones(500.0)
    assert len(active_500) == 1
    assert active_500[0]["name"] == "zone_1"

    # At distance 1500 -> zone_2 active
    active_1500 = wm.get_active_spawn_zones(1500.0)
    assert len(active_1500) == 1
    assert active_1500[0]["name"] == "zone_2"
    assert wm.get_spawn_zone(1500.0)["name"] == "zone_2"
