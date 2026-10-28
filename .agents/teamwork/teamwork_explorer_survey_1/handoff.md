# Handoff Report: Explorer 1 (Popup Systems & Runtime Triggers)

## 1. Observation

### 1.1 In-Game Pop-up Notification Triggers & Event IDs in `src/game/states/game_state.py`
Direct inspection of `src/game/states/game_state.py` reveals that `PopupSceneManager` is initialized at line 189–190:
```python
189:         from src.game.systems.popup_scene_manager import PopupSceneManager
190:         self.popup_scene_manager = PopupSceneManager.get_instance()
```
The runtime queries `self.popup_scene_manager` across 9 specific call sites:

1. **`event_prologue_awakening`** (lines 966–974, inside `on_enter`):
   ```python
   966:         prologue_popup = self.popup_scene_manager.get_popup("event_prologue_awakening") if hasattr(self, "popup_scene_manager") else None
   967:         if prologue_popup and prologue_popup.get("enabled", True):
   968:             self.side_notification.show(
   969:                 prologue_popup.get("text", "The catacombs stir. Death has not taken you, but the dark beckons. Advance through the shadows."),
   970:                 prologue_popup.get("title", "The Awakening"),
   971:                 icon=prologue_popup.get("icon", "assets/graphics/UI/PNG/Exclamation_Yellow.png"),
   972:                 hold=prologue_popup.get("hold", 6.0),
   973:                 theme=prologue_popup.get("theme", "gothic_gold"),
   974:             )
   ```
2. **`event_soul_quota_betrayal`** (lines 899–915, inside `_on_soul_quota_reached`):
   ```python
   899:         popup = self.popup_scene_manager.get_popup("event_soul_quota_betrayal") if hasattr(self, "popup_scene_manager") else None
   900:         if popup:
   901:             if popup.get("enabled", True):
   902:                 self.side_notification.show(
   903:                     popup.get("text", "Ten thousand souls bound by your hand!"),
   904:                     popup.get("title", "The Fabricator's Betrayal"),
   905:                     icon=popup.get("icon", "assets/free-undead-loot-pixel-art-icons/PNG/Transperent/Icon1.png"),
   906:                     hold=popup.get("hold", 7.5),
   907:                     theme=popup.get("theme", "blood_bone"),
   908:                 )
   ```
3. **`event_book_ponder` (Occurrence A)** (lines 919–928, inside `_show_ambient_lore`):
   ```python
   919:         popup = self.popup_scene_manager.get_popup("event_book_ponder") if hasattr(self, "popup_scene_manager") else None
   920:         if popup:
   921:             if popup.get("enabled", True) and hasattr(self, "hud_overlay") and hasattr(self.hud_overlay, "side_notification"):
   922:                 self.hud_overlay.side_notification.show(
   923:                     popup.get("text", text),
   924:                     popup.get("title", "The Grimoire Whispers"),
   925:                     icon=popup.get("icon", "assets/graphics/magic_book_single/magic_book.png"),
   926:                     hold=popup.get("hold", max(duration, 8.5)),
   927:                     theme=popup.get("theme", "grimoire_leather"),
   928:                 )
   ```
4. **`event_book_ponder` (Occurrence B)** (lines 2125–2136, inside `on_buff_applied` for `buff_data.get("book_ponder")`):
   ```python
   2125:         if buff_data.get("book_ponder"):
   2126:             # Delayed player reflection after the Andras book encounter
   2127:             bp_popup = self.popup_scene_manager.get_popup("event_book_ponder") if hasattr(self, "popup_scene_manager") else None
   2128:             if bp_popup:
   2129:                 if bp_popup.get("enabled", True):
   2130:                     self.side_notification.show(
   2131:                         bp_popup.get("text", "What does this demon want with me...?"),
   2132:                         bp_popup.get("title", "The Runner Wonders"),
   2133:                         icon=bp_popup.get("icon", "assets/graphics/UI/PNG/Exclamation_Yellow.png"),
   2134:                         hold=bp_popup.get("hold", 6.0),
   2135:                         theme=bp_popup.get("theme", "grimoire_leather"),
   2136:                     )
   ```
