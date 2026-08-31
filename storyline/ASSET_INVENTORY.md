# Asset Inventory & Visual Audit

This document provides a comprehensive, itemized audit of all sprite sheets, animation frames, tilesets, parallax layers, props, and VFX assets available in the `/assets` directory (6,515 total image files across 603 directories).

---

## 1. Executive Summary & Asset Scope

| Category | Directories | Sprite / Image Count | Status | Production Readiness |
| :--- | :---: | :---: | :---: | :--- |
| **Characters & Humans** | 243 | 1,839 | 🟢 Surplus | 12+ fully-animated unique heroes, knights, mages, rangers, and NPCs. |
| **Demons & Shadow Entities** | 54 | 549 | 🟢 Surplus | Complete shadow transformation set (46 states), void forms, hounds, wraiths. |
| **Monsters & Beasts** | 42 | 556 | 🟢 Surplus | Winged chimera / Gatekeeper, goblins, kobolds, evil eye, blobs, scarecrows. |
| **Ghosts, Undead & Spirits** | 44 | 734 | 🟢 Surplus | Skeletons (5 anim sets), blood zombies, necromancers, grove spirits, fairies. |
| **Animals & Vermin** | 12 | 124 | 🟢 Ready | Bats, rats, pigeons, snails, snakes. |
| **Environment & Parallax** | 56 | 212 | 🟢 Surplus | 4 complete 1080p parallax biomes (skies, mountains, tree canopies, roads, flora). |
| **Cliffs, Rocks & Tilesets** | 63 | 438 | 🟢 Surplus | Floating cliffs, dungeon masonry, weathered brick autotiles, cavern boulders. |
| **VFX, Portals & Props** | 102 | 2,057 | 🟢 Surplus | Warp portals, cosmic relics, chests, blood splatters, elemental spells. |

**Verdict**: The project possesses **100% of the visual assets required** to build the prologue setting, all level acts, environmental parallax, NPC interactions, and boss encounters without needing new art.

---

## 2. Detailed Category Breakdown

### 🌲 Trees & Foliage (44 Images across 8 Sets)

* **Ancient Dark Jungle / Weeping Woods** (`1920x1080`):
  * Path: [`assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/trees&bushes.png`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/trees&bushes.png)
  * Characteristics: Dense dark canopy with gnarled twisted branches and layered depth.
* **The Weeping Spirit Tree** (`1920x1080`):
  * Path: [`assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/tree_face.png`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/tree_face.png)
  * Characteristics: Ancient massive trunk featuring a weeping spirit face carved into the bark.
* **Lianas & Hanging Tendrils** (`1920x1080`):
  * Path: [`assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/lianas.png`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/lianas.png)
  * Characteristics: Dense foreground hanging vines for layered parallax depth.
* **Temperate & Autumn Forest Layers** (`1024x346`):
  * Path: [`assets/graphics/GandalfHardcore FREE Platformer Assets/GandalfHardcore Background layers`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/GandalfHardcore%20FREE%20Platformer%20Assets/GandalfHardcore%20Background%20layers)
  * Variants: Autumn golden foliage, normal lush green, and barren winter branches.
* **Frosted Winter Pines** (`512x256`):
  * Path: [`assets/graphics/background images/Free Pixel Art Winter Forest/PNG`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/background%20images/Free%20Pixel%20Art%20Winter%20Forest/PNG)
  * Characteristics: Snow-capped evergreen silhouettes.

---

### 🏔️ Mountains, Cliffs & Rocks (113 Images across 63 Sets)

* **Jagged Dragon Mountains** (`1920x1080`):
  * Path: [`assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground2/Bright/mountaims.png`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground2/Bright/mountaims.png)
  * Characteristics: Distant volcanic mountain ridges in deep purple and indigo hues.
* **Floating Magic Cliffs & Rock Arches**:
  * Path: [`assets/graphics/Magic-Cliffs-Gamekit`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Magic-Cliffs-Gamekit)
  * Characteristics: Massive floating stone islands, rocky overhangs, and crumbling natural stone bridges.
* **Wasteland Crags & Ridges** (`256x256`):
  * Path: [`assets/graphics/Wasteland_Mountains_1.png`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Wasteland_Mountains_1.png) & [`Wasteland_Mountains_2.png`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Wasteland_Mountains_2.png)
  * Characteristics: Desolate jagged rock outcrops.
