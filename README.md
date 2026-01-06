# Guardian Runner ⚔️🔥

Guardian Runner is a 2D action runner built with Pygame. Guide the last Star-Fire Guardian through story, menu, and gameplay states, unleash two melee attacks with frame-accurate hit windows, and enjoy the fully voiced/sampled audio set that now covers jumps, footsteps, attack cues, and enemy events.

## ✨ Current Feature Set

- **State-driven flow** – Splash ➜ Story slideshow ➜ Animated Menu ➜ In-game StateMachine with pause/resume hooks.
- **Responsive presentation** – Resizable window that rescales parallax backgrounds, UI, and buttons to the active monitor.
- **Frame-precise combat** – Two attack types (Thrust/Smash) with per-frame hitboxes, hit-stop, and collision gating to prevent duplicate hits.
- **Audio pass** – Unique sounds for jump grunt, landing, smash phases, thrusts, skeleton spawn/death, player hurt/hit, footsteps, and ambient forest loop. Attack Two now layers both animation cues and impact slices even without collisions.
- **Input options** – Keyboard by default plus detected gamepads (tested with DualShock/Sony Wireless Controller) for movement, combat, and jump actions.
- **Utilities** – Player reset flow, skeleton spawn manager, adaptive bat spawns, and debug toggles.

## 🧰 Requirements

- Python 3.10+ (project currently runs on Python 3.12.3)
- Pygame 2.6+
- Optional: A connected gamepad/joystick for analog control

## 🚀 Setup & Launch

1. **Clone the repo**
   ```bash
   git clone <repo-url>
   cd Pixel-Runner
   ```

2. **(Optional) Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # Linux/macOS
   # .venv\Scripts\activate      # Windows PowerShell
   ```

3. **Install dependencies**
   ```bash
   pip install pygame
   ```

4. **Start the game**
   ```bash
   python main.py
   ```

Expect the console to log state transitions (Splash ➜ MainMenu ➜ Story ➜ Game). Audio initialization and joystick detection messages also appear here.

## 🎮 Controls

| Action | Keyboard | Gamepad |
| --- | --- | --- |
| Move | ← / → arrows | Left stick (horizontal axis)
| Jump | Space | Button 0 (Cross / A) or pushing the left stick vertically
| Attack One – Thrust | Q | Button 2 (Square / X)
| Attack Two – Smash | E | Button 1 (Circle / B)
| Advance Story / Confirm Menu | Space | Button 0
| Toggle Debug Info (GameState) | D | —
| Story Skip | Esc | Start / equivalent (mapped by OS)

Controls are read every frame in `Player.player_input()`, so holding inputs is supported. Story slides advance on Space, while menu buttons also react to mouse hover/click.

## 🔊 Audio Reference

Key sound hooks (see `main.py` for exact asset paths):

- `background_music` → `assets/audio/mixkit-fright-night-871.mp3`
- `game_loop` → `assets/audio/game_loop.mp3`
- Jump grunt / landing → `angry-grunt-103204.mp3`, `land2-43790.mp3`
- Attack sounds → `smash.wav`, `sword-slash-and-swing-185432.mp3`, `sword-slice-2-393845.mp3`, plus the base impact slice `mixkit-quick-knife-slice-cutting-2152.mp3`
- Player hurt/hit → `mixkit-fighting-man-voice-of-pain-2173.wav` and `mixkit-quick-knife-slice-cutting-2152.mp3`
- Skeleton spawn/death/idle → `whoosh-cinematic-sound-effect-376889.mp3`, `skeletom scream.mp3`, `zombie-noise.mp3`
- Ambient forest loop & bats → `dark-forest.ogg`, `bats.wav`

Gameplay state switches stop currently playing tracks before starting new ambience; modify `GameState.on_enter()` if you prefer uninterrupted background music.

## 📂 Project Structure

- `main.py` – Entry point (display setup, audio loading, StateManager loop)
- `assets/` – Graphics, fonts, and all audio listed above
- `src/`
  - `game/entities/` – Player, skeletons, combat system
  - `game/states/` – Splash, Story, Menu, Game, Intro, etc.
  - `game/audio/` – Footstep controller helper
  - `my_engine/` – Lightweight engine (StateMachine, AssetManager, AudioManager)

## 🧪 Troubleshooting

- **No music after entering gameplay** – `GameState.on_enter()` intentionally fades out menu music and loops `forest`. Remove the `stop_all_sounds()` call or replay `background_music` there if desired.
- **No sound output** – Verify that `pygame.mixer` initialized successfully (console warning otherwise) and that your OS audio device is not muted. The game logs “Sound not found” if an asset fails to load.
- **Controller not detected** – Ensure your controller is connected before launching the game so `pygame.joystick` can initialize it. Otherwise keyboard controls remain available.

## 🤝 Contributing & Next Steps

Pull requests are welcome! Good first issues include new enemy archetypes, additional attack combos, improved UI scaling, or porting the new audio hooks to other states (e.g., boss fights). Please keep feature switches configurable and respect the existing footstep cadence controller.

Run fast, strike true, and keep the Star-Fire burning! 🏃‍♂️🔥