5. **Entity ID Lookups via `get_popup_by_entity(eid)`**:
   - Interaction Points (lines 1069–1079):
     ```python
     1069:                     eid = getattr(point, "event_id", None)
     1070:                     epop = self.popup_scene_manager.get_popup_by_entity(eid) if (hasattr(self, "popup_scene_manager") and eid is not None) else None
     ```
   - NPCs (lines 1111–1121):
     ```python
     1111:                         eid = getattr(npc, "event_id", None)
     1112:                         epop = self.popup_scene_manager.get_popup_by_entity(eid) if (hasattr(self, "popup_scene_manager") and eid is not None) else None
     ```
6. **`event_level_complete`** (lines 1573–1585, inside `update` when `self.world_distance >= self._level_end_distance`):
   ```python
   1575:             popup = self.popup_scene_manager.get_popup("event_level_complete") if hasattr(self, "popup_scene_manager") else None
   1576:             if popup:
   1577:                 if popup.get("enabled", True):
   1578:                     self.side_notification.show(
   1579:                         popup.get("text", "You have reached the end of this land."),
   1580:                         popup.get("title", "Level Complete"),
   1581:                         icon=popup.get("icon", "assets/graphics/ui/relic_icon.png"),
   1582:                         hold=popup.get("hold", 9.0),
   1583:                         theme=popup.get("theme", "gothic_gold"),
   1584:                     )
   ```
7. **`event_demon_time_unlocked`** (lines 1642–1655, inside `update` when `relic_manager.is_collected("the_eye")`):
   ```python
   1646:                         dt_popup = self.popup_scene_manager.get_popup("event_demon_time_unlocked") if hasattr(self, "popup_scene_manager") else None
   1647:                         if dt_popup:
   1648:                             if dt_popup.get("enabled", True):
   1649:                                 self.side_notification.show(
   1650:                                     dt_popup.get("text", "The watching eye awakens in your soul. Press [V] to initiate Demon Time."),
   1651:                                     dt_popup.get("title", "ANCIENT WEAPON: THE EYE OF ANDRAS"),
   1652:                                     icon=dt_popup.get("icon", "assets/graphics/ui/relic_icon.png"),
   1653:                                     hold=dt_popup.get("hold", 7.5),
   1654:                                     theme=dt_popup.get("theme", "arcane_void"),
   1655:                                 )
   ```
8. **`event_forest_inquiry_1400m`** (lines 1675–1686, inside `update` when `self.world_distance >= 1400`):
   ```python
   1675:         if not getattr(self, "_forest_inquiry_shown", False) and self.world_distance >= 1400:
   1676:             self._forest_inquiry_shown = True
   1677:             forest_popup = self.popup_scene_manager.get_popup("event_forest_inquiry_1400m") if hasattr(self, "popup_scene_manager") else None
   1678:             if forest_popup:
   1679:                 if forest_popup.get("enabled", True):
   1680:                     self.side_notification.show(
   1681:                         forest_popup.get("text", "What in God's name is this forest...?"),
   1682:                         forest_popup.get("title", "The Runner Questions"),
   1683:                         icon=forest_popup.get("icon", "assets/graphics/UI/PNG/Exclamation_Yellow.png"),
   1684:                         hold=forest_popup.get("hold", 6.0),
   1685:                         theme=forest_popup.get("theme", "clean_minimalist"),
   1686:                     )
   ```
