# Pixel-Runner Simulation Report

**Overall Status:** FAILED ❌

## Issues Found
1. Scale mismatch: level JSON has 3.6, entity_dimensions.json has 4.11 for 'boss:wizard'

**Final Distance:** 500.0
**Simulation Duration:** 8005.0ms
**Scroll Speed:** 5 px/frame

### NPC #1: Masked Stranger (✅ PASSED)
- **Registry Key:** `generic_npc_masked_man`
- **Trigger Distance:** JSON=174.0m | Spawned at=175.0m
- **Scale:** JSON=4.5 | Registry=4.5 | Runtime=4.5
- **Proximity Radius:** JSON=160.0 | Runtime=160.0
- **Image Dimensions:** 144×144
- **Initial Screen Pos:** (1647, 654)
- **Frames Tracked:** 263
- **Total X Scrolled:** 325px
- **Physical Collision:** None (no bounding box overlap)
- **Proximity Collision:** None (no interaction radius overlap)
- **Position Samples:**
  - Frame 0: (1647, 654)
  - Frame 131: (1322, 654)
  - Frame 262: (1322, 654)

### NPC #8: Mini Boss (❌ FAILED)
- **Registry Key:** `boss:wizard`
- **Trigger Distance:** JSON=500.0m | Spawned at=500.0m
- **Scale:** JSON=3.6 | Registry=4.11 | Runtime=3.6
- **Proximity Radius:** JSON=160.0 | Runtime=160.0
- **Image Dimensions:** 539×539
- **Initial Screen Pos:** (1586, 235)
- **Frames Tracked:** 198
- **Total X Scrolled:** 591px
- **Physical Collision:** None (no bounding box overlap)
- **Proximity Collision:** None (no interaction radius overlap)
- **Position Samples:**
  - Frame 0: (1586, 235)
  - Frame 99: (1289, 412)
  - Frame 197: (995, 412)
- **⚠ Issues:**
  - Scale mismatch: level JSON has 3.6, entity_dimensions.json has 4.11 for 'boss:wizard'

### NPC #4: Wizard (⚠️ SKIPPED (not reached))
- **Registry Key:** `wizard_npc`
- **Trigger Distance:** JSON=1200.0m | Spawned at=N/Am
- **Scale:** JSON=1.6 | Registry=1.6 | Runtime=N/A
- **Proximity Radius:** JSON=180.0 | Runtime=N/A
- **Spawned:** No

### NPC #7: Moon Tower (⚠️ SKIPPED (not reached))
- **Registry Key:** `generic_npc_redmoontower`
- **Trigger Distance:** JSON=2145.0m | Spawned at=N/Am
- **Scale:** JSON=2.0 | Registry=2.0 | Runtime=N/A
- **Proximity Radius:** JSON=160.0 | Runtime=N/A
- **Spawned:** No
