# Pixel Runner 🎮

**Pixel Runner** is a fun 2D endless runner game made with Pygame. Run, jump over snails 🐌 and flies 🪰, and try to get the highest score! The game gets faster as you play, with cool pixel-art graphics and sounds to keep you engaged.

## Table of Contents 📑

- [What’s This Game?](#whats-this-game-🌟)
- [Cool Features](#cool-features-✨)
- [How to Install](#how-to-install-🛠️)
- [How to Play](#how-to-play-🎲)
- [Screenshots](#screenshots-📸)
- [Game Files](#game-files-🖼️)
- [Want to Help?](#want-to-help-🤝)
- [License](#license-📜)

## What’s This Game? 🌟

In Pixel Runner, you control a character running through a pixel-art world. Dodge obstacles like snails and flies to keep going and increase your score. The game gets harder the longer you survive, challenging your reflexes!

## Cool Features ✨

- **Pixel Art Style 🖼️**: Awesome retro graphics for the player, obstacles, and backgrounds.
- **Gets Harder ⚡**: The game speeds up (60 to 120 FPS) as your score grows.
- **Smooth Moves 🎞️**: Animated walking, jumping, and obstacle movements.
- **Sounds 🔊**: Hear a jump sound and enjoy background music.
- **Score Tracking 🏆**: See your score live as you play.
- **Game Over Screen 📊**: Check your final score and restart with one key.

## How to Install 🛠️

Follow these steps to play Pixel Runner on your computer:

### What You Need ✅

- **Python 3.6+**: Download from [python.org](https://www.python.org/).
- **Pygame**: A Python library for games.

### Steps 🚶

1. **Get the Game Files**:
   - Clone the repository (replace `<repository-url>` with your GitHub link, e.g., `https://github.com/your-username/pixel-runner.git`):
     ```bash
     git clone <repository-url>
     cd pixel-runner
     ```
   - Or download the ZIP from GitHub and unzip it.

2. **Install Pygame**:
   - In the VS Code terminal (`Ctrl + ~`), run:
     ```bash
     pip install pygame
     ```
   - If that doesn’t work, try:
     ```bash
     pip3 install pygame
     ```

3. **Check Game Files 📂**:
   - Make sure the `Resources` folder is in the same folder as `myStuff.py`.
   - It should have:
     - `graphics/Sky.png`
     - `graphics/ground.png`
     - `graphics/player/player_walk_1.png`, `player_walk_2.png`, `jump.png`, `player_stand.png`
     - `graphics/snail/snail1.png`, `snail2.png`
     - `graphics/fly/fly1.png`, `fly2.png`
     - `audio/jump.mp3`, `audio/music.wav`
     - `font/Pixeltype.ttf`

4. **Run the Game 🎮**:
   - In the terminal, run:
     ```bash
     python myStuff.py
     ```
   - Or:
     ```bash
     python3 myStuff.py
     ```

## How to Play 🎲

- **Start**: Press **SPACE** to begin.
- **Jump**: Press **SPACE** to jump over snails and flies.
- **Dodge**: Avoid snails (on ground) and flies (in air).
- **Score**: Survive longer to increase your score (shown on screen).
- **Game Over**: Hit an obstacle, and the game ends. Press **SPACE** to try again.
- **Quit**: Close the window to exit.

## Screenshots 📸

See Pixel Runner in action!

- **Start Screen**: Welcomes you to the game!
  ![Welcome Screen](https://github.com/user-attachments/assets/d3cbc437-c1c9-46d5-953d-4e7faf9e5121)
- **Gameplay**: Jump and dodge to score high!
  ![Gameplay 1](https://github.com/user-attachments/assets/850c621d-2fa1-4eeb-bc00-4e9f5e711c7d)
  ![Gameplay 2](https://github.com/user-attachments/assets/4c195f9f-cdd7-48fb-863f-26a31435b6e7)

## Game Files 🖼️

The `Resources` folder contains:

- **Graphics 🎨**: Pixel-art for sky, ground, player, and obstacles.
- **Audio 🎵**: `jump.mp3` (jump sound) and `music.wav` (background music).
- **Font ✍️**: `Pixeltype.ttf` for text.

## Want to Help? 🤝

Love the game? Help make it better! Suggest:

- New features (like new obstacles or skins) 💡
- Bug fixes 🐞
- More graphics or sounds 🎨

Submit ideas or code changes on GitHub. Keep code clear and commented. Join [Discussions](<repository-url>/discussions) to share ideas or high scores!

## License 📜

This game uses the MIT License. Check the [LICENSE](LICENSE) file for details.