9. **`event_first_encounter` and `event_first_kill` (via Flag or Fallback)** (lines 1830–1852):
   ```python
   1831:             p_flag = getattr(pending, "flag", None)
   1832:             flag_popup = None
   1833:             if hasattr(self, "popup_scene_manager"):
   1834:                 if p_flag:
   1835:                     flag_popup = self.popup_scene_manager.get_popup_by_flag(p_flag)
   1836:                 if not flag_popup:
   1837:                     title_lower = getattr(pending, "title", "").lower()
   1838:                     text_lower = getattr(pending, "text", "").lower()
   1839:                     if "encounter" in title_lower or "encounter" in text_lower:
   1840:                         flag_popup = self.popup_scene_manager.get_popup("event_first_encounter")
   1841:                     elif "kill" in title_lower or "kill" in text_lower or "blood" in title_lower:
   1842:                         flag_popup = self.popup_scene_manager.get_popup("event_first_kill")
   ```

---

### 1.2 Audit of `game_data/scene_popups_config.json`
Direct inspection of `game_data/scene_popups_config.json` (146 lines, 10 entries):

| Entry # | Scene ID | Trigger Type | Dist | Entity ID | Flag | Current Title | Current Text | Theme | Hold | Enabled |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `event_prologue_awakening` | distance | 0 | null | null | `"The Fabricator's Enforcer"` (MISMATCH) | `"Clanking gears of malice screech in the dark..."` (MISMATCH) | `gothic_gold` | 15.0 | true |
| 2 | `event_sealed_book_encounter` | entity | 650 (MISMATCH with level_1 1013m) | 10 | null | `"Grimoire of the Ancients"` | `"The Runes of mortal demies..."` | `grimoire_leather` | 7.0 | true |
| 3 | `event_first_kill` | flag | 850 | null | `first_kill` | `"First Kill"` | `"The first of many more..."` | `blood_bone` | 9.0 | true |
| 4 | `event_boss_blood_zombie` | entity | 2558 | 14 | null | `"The Crimson Horror"` | `"A hulking mass of gore..."` | `blood_bone` | 8.0 | true |
| 5 | `event_demon_time_unlocked` | distance | 2600 | null | null | `"Demon Time Unlocked"` | `"The veil tears! Press [Q]..."` | `arcane_void` | 7.5 | true |
| 6 | `event_moonstone_keeper` | entity | 10500 | 13 | null | `"The Moonstone Keeper"` | `"The celestial guardian watches..."` | `arcane_void` | 7.0 | true |
| 7 | `event_gatekeeper_encounter` | entity | 12500 | 1 | null | `"The Iron Gatekeeper"` | `"None pass beyond the Obsidian..."` | `gothic_gold` | 7.0 | true |
| 8 | `event_soul_quota_betrayal` | flag | 20000 | null | `soul_quota` | `"Harvester's Tithe"` | `"Ten thousand souls consumed..."` | `blood_bone` | 7.5 | true |
| 9 | `event_fabricators_enforcer` | entity | 34500 | 3 | null | `"The Fabricator's Enforcer"` | `"Clanking gears of malice..."` | `clean_minimalist` | 8.0 | true |
| 10 | `event_level_complete` | distance | 36000 | null | null | `"Extraction Achieved"` | `"The catacomb collapses..."` | `gothic_gold` | 9.0 | true |

**Observed Defects in `scene_popups_config.json`**:
1. **Title & Text of `event_prologue_awakening`**:
   - Currently: Title is `"The Fabricator's Enforcer"` and text is `"Clanking gears of malice screech in the dark. The final sentinel awakens to crush your escape."` (identical to `event_fabricators_enforcer`!).
   - In `tests/test_popup_scene_manager.py:34`: `assert prologue["title"] in ("The Awakening", "The Dark Forest")`.
   - In `game_state.py:969–970`: Default title is `"The Awakening"`, text is `"The catacombs stir. Death has not taken you, but the dark beckons. Advance through the shadows."`, icon is `"assets/graphics/UI/PNG/Exclamation_Yellow.png"`, hold is `6.0`.
