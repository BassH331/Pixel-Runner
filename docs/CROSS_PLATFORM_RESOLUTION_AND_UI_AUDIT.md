# Cross-Platform Resolution, UI, and Ground Level Audit

## 1. Executive Summary

When running the game across different machines (e.g., Linux laptop with a 1600×900 display vs. Windows Intel vPro with a 1920×1080 display), two major inconsistencies arise:
1. **The Ground Level Mismatch:** On Linux, the player stands naturally on the dirt path. On Windows, the player floats ~190 pixels in mid-air inside the foliage canopy.
2. **UI Proportion and Alignment Degradation:** HUD components (health bars, stamina/mana gauges, soul counters, timer/distance indicators) appear shrunken, cramped in the top-left, or detached from screen boundaries.

This document outlines the root causes identified through mathematical and visual forensic analysis, compares both machines, and presents the two architectural solutions to achieve 100% platform and resolution parity.

---

## 2. Root Cause Analysis

### A. Ground Floor (`ground_y`) vs. Dynamic Background Scaling

1. **Hardcoded Level Configuration:**
   In `game_data/level_1.json`, the ground floor is saved as a fixed absolute pixel offset:
   ```json
   "ground_y": 609
   ```

2. **Parallax Layer Scaling (`EnvironmentManager`):**
   In `src/game/systems/environment_manager.py`, parallax layers (such as `grass&road.png`, raw size `1920×1080`) scale dynamically to match the active window height:
   ```python
   target_height = max(1, int(screen_height * scale_y))
   ```
   In `grass&road.png`, the visual dirt path is located at **72% – 75%** of the asset's total vertical height.

3. **Screen Height Disparity:**
   * **Linux Machine (1600×900 monitor, window content height $\approx 823\text{ px}$):**
     $$\text{Road Y} \approx 823 \times 0.74 \approx 609\text{ px}$$
     Because `ground_y` was `609`, the player landed **directly on the dirt road**.
   * **Windows Machine (1920×1080 monitor, window content height $\approx 1078\text{ px}$):**
     $$\text{Road Y} \approx 1078 \times 0.74 \approx 798\text{ px}$$
     However, the physics engine in `src/game/states/game_state.py` still assigns:
     ```python
     player_sprite.set_ground_y(609)
     ```
     As a result, the player stands at $Y = 609$, which is **$798 - 609 = 189\text{ pixels}$ above the road**, floating in the trees.

---

### B. UI Degradation and Proportions

1. **Display Hardware Queries vs. Window Surface (`pg.display.Info()`):**
   Recent changes introduced `pg.display.Info().current_w` and `current_h` in:
   * `src/game/ui/player_ui.py`
   * `src/game/ui/tutorial_overlay.py`
   * `src/game/states/transformation_cutscene.py`

   `pg.display.Info()` queries the **hardware desktop display adapter resolution**, *not* the Pygame window or virtual rendering surface. In windowed mode or multi-monitor setups, UI components miscalculate offsets and anchor to desktop coordinates outside the game frame.

2. **Static 720p Pixel Metrics on 1080p Displays:**
   The game layout was authored for a **1280×720** reference canvas:
   * Health bar frame size and offsets: `(20, 20)`
   * Icon assets: static `36×36` pixels
   * Typography: static font point sizes (`18`, `24`, `32`)
   
   When rendered directly onto a 1080p surface without an internal scaling viewport, UI elements occupy a smaller fraction of the viewport, leading to cramped layouts, improper spacing, and text collisions.

---

## 3. Comparison Breakdown

| Feature | Reference Design (720p) | Linux Machine (900p / ~823p inner) | Windows Machine (1080p / ~1078p inner) |
| :--- | :--- | :--- | :--- |
| **Window Inner Height** | $720\text{ px}$ | $\approx 823\text{ px}$ | $\approx 1078\text{ px}$ |
| **Visual Road Y (0.74×)** | $\approx 533\text{ px}$ | $\approx 609\text{ px}$ | $\approx 798\text{ px}$ |
| **Configured `ground_y`** | $609\text{ px}$ | $609\text{ px}$ | $609\text{ px}$ |
| **Player Visual Position** | Below road (submerged) | **Aligned on road** | **Floating $+189\text{ px}$ in air** |
| **UI Proportions** | Standard | Slightly scaled | Tiny / misaligned |

---

## 4. Architectural Solutions

### Approach A: Virtual Viewport / Canvas (Recommended for Pixel Art)
Implement a fixed **1280×720** virtual surface inside `v3x_zulfiqar_gideon/core.py`.

1. **Mechanism:**
   * All game subsystems (physics, combat, `ground_y`, UI, particles, cutscenes) render to a sovereign `1280×720` surface (`virtual_surface`).
   * The core engine scales `virtual_surface` to the physical window using aspect-ratio preservation (letterbox/pillarbox).
   * Mouse events are transformed from physical window coordinates to virtual canvas coordinates.
2. **Advantages:**
   * **100% Cross-Platform Parity:** Pixel-for-pixel identical behavior on Linux, Windows, macOS, and Steam Deck.
   * **No Asset or Config Rework:** Level JSONs, `level_editor.py`, and `wave_editor.py` remain fully aligned without editing coordinates.
   * Eliminates floating characters, stretched hitboxes, and misaligned fonts permanently.

---

### Approach B: Resolution-Normalized Dynamic Coordinates
If dynamic multi-resolution without letterboxing is preferred:

1. **Normalized Ground Y:**
   Instead of storing absolute pixels in level JSONs, store a normalized ratio:
   $$\text{ground\_ratio} = \frac{609}{823} \approx 0.74$$
   Compute runtime ground floor dynamically:
   $$\text{ground\_y} = \text{int}(\text{screen\_height} \times \text{ground\_ratio})$$
2. **UI Scaling Factor:**
   Scale all UI coordinates, icon sizes, and fonts using:
   $$\text{scale\_factor} = \frac{\text{screen\_height}}{720.0}$$
3. **Audit Surface Calls:**
   Remove all `pg.display.Info()` hardware queries in UI modules and restore surface-relative metrics:
   ```python
   surf = pg.display.get_surface()
   surf_w = surf.get_width() if surf else 1280
   ```

---

## 5. Implementation Checklist

- [ ] Select preferred architecture (Approach A vs. Approach B).
- [ ] If **Approach A**:
  - [ ] Update `v3x_zulfiqar_gideon/core.py` to maintain a canonical `1280×720` virtual surface.
  - [ ] Route mouse inputs through coordinate normalization.
  - [ ] Scale virtual canvas to window with letterboxing/pillarboxing.
  - [ ] Revert `pg.display.Info()` in `player_ui.py`, `tutorial_overlay.py`, and `transformation_cutscene.py`.
- [ ] If **Approach B**:
  - [ ] Add `ground_ratio` or normalized floor resolution in `EnvironmentManager`.
  - [ ] Implement responsive UI scaling helper in `src/game/ui/player_ui.py`.
  - [ ] Synchronize `level_editor.py` canvas bounds with the target aspect ratio.