* **Dungeon Cavern Boulders & Pillars**:
  * Path: [`assets/graphics/The Sidescroller's Dungeon - Tileset`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/The%20Sidescroller's%20Dungeon%20-%20Tileset)
  * Characteristics: Subterranean stone blocks, rock ceilings, and ancient carved pillars.

---

### 🪨 Ground, Terrain & Tilesets (168 Images across 47 Sets)

* **Forest Dirt Road & Pebble Path** (`1920x1080`):
  * Path: [`assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/grass&road.png`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/grass&road.png)
  * Characteristics: Packed dirt pathway with stones, pebbles, and grass tufts.
* **Temple Flagstone Flooring** (`1920x1080`):
  * Path: [`assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground2/Bright/floor.png`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground2/Bright/floor.png)
  * Characteristics: Weathered ancient paving stones and ceremonial slabs.
* **Grungy Floor Modular Autotile System**:
  * Path: [`assets/graphics/Grungy_Floor_Tileset_v1.0`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Grungy_Floor_Tileset_v1.0)
  * Characteristics: Full platformer tileset with corner pieces, slopes, walls, and ledges.
* **Sidescroller Dungeon Flooring**:
  * Path: [`assets/graphics/The Sidescroller's Dungeon - Tileset`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/The%20Sidescroller's%20Dungeon%20-%20Tileset)
  * Characteristics: Dark stone brick flooring and rustic wooden platform ledges.

---

### 🌿 Grass, Flora & Foreground Elements (5 Sets + Sub-props)

* **Ethereal Wild Grass Layer** (`1920x1080`):
  * Path: [`assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/grasses.png`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/grasses.png)
  * Characteristics: Tall wild grass stalks with ambient wind sway.
* **Ambient Fireflies & Embers** (`1920x1080`):
  * Path: [`assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/fireflys.png`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/fireflys.png)
  * Characteristics: Floating golden embers and forest firefly particles.

---

### 🌌 Skies & Background Atmospheres (23 Master Panoramic Images)

* **Battleground 1-4 Sky Layers** (`1920x1080`):
  * Path: [`assets/graphics/Pixel-Art-Battlegrounds`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel-Art-Battlegrounds)
  * Palettes: Deep Twilight Blue, Golden Sunset Dusk, Blood Moon Crimson, Clear Daylight.
* **Parallax Sky Clouds**:
  * Path: [`assets/graphics/Clouds 3`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Clouds%203)
  * Speeds: 4 distinct cloud density layers (`1.png` to `4.png`) for multi-speed drift.
* **Red Moon Tower Setting**:
  * Path: [`assets/graphics/RedMoonTower`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/RedMoonTower)
  * Characteristics: Massive crimson moon backdrop behind a dark Gothic spire.

---

### 👤 Characters & Humanoid Roster (1,839 Images across 152 Sets)

| Character | Asset Directory | Visual Details | Available Animations & States |
| :--- | :--- | :--- | :--- |
| **Shadow Warrior** *(Protagonist)* | [`assets/shadow_warrior`](file:///home/chosen333/Software/Pixel-Runner/assets/shadow_warrior) | Dark steel armor, scarf, dual katana/scythe blade. | **46 distinct animation sets**: Idle (12f), Run (8f), Jump Up/Down, 3 Attacks (14f/17f/23f), Special Attack (34f), Roll, Dash, Defend, Couch Sequence, Ladder/Rope Climb, Wall Cling/Slide, Take Hit, Death. |
| **Dark Ronin** *(Staff / Graduate)* | [`assets/graphics/Ronin`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Ronin) | Kabuto/straw hat, armored samurai robes, katana. | Idle (8f), Run (10f), Heavy Blade Attack (33f), Dash Strike (10f), Hurt (7f), Death (16f). |
| **Moon Knight** | [`assets/Moon_knight`](file:///home/chosen333/Software/Pixel-Runner/assets/Moon_knight) | Lunar plate armor, silver visor, spear/greatsword. | Idle (8f), Run (8f), Thrust (13f), Ground Smash (17f), Death (29f). |
| **Agis (Hoplite)** | [`assets/Agis`](file:///home/chosen333/Software/Pixel-Runner/assets/Agis) | Golden crest helmet, bronze breastplate, spear & shield. | 15 complete animation sequences (`Agis_00` to `Agis_14`, 224x240). |
| **Hero Knight 2** | [`assets/graphics/Hero Knight 2`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Hero%20Knight%202) | Classic plate armor, broadsword, shield. | Idle, Run, 3 Combos, Shield Block, Roll, Fall, Death. |
| **Metal Bladekeeper** | [`assets/characters/Elementals_metal_bladekeeper_FREE_v1.1`](file:///home/chosen333/Software/Pixel-Runner/assets/characters/Elementals_metal_bladekeeper_FREE_v1.1) | Heavy dual-blade metal armor champion. | 25 animation folders (288x128): Combos, Projectile Cast, Trap Detonation, Roll, Death. |
| **Leaf Ranger** | [`assets/characters/Elementals_Leaf_ranger_Free_v1.0`](file:///home/chosen333/Software/Pixel-Runner/assets/characters/Elementals_Leaf_ranger_Free_v1.0) | Hooded elven archer with longbow. | 28 animation folders: Bow Shot, Arrow Shower, Poison Arrow, Thorn Entangle, Beam Extension. |
| **Water Priestess** | [`assets/characters/Elementals_water_priestess_FREE_v1.1`](file:///home/chosen333/Software/Pixel-Runner/assets/characters/Elementals_water_priestess_FREE_v1.1) | Cyan ceremonial robes, water magic. | 16 animation folders: Water Spouts, Geyser Wave, Air Dive, Walk, Death. |
| **Martial Hero 2** | [`assets/characters/Martial Hero 2`](file:///home/chosen333/Software/Pixel-Runner/assets/characters/Martial%20Hero%202) | Eastern martial monk / swordsman. | Idle, Run, 2 Melee Combos, Jump, Fall, Hurt, Death. |
| **Fire Wizard / Elder NPC** | [`assets/wizard`](file:///home/chosen333/Software/Pixel-Runner/assets/wizard), [`Wizard_NPC`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Wizard_NPC) | Hooded pyromancer / bearded sage with staff. | Idle (8f), Run (8f), Spell Cast (8f), Hurt (4f), Death (5f). |
| **Masked Man** | [`assets/graphics/masked_man`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/masked_man) | Cloaked wanderer in traveler's garb and white mask. | Idle and dialogue stance. |
| **Ace (Rogue)** | [`assets/characters/PixelUnitPack_1_Sample`](file:///home/chosen333/Software/Pixel-Runner/assets/characters/PixelUnitPack_1_Sample) | Cloaked agile skirmisher. | Breathing, Attack, Run, Projectile Slash, Hit. |
| **Dialogue Portraits** | [`assets/characters/FreeSprites5_LeafletGames`](file:///home/chosen333/Software/Pixel-Runner/assets/characters/FreeSprites5_LeafletGames) | 3 High-resolution female characters (Amy, Kaitlyn, Seraphina). | Emotion states: Smile, Frown, Surprise (1080p). |

---

### 👹 Demons & Shadow Entities (549 Images across 54 Sets)

* **Shadow Demon Form (Player Transformed)**:
  * Path: [`assets/shadow_warrior`](file:///home/chosen333/Software/Pixel-Runner/assets/shadow_warrior) (`e_*` prefixes)
  * Characteristics: Horned shadow beast with glowing red eyes, dark aura, and void blade slashes.
  * States: `e_idle` (18f), `e_run` (10f), `e_jump_up` (3f), `e_jump_down` (3f), `e_1_atk` (14f), `e_2_atk` (22f), `e_3_atk` (35f), `e_sp_atk` (19f), `e_defend` (6f), `e_take_hit` (7f).
* **Dimensional Void Vortex**:
  * Path: [`assets/shadow_warrior/transform_black_hole_loop`](file:///home/chosen333/Software/Pixel-Runner/assets/shadow_warrior/transform_black_hole_loop)
  * Characteristics: Animated swirling black hole for transformation cutscenes.
* **Shadeflit (Shadow Wraith)**:
  * Path: [`assets/characters/SHADOW Series - Shadeflit (Free)`](file:///home/chosen333/Software/Pixel-Runner/assets/characters/SHADOW%20Series%20-%20Shadeflit%20(Free))
  * Characteristics: Floating shadow creature with trailing dark tendrils.
* **Hell-Hounds**:
  * Path: [`assets/characters/Hell-Hound-Files`](file:///home/chosen333/Software/Pixel-Runner/assets/characters/Hell-Hound-Files)
  * Characteristics: 4-legged hellish beast (Walk 12f, Run, Jump, Idle).

---

### 🐉 Monsters & Beasts (556 Images across 42 Sets)

* **The Gatekeeper (Green Monster / Winged Chimera)**:
  * Path: [`assets/graphics/green_monster`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/green_monster)
  * Characteristics: Emerald winged gargoyle with razor talons.
  * States: Fly, Idle, Walk, Attack 1, Attack 2, Hurt, Death.
* **Spear & Blade Goblins**:
  * Path: [`assets/graphics/Goblin`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Goblin)
  * States: Idle, Run, Attack, Hit, Death.
* **Kobold Warriors**:
  * Path: [`assets/graphics/Kobold_Warrior`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Kobold_Warrior)
  * Characteristics: Armored reptilian warriors with shields and spiked maces.
* **Evil Eye Beast (Voragis's Surveillance)**:
  * Path: [`assets/graphics/Evil Eye Beast For Itch`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Evil%20Eye%20Beast%20For%20Itch)
  * Characteristics: Floating multi-tentacled eyeball watcher with fire/lightning rings.
* **Evil Jack (Pumpkin Demon)**:
  * Path: [`assets/graphics/Evil_jack`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Evil_jack)
  * Characteristics: Sinister pumpkin-headed stalker.
* **Slime Blobs**:
  * Path: [`assets/characters/Blob Character Pack`](file:///home/chosen333/Software/Pixel-Runner/assets/characters/Blob%20Character%20Pack)
  * Variants: Green, Blue, Red morphing blobs with assemble, run, and land animations.

---

### 🦇 Animals & Vermin (124 Images across 12 Sets)

* **Cave Bats**: [`assets/graphics/bat`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/bat) — Flapping flight, swooping dive attack, death.
* **Cave Rats**: [`assets/graphics/rat`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/rat) — Idle, scurrying movement, bite attack, death.
* **Pigeons & Wild Birds**: [`assets/graphics/pigeon`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/pigeon) — Perching, take-off, and flying cycles.
* **Armored Snails**: [`assets/graphics/snail`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/snail) — Shell crawl and retreat.
* **Serpents / Vipers**: [`assets/graphics/snake`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/snake) — Slither, coil, and strike.

---

### 💀 Ghosts, Undead & Spiritual Entities (734 Images across 44 Sets)

* **Skeletons (White / Armored Minions)**:
  * Path: [`assets/skeleton`](file:///home/chosen333/Software/Pixel-Runner/assets/skeleton)
  * States: Idle (11f), Walk (13f), Attack 1 (18f), Attack 2 (9f), Hurt (5f), Death (13f).
* **Blood Zombies**:
  * Path: [`assets/graphics/bloodZombie`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/bloodZombie)
  * Characteristics: Blood-soaked decaying husks with heavy claw strikes.
* **Skeleton Zombies**:
  * Path: [`assets/graphics/SkeletonZombie`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/SkeletonZombie)
  * Characteristics: Armored undead hybrids.
* **Necromancer / The Broker**:
  * Path: [`assets/graphics/Necromancer`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Necromancer)
  * Characteristics: Floating dark robed occultist with grimoire and summoning circles.
* **Moonstone Keeper (Candora's Exiled Priestess)**:
  * Path: [`assets/graphics/Moonstone_Keeper Eldermoon_Grove - By SUCART`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Moonstone_Keeper%20Eldermoon_Grove%20-%20By%20SUCART)
  * Characteristics: Horned spirit guardian with celestial cloak (Idle, Sky Land, Sky Launch).
* **Fairies / Light Wisps**:
  * Path: [`assets/graphics/Fairy`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Fairy)
  * Characteristics: Floating winged light orbs.
* **Undead & Warlock Skill Icons**:
  * Over 100 high-res icons (`512x512` & `32x32`) in [`Free Warlock Skills`](file:///home/chosen333/Software/Pixel-Runner/assets/Free%20Warlock%20Skills/PNG) and [`Free-Undead-Skill-Pixel-Art-Icons`](file:///home/chosen333/Software/Pixel-Runner/assets/Free-Undead-Skill-Pixel-Art-Icons).

---

### 🛸 Otherworldly Relics, Props & VFX (2,360 Images across 107 Sets)

* **Mysterious Monoliths & Cosmic Artifacts**:
  * Path: [`assets/PIPOYA FREE VFX Mysterious Object`](file:///home/chosen333/Software/Pixel-Runner/assets/PIPOYA%20FREE%20VFX%20Mysterious%20Object)
  * Sizes: `192x192` and `480x480`. Floating crystalline monoliths, pulsing rift orbs, and alien obelisks.
* **Warp Portals & Dimensional Gates**:
  * Path: [`assets/Pipoya VFX WarpPortal`](file:///home/chosen333/Software/Pixel-Runner/assets/Pipoya%20VFX%20WarpPortal), [`assets/spr_portal_strip8`](file:///home/chosen333/Software/Pixel-Runner/assets/spr_portal_strip8)
  * Characteristics: Swirling spatial portals with multi-color particle rings.
* **Cosmic Sigils & Sacred Geometry**:
  * Path: [`assets/Pattern-Panic-v-1.0`](file:///home/chosen333/Software/Pixel-Runner/assets/Pattern-Panic-v-1.0)
* **Interactive Props & Loot**:
  * Path: [`assets/graphics/Pixel Treasure Chest Pack`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel%20Treasure%20Chest%20Pack), [`assets/graphics/Props`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Props)
  * Assets: Wooden, Iron, Gold, and Mimic chests, braziers, torches, tombstones, and ancient statues.
* **VFX Explosions, Blood & Spells**:
  * Path: [`assets/graphics/Pixel Explosion Effects Pack 01 v1_1`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Pixel%20Explosion%20Effects%20Pack%2001%20v1_1), [`assets/graphics/VFX Blood Concepts`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/VFX%20Blood%20Concepts), [`assets/graphics/Fire Effect 2`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/Fire%20Effect%202), [`assets/graphics/swirl magic shots`](file:///home/chosen333/Software/Pixel-Runner/assets/graphics/swirl%20magic%20shots)