2. **Missing Event Entries**:
   - `event_book_ponder` is completely missing from `scene_popups_config.json`.
   - `event_first_encounter` is completely missing from `scene_popups_config.json`.
   - `event_forest_inquiry_1400m` is completely missing from `scene_popups_config.json`.
3. **Trigger Distance Mismatch for Sealed Book (Entity 10)**:
   - In `scene_popups_config.json:22`: `distance: 650`.
   - In `game_data/level_1.json:561`: Entity 10 (`"The Sealed Book"`) is at `distance: 1013`.

---

### 1.3 Entity Coordinates & IDs in `game_data/level_1.json`
Direct inspection of `game_data/level_1.json` lines 558–677 (`world_events`):
```json
558:     "world_events": [
559:         {
560:             "id": 10,
561:             "distance": 1013,
562:             "type": "npc",
563:             "params": {
564:                 "npc_type": "generic",
565:                 "title": "The Sealed Book",
566:                 "text": "The book pulses with a dark energy. Something awakens in the spiritual realm.",
567:                 "radius": 80,
568:                 "sprite_dir": "assets/graphics/magic_book_single",
569:                 "scale": 1.12,
570:                 "is_magic_book": true,
...
589:         {
590:             "id": 14,
591:             "distance": 2558,
592:             "type": "boss",
593:             "params": {
594:                 "title": "Blood Zombie",
595:                 "scale": 2.0,
596:                 "health": 120.0,
597:                 "tier": "boss",
598:                 "sprite_dir": "assets/graphics/bloodZombie",
...
608:         {
609:             "id": 13,
610:             "distance": 10500,
611:             "type": "npc",
612:             "params": {
613:                 "npc_type": "generic",
614:                 "title": "The Moonstone Keeper",
...
636:         {
637:             "id": 1,
638:             "distance": 12500,
639:             "type": "boss",
640:             "params": {
641:                 "title": "The Gatekeeper",
...
657:         {
658:             "id": 3,
659:             "distance": 34500,
660:             "type": "boss",
661:             "params": {
662:                 "title": "The Fabricator's Enforcer",
```

- **Totems**: Full-repo search for `totem` in `game_data/` yielded 0 results. No totem entity exists in `level_1.json`.
- **Boss Sequence**: `GreenMonster`, `Gatekeeper`, `BloodZombie`, `FireWizard`, `DarkRonin`.
- **Level End Distance**: 36000m (`"level_end_distance": 36000`).

---

### 1.4 `game_data/.level_default.json` State
- Direct inspection: `{"last_level": "game_data/level_2.json"}`.
- Verification via `find_by_name`: `game_data/level_2.json` does NOT exist anywhere in the repository.
- Direct inspection of `src/game/states/game_state.py:355–364`:
  ```python
  355:         last_level_cfg = os.path.join("game_data", ".level_default.json")
  356:         if level_path == default_level and os.path.exists(last_level_cfg):
  357:             try:
  358:                 with open(last_level_cfg, "r") as f:
  359:                     cfg = json.load(f)
  360:                 cand = cfg.get("last_level", "")
  361:                 if cand and os.path.exists(cand):
  362:                     level_path = cand
  363:             except Exception:
  364:                 pass
  ```
  Because `cand` does not exist on disk, it falls back to `default_level` (`game_data/level_1.json`). In `level_editor.py:2386`, `level_editor.py` writes `.level_default.json` upon level select. Having an invalid non-existent path violates Requirement R1.

---

### 1.5 Silenced Systems Verification
Direct inspection of code shows how and where each system is disabled:
1. **`WhispererSystem`**:
   - `src/game/systems/whisperer_system.py:44`:
     ```python
     ENABLED: bool = False
     ```
   - `src/game/systems/whisperer_system.py:241–243`:
     ```python
     self._cooldown_remaining = self.COOLDOWN
     if not self.ENABLED:
         return
     ```
   - `src/game/states/game_state.py:202–204`:
     ```python
     # Whisperer System (Sub-task 3) — reactive bark dialogue wired but silenced
     # (WhispererSystem.ENABLED = False).  Re-enable in whisperer_system.py to restore.
     self.whisperer_system = WhispererSystem(...)
     ```
   - Status: Properly disabled via class flag `ENABLED = False`.

