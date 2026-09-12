# Chatterbox Voiceover Integration — Task List

## Foundation
- [x] Create `tools/voice_manifest.json` — central dialogue manifest
- [x] Create `tools/setup_chatterbox.sh` — environment bootstrap script
- [x] Create `tools/chatterbox_backend.py` — generation engine
- [x] Create `assets/audio/voiceovers/.gitkeep`
- [x] Update `.gitignore`

## Game Runtime Integration
- [x] Create `src/game/audio/voiceover_manager.py` — playback manager
- [x] Modify `src/game/entities/generic_npc.py` — accept `voice_line_id`
- [x] Modify `game_data/level_1.json` — add `voice_line_id` fields
- [x] Modify `src/game/systems/cutscene_manager.py` — trigger voiceover playback
- [x] Modify `src/game/states/story_state.py` — prologue voiceover

## Voiceover Editor Plugin
- [x] Create `voiceover_editor.py` — full web-based editor with:
  - [x] Dashboard (env health, generation status overview)
  - [x] Voice profiles panel (per-NPC settings)
  - [x] Voice lines table (status, actions)
  - [x] Generation console (progress bar, ETA, logs)
  - [x] Audio preview (in-browser playback)
  - [x] API endpoints (manifest CRUD, generate, cancel, SSE progress)

## Testing & Verification
- [x] Create `tests/test_voiceover_manager.py`
- [x] Create `tests/test_voice_manifest.py`
- [x] Run full test suite