2. **Boss Combat Taunts**:
   - `src/game/states/game_state.py:1474–1476`:
     ```python
     # Boss in-combat taunts — disabled to reduce notification noise.
     # Uncomment the line below to restore periodic boss taunt pop-ups.
     # self._update_boss_combat_taunts(dt)
     ```
   - Status: Properly disabled by commenting out the timer update call in the main game loop.

3. **`ObjectiveDisplay`**:
   - `src/game/ui/objective_display.py`: Inherits from `ParchmentDisplay`.
   - `src/game/ui/hud_overlay.py:45`: `self.objective_display = ObjectiveDisplay()`.
   - Grep search confirms `objective_display.show(...)` is never called in `game_state.py`.
   - Status: Inactive / dormant during runtime gameplay.

4. **`ItemLoreSystem`**:
   - `src/game/systems/item_lore_system.py`: Manages relic memory flashbacks.
   - Grep search confirms `ItemLoreSystem.get_instance().discover_relic(...)` is never called in `game_state.py` (only called in `tests/test_item_lore_system.py`).
   - Status: Inactive / dormant during runtime gameplay.

---

### 1.6 `src/game/systems/popup_scene_manager.py` Architecture
- Singleton pattern: `get_instance(config_path="game_data/scene_popups_config.json")`, `reset_instance()`.
- Triple-indexing in `_rebuild_indices()`:
  - `_scenes_by_id[scene["id"]]` -> `scene`
  - `_scenes_by_entity[int(scene["entity_id"])]` -> `scene`
  - `_scenes_by_flag[scene["flag"]]` -> `scene`
- Hot reload: `check_reload()` checks `os.path.getmtime(self.config_path)` on every read/write call.
- Persistence: `save_config()` calls `atomic_write_json(path, payload, indent=2, backup=True)`.

---

## 2. Logic Chain

1. **Premise**: Pop-up notifications in `GameState` are driven by `PopupSceneManager.get_instance()`, querying by string scene ID (`get_popup(id)`), integer entity ID (`get_popup_by_entity(eid)`), or event flag (`get_popup_by_flag(flag)`).
2. **Observation Step 1**: In `GameState`, `event_book_ponder`, `event_first_encounter`, and `event_forest_inquiry_1400m` are directly queried via `get_popup("...")` or `get_popup_by_flag("...")`.
3. **Observation Step 2**: In `game_data/scene_popups_config.json`, none of these three scene IDs exist.
4. **Deduction 1**: When these events trigger in gameplay, `get_popup(...)` returns `None`. While `GameState` has hardcoded fallback strings in `else` branches, the data-driven configuration system is bypassed, preventing editor plugins (`popup_controller.py`) from customizing them and causing unit tests expecting valid configurations to fail.
5. **Observation Step 3**: In `game_data/scene_popups_config.json`, `event_prologue_awakening` has title `"The Fabricator's Enforcer"` and body `"Clanking gears of malice screech in the dark..."`, which is an erroneous duplicate of `event_fabricators_enforcer`.
6. **Observation Step 4**: In `tests/test_popup_scene_manager.py:34`, the test explicitly asserts `assert prologue["title"] in ("The Awakening", "The Dark Forest")`.
7. **Deduction 2**: The prologue awakening configuration in `scene_popups_config.json` is corrupted and directly fails unit test assertions. It must be updated to title `"The Awakening"` and text `"The catacombs stir. Death has not taken you, but the dark beckons. Advance through the shadows."`.
8. **Observation Step 5**: In `scene_popups_config.json`, `event_sealed_book_encounter` has `distance: 650`, but in `game_data/level_1.json`, Entity 10 is defined at `distance: 1013`.
9. **Deduction 3**: This 363-meter discrepancy causes timeline desynchronization in `popup_controller.py`'s timeline and `EntityCatalog`. Aligning `distance: 1013` resolves the mismatch.
10. **Observation Step 6**: `game_data/.level_default.json` points to `"game_data/level_2.json"`, which does not exist on disk.
11. **Deduction 4**: Updating `game_data/.level_default.json` to `"game_data/level_1.json"` ensures that default level loading resolves to a valid, existing level file.
12. **Observation Step 7**: Silenced systems (`WhispererSystem.ENABLED = False`, commented-out boss taunts, inactive `ObjectiveDisplay` and `ItemLoreSystem`) must remain disabled per R1 and acceptance criteria. No code should re-enable them.

---

## 3. Caveats

1. **Title Discrepancies between Scene Config and Level 1**:
   - In `scene_popups_config.json`, Entity 14 has title `"The Crimson Horror"` while in `level_1.json` it is titled `"Blood Zombie"`.
   - In `scene_popups_config.json`, Entity 1 has title `"The Iron Gatekeeper"` while in `level_1.json` it is titled `"The Gatekeeper"`.
   - In `scene_popups_config.json`, Entity 10 has title `"Grimoire of the Ancients"` while in `level_1.json` it is titled `"The Sealed Book"`.
   - *Assessment*: These atmospheric narrative titles are intentional thematic overlays for pop-up notifications (or can be preserved while matching distances and entity IDs).
2. **`event_book_ponder` Trigger Type**:
   - `event_book_ponder` is called in two different contexts in `game_state.py`: in `_show_ambient_lore` (ambient lore display) and in `on_buff_applied` (when `buff_data.get("book_ponder")` is True). Configuring it with `trigger_type: "flag"` or `"distance"`, `distance: 1013`, and `flag: "book_ponder"` satisfies all retrieval methods.
3. **Editor Plugin Scope**:
   - Explorer 1 is focused on Runtime triggers, `GameState`, and JSON configurations. The detailed editor plugin save/roundtrip behaviors are also being surveyed by Explorer 2.

---

## 4. Conclusion & Actionable Recommendations

To fully satisfy Requirement R1 and the Acceptance Criteria:

### Proposed Changes to `game_data/scene_popups_config.json`:
1. **Fix `event_prologue_awakening`**:
   ```json
   {
     "id": "event_prologue_awakening",
     "trigger_type": "distance",
     "distance": 0,
     "entity_id": null,
     "flag": null,
     "title": "The Awakening",
     "text": "The catacombs stir. Death has not taken you, but the dark beckons. Advance through the shadows.",
     "theme": "gothic_gold",
     "icon": "assets/graphics/UI/PNG/Exclamation_Yellow.png",
     "hold": 6.0,
     "enabled": true,
     "description": "Prologue intro at game start"
   }
   ```
2. **Align `event_sealed_book_encounter` distance to 1013**:
   Change `"distance": 650` -> `"distance": 1013`.
3. **Add `event_book_ponder`**:
   ```json
   {
     "id": "event_book_ponder",
     "trigger_type": "flag",
     "distance": 1013,
     "entity_id": 10,
     "flag": "book_ponder",
     "title": "The Runner Wonders",
     "text": "What does this demon want with me...?",
     "theme": "grimoire_leather",
     "icon": "assets/graphics/magic_book_single/magic_book.png",
     "hold": 6.0,
     "enabled": true,
     "description": "Player reflection following the Sealed Book encounter"
   }
   ```
4. **Add `event_first_encounter`**:
   ```json
   {
     "id": "event_first_encounter",
     "trigger_type": "flag",
     "distance": 1080,
     "entity_id": null,
     "flag": "first_encounter",
     "title": "The Whispering Grimoire",
     "text": "Look at the wretched thing slithering through the brush. Those who step into this forest change from their very first encounter... breathe it in, runner. The hunt has already marked you.",
     "theme": "blood_bone",
     "icon": "assets/graphics/magic_book_single/magic_book.png",
     "hold": 5.5,
     "enabled": true,
     "description": "First encounter with an enemy in Level 1"
   }
   ```
5. **Add `event_forest_inquiry_1400m`**:
   ```json
   {
     "id": "event_forest_inquiry_1400m",
     "trigger_type": "distance",
     "distance": 1400,
     "entity_id": null,
     "flag": null,
     "title": "The Runner Questions",
     "text": "What in God's name is this forest...?",
     "theme": "clean_minimalist",
     "icon": "assets/graphics/UI/PNG/Exclamation_Yellow.png",
     "hold": 6.0,
     "enabled": true,
     "description": "Distance milestone inquiry at 1,400m"
   }
   ```

### Proposed Change to `game_data/.level_default.json`:
Replace contents with:
```json
{"last_level": "game_data/level_1.json"}
```

### Invariants to Maintain:
- `WhispererSystem.ENABLED = False` in `src/game/systems/whisperer_system.py:44` must remain `False`.
- `self._update_boss_combat_taunts(dt)` in `src/game/states/game_state.py:1476` must remain commented out.
- `ObjectiveDisplay` and `ItemLoreSystem` must remain inactive in the runtime loop.

---

## 5. Verification Method

### 5.1 Programmatic Verification Script
Write and run a dedicated verification script `verify_popup_triggers.py` verifying:
```python
import json
from src.game.systems.popup_scene_manager import PopupSceneManager

PopupSceneManager.reset_instance()
mgr = PopupSceneManager.get_instance("game_data/scene_popups_config.json")

# Required event IDs from GameState
REQUIRED_EVENTS = [
    "event_prologue_awakening",
    "event_book_ponder",
    "event_first_encounter",
    "event_first_kill",
    "event_forest_inquiry_1400m",
    "event_demon_time_unlocked",
    "event_moonstone_keeper",
    "event_soul_quota_betrayal",
    "event_level_complete",
]

for eid in REQUIRED_EVENTS:
    p = mgr.get_popup(eid)
    assert p is not None, f"Missing popup for {eid}"
    assert p.get("title"), f"Empty title for {eid}"
    assert p.get("text"), f"Empty text for {eid}"

# Verify prologue awakening title
prologue = mgr.get_popup("event_prologue_awakening")
assert prologue["title"] in ("The Awakening", "The Dark Forest")
assert "Fabricator" not in prologue["title"]

# Verify entity lookups
assert mgr.get_popup_by_entity(10) is not None
assert mgr.get_popup_by_entity(14) is not None
assert mgr.get_popup_by_entity(13) is not None
assert mgr.get_popup_by_entity(1) is not None
assert mgr.get_popup_by_entity(3) is not None

# Verify entity 10 distance matches level_1.json
with open("game_data/level_1.json", "r") as f:
    l1 = json.load(f)
e10 = next(e for e in l1["world_events"] if e["id"] == 10)
assert mgr.get_popup_by_entity(10)["distance"] == e10["distance"]

# Verify .level_default.json points to existing file
with open("game_data/.level_default.json", "r") as f:
    df = json.load(f)
assert os.path.exists(df["last_level"])
```

### 5.2 Unit Test Execution
- Run `tests/test_popup_scene_manager.py`
- Run `tests/test_popup_controller.py`

### 5.3 Invalidation Conditions
- If any event ID in `REQUIRED_EVENTS` returns `None` from `mgr.get_popup(eid)`.
- If `event_prologue_awakening` contains the Fabricator text.
- If `event_sealed_book_encounter` distance does not match `level_1.json` distance (1013m).
- If `game_data/.level_default.json` points to a non-existent file.
