"""
the_eye_manager.py — Perception Data Engine & Unity-Style Story Tree Model for Pixel-Runner.

Manages the dual-mapped hierarchical story tree of the player's journey:
1. Timeline Perspective: Act -> Distance Milestone -> Entity -> Speech / Taunt Lines
2. Entity Perspective: Entity Category -> Entity -> Speeches & Taunts mapped to Timeline

Each conversation line is explicitly tagged with whether it is a TAUNT or DIALOGUE (is_taunt: bool).
Provides full CRUD: add speech/taunt, delete speech/taunt, edit text, toggle taunt status,
and persist changes directly to level_1.json and storyline_config.json with backups.
"""

from __future__ import annotations

import os
import json
import time
import copy
from typing import Dict, List, Optional, Any, Tuple

LEVEL_1_PATH = "game_data/level_1.json"
STORYLINE_PATH = "game_data/storyline_config.json"


class SpeechItem:
    """An individual speech line, cutscene dialogue, or in-combat taunt."""

    def __init__(
        self,
        speech_id: str,
        parent_node_id: str,
        speaker_name: str,
        text: str,
        category: str,  # "encounter", "combat_taunt", "pre_fight", "death_line", "corruption_low", "corruption_mid", "corruption_high", "relic"
        is_taunt: bool = False,
        distance: int = 0,
        act: str = "",
        relic_id: Optional[str] = None,
        list_idx: Optional[int] = None,
        trigger_type: str = "distance",  # "distance", "proximity", "combat_taunt", "pre_fight", "death_line", "corruption"
        hold_duration: float = 4.0,       # seconds to display on screen
        audio_cue: Optional[str] = None, # sound cue or voiceover id (e.g. "whisper", "boss_taunt", "evil_eye_bones")
    ):
        self.speech_id = speech_id
        self.parent_node_id = parent_node_id
        self.speaker_name = speaker_name
        self.text = text
        self.category = category
        self.is_taunt = is_taunt
        self.distance = distance
        self.act = act
        self.relic_id = relic_id
        self.list_idx = list_idx
        self.trigger_type = trigger_type
        self.hold_duration = hold_duration
        self.audio_cue = audio_cue
        self.original_text = text
        self.original_is_taunt = is_taunt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speech_id": self.speech_id,
            "parent_node_id": self.parent_node_id,
            "speaker_name": self.speaker_name,
            "text": self.text,
            "category": self.category,
            "is_taunt": self.is_taunt,
            "distance": self.distance,
            "act": self.act,
            "relic_id": self.relic_id,
            "list_idx": self.list_idx,
            "trigger_type": self.trigger_type,
            "hold_duration": self.hold_duration,
            "audio_cue": self.audio_cue,
        }


class TreeItem:
    """
    Unity-style hierarchical tree node.
    Supports expandable/collapsible folders, child hierarchy, and metadata badges.
    """

    def __init__(
        self,
        item_id: str,
        label: str,
        node_type: str,  # "root", "act", "milestone", "entity_category", "entity", "speech"
        data: Optional[Any] = None,
        parent: Optional["TreeItem"] = None,
        icon: str = "📁",
        badge: str = "",
        badge_color: Tuple[int, int, int] = (150, 150, 150),
        is_taunt: Optional[bool] = None,
    ):
        self.item_id = item_id
        self.label = label
        self.node_type = node_type
        self.data = data
        self.parent = parent
        self.children: List[TreeItem] = []
        self.expanded: bool = True
        self.icon = icon
        self.badge = badge
        self.badge_color = badge_color
        self.is_taunt = is_taunt

    def add_child(self, child: "TreeItem") -> "TreeItem":
        child.parent = self
        self.children.append(child)
        return child

    @property
    def has_children(self) -> bool:
        return len(self.children) > 0


class StoryNode:
    """Represents an encounter node on the player's story journey."""

    def __init__(
        self,
        node_id: str,
        title: str,
        distance: int,
        act: str,
        entity_type: str,  # "NPC", "ENEMY", "MINI-BOSS", "BOSS", "RELIC", "LORE"
        character_name: str,
        sprite_path: str,
        summary: str,
        conversations: Dict[str, Any],
        source_file: str,  # "level_1" or "storyline"
        source_key: Optional[str] = None,
    ):
        self.node_id = node_id
        self.title = title
        self.distance = distance
        self.act = act
        self.entity_type = entity_type
        self.character_name = character_name
        self.sprite_path = sprite_path
        self.summary = summary
        self.conversations = conversations
        self.source_file = source_file
        self.source_key = source_key
        self.original_conversations = copy.deepcopy(conversations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "distance": self.distance,
            "act": self.act,
            "entity_type": self.entity_type,
            "character_name": self.character_name,
            "sprite_path": self.sprite_path,
            "summary": self.summary,
            "conversations": self.conversations,
            "source_file": self.source_file,
            "source_key": self.source_key,
        }


class TheEyePerceptionManager:
    """
    The All-Seeing Perception Manager.
    Reads level and storyline data, constructs the narrative trail, builds
    Unity-style tree hierarchies, and persists dialogue modifications.
    """

    _instance: Optional["TheEyePerceptionManager"] = None

    def __init__(
        self,
        level_path: str = LEVEL_1_PATH,
        storyline_path: str = STORYLINE_PATH,
    ):
        self.level_path = level_path
        self.storyline_path = storyline_path
        self.nodes: List[StoryNode] = []
        self._node_map: Dict[str, StoryNode] = {}
        self.speech_items: Dict[str, SpeechItem] = {}
        self.level_data: Dict[str, Any] = {}
        self.storyline_data: Dict[str, Any] = {}
        self.revision: int = 0
        self.load_all()

    @classmethod
    def get_instance(
        cls,
        level_path: str = LEVEL_1_PATH,
        storyline_path: str = STORYLINE_PATH,
    ) -> "TheEyePerceptionManager":
        if cls._instance is None:
            cls._instance = TheEyePerceptionManager(level_path, storyline_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def load_all(self) -> None:
        """Load JSON data from disk and build the full journey trail."""
        self._load_json_files()
        self._construct_story_trail()
        self._extract_all_speech_items()
        self.revision += 1

    def _load_json_files(self) -> None:
        if os.path.exists(self.level_path):
            try:
                with open(self.level_path, "r", encoding="utf-8") as f:
                    self.level_data = json.load(f)
            except Exception as e:
                print(f"[TheEye] Error loading {self.level_path}: {e}")
                self.level_data = {}
        else:
            self.level_data = {}

        if os.path.exists(self.storyline_path):
            try:
                with open(self.storyline_path, "r", encoding="utf-8") as f:
                    self.storyline_data = json.load(f)
            except Exception as e:
                print(f"[TheEye] Error loading {self.storyline_path}: {e}")
                self.storyline_data = {}
        else:
            self.storyline_data = {}

    def _construct_story_trail(self) -> None:
        """Construct the 16 canonical story nodes mapping the player's journey."""
        self.nodes.clear()
        self._node_map.clear()

        boss_dialogue = self.storyline_data.get("boss_dialogue", {})
        relics = self.storyline_data.get("relics", {})

        world_events = self.level_data.get("world_events", [])
        entities = self.level_data.get("entities", [])
        entity_dict = {}
        for ent in (world_events + entities):
            e_id = ent.get("id")
            if e_id is not None:
                entity_dict[str(e_id)] = ent
            if ent.get("params", {}).get("is_magic_book") or ent.get("is_magic_book") or str(e_id) == "10":
                entity_dict["magic_book"] = ent

        # ── 1. Node 1: Distance 0m — The Shattered Border (Prologue)
        gauntlet_relic = relics.get("shattered_gauntlet", {})
        self._add_node(
            StoryNode(
                node_id="node_00_prologue",
                title="Awakening at the Border Stone",
                distance=0,
                act="Act I: The Forest Verge",
                entity_type="RELIC",
                character_name="Fallen Runner & Andras",
                sprite_path="assets/free-undead-loot-pixel-art-icons/PNG/Transperent/Icon1.png",
                summary="The mortal warrior awakens on the bloodied verge. The shattered gauntlet seals the demonic pact.",
                conversations={
                    "primary": gauntlet_relic.get(
                        "memory_text",
                        "You fell on the battlefield. Your armor crushed. You were supposed to die here. Then, a voice offered you a second chance.",
                    ),
                    "lore": gauntlet_relic.get(
                        "lore",
                        "A gauntlet crushed into pieces — the last thing you wore before death took you. Andras found you here, broken and forgotten.",
                    ),
                    "combat_taunts": [
                        "Take my flame, warrior! Your death was meaningless; your vengeance will be eternal!",
                    ],
                    "corruption_low": "A faint heartbeat remains beneath the cold plate armor.",
                    "corruption_mid": "The veins in your right arm blacken with demonic essence.",
                    "corruption_high": "The gauntlet fuses directly into your flesh.",
                },
                source_file="storyline",
                source_key="relics.shattered_gauntlet",
            )
        )

        # ── 2. Node 2: Distance 650m — Shrine of the Cursed Grimoire
        grim_ent = entity_dict.get("magic_book", {})
        grim_params = grim_ent.get("params", {})
        self._add_node(
            StoryNode(
                node_id="node_01_grimoire",
                title="Shrine of the Cursed Grimoire",
                distance=650,
                act="Act I: The Forest Verge",
                entity_type="NPC",
                character_name=grim_params.get("title") or "Cursed Grimoire",
                sprite_path=grim_params.get("sprite_dir") or "assets/Magic Book/magic book _16.png",
                summary="An ancient demonic tome hovering above an altar of roots. Taunts those who shed blood in the forest.",
                conversations={
                    "primary": grim_params.get("text") or "Those that come into this forest change from the very first kill, and their very first encounter with the creatures of this forest.",
                    "combat_taunts": grim_params.get("combat_taunts") or [
                        "Flesh and bone walk these woods, yet you carry mere iron. Let us see how long your pulse lasts.",
                        "The blood of the forest is on your hands. There is no turning back now, wanderer.",
                        "Each strike feeds the tome. Your iron is merely our quill.",
                    ],
                    "death_line": "The pages never close... they only wait for the next fool.",
                    "corruption_low": "You cling to your fragile mortal memories.",
                    "corruption_mid": "The ink flows thicker as you harvest the slain.",
                    "corruption_high": "We are bound together in the black ash of discord.",
                    "relic_branch": {
                        "relic_id": "tainted_sigil",
                        "text": "The sigil on your wrist pulses in harmony with my scripture.",
                    },
                },
                source_file="level_1",
                source_key="entities.magic_book",
            )
        )

        # ── 3. Node 3: Distance 1,080m — The Bone Fields Outpost
        self._add_node(
            StoryNode(
                node_id="node_02_skeletons",
                title="The Bone Fields Outpost",
                distance=1080,
                act="Act I: The Forest Verge",
                entity_type="ENEMY",
                character_name="Skeleton Minions",
                sprite_path="assets/skeleton",
                summary="The skeletal remains of past runners reanimated by necromantic ash.",
                conversations={
                    "primary": "Rattling bones rise from the soil! Intruders shall feed the roots of the woods!",
                    "combat_taunts": [
                        "Flesh... tear the living flesh!",
                        "Join us in the dirt, mortal!",
                        "No one leaves the dark forest unbroken!",
                    ],
                    "death_line": "Returned to dust... but master will raise us again...",
                    "corruption_low": "Your strike is swift, but the woods are endless.",
                    "corruption_mid": "You shatter bone like one accustomed to slaughter.",
                    "corruption_high": "You smell of our master... yet you strike us down?",
                },
                source_file="storyline",
                source_key="enemy_taunts.skeleton_minion",
            )
        )

        # ── 4. Node 4: Distance 2,200m — The Void Scribe's Crossing
        scribe_ent = entity_dict.get("npc_void_scribe", {})
        scribe_params = scribe_ent.get("params", {})
        scribe_dial = scribe_params.get("dialogue", {})
        scribe_corrupt = scribe_dial.get("corruption_variants", {})
        self._add_node(
            StoryNode(
                node_id="node_03_void_scribe",
                title="The Void Scribe's Crossing",
                distance=2200,
                act="Act I: The Forest Verge",
                entity_type="NPC",
                character_name=scribe_params.get("title", "Void Scribe"),
                sprite_path="assets/graphics/Wizard_NPC",
                summary="A hooded chronicler documenting every pact, death, and hollowed warrior in the endless ledger.",
                conversations={
                    "primary": scribe_params.get(
                        "text",
                        "I record what Andras makes. Names, dates, fates. The ledger is never full. There is always room.",
                    ),
                    "combat_taunts": [
                        "Do not spill ink on my ledger, runner.",
                        "Every blow you strike fills another line.",
                    ],
                    "death_line": "My ink may dry, but your doom is already inscribed.",
                    "corruption_low": scribe_corrupt.get("low", "No entry for you yet. Keep it that way."),
                    "corruption_mid": scribe_corrupt.get("mid", "Your name is... pencilled in. Lightly. For now."),
                    "corruption_high": scribe_corrupt.get("high", "I have been waiting for you. Your page is nearly ready."),
                    "relic_branch": scribe_dial.get(
                        "relic_branch",
                        {
                            "relic_id": "hollowed_ledger_page",
                            "text": "You found a page. One of many. Did you read the names?",
                        },
                    ),
                },
                source_file="level_1",
                source_key="entities.npc_void_scribe",
            )
        )

        # ── 5. Node 5: Distance 3,000m — The Void Bloom Rift
        bloom_ent = entity_dict.get("lore_void_bloom", {})
        self._add_node(
            StoryNode(
                node_id="node_04_void_bloom",
                title="The Void Bloom Rift",
                distance=3000,
                act="Act I: The Forest Verge",
                entity_type="LORE",
                character_name="Void Bloom",
                sprite_path="assets/graphics/UI/PNG/Exclamation_Yellow.png",
                summary="A pitch-black flower with silver veins that tracks the runner's steps.",
                conversations={
                    "primary": bloom_ent.get("params", {}).get(
                        "text",
                        "A flower grows from a crack in the earth ahead — black petals, silver centre. It turns toward you as you pass.",
                    ),
                    "corruption_low": "The silver centre glows faintly with Candora's residual grace.",
                    "corruption_mid": "The petals whisper as you sprint past.",
                    "corruption_high": "The flower turns to ash in your wake, consumed by your void aura.",
                },
                source_file="level_1",
                source_key="entities.lore_void_bloom",
            )
        )

        # ── 6. Node 6: Distance 3,500m — Watcher of the Abyss
        eye1_ent = entity_dict.get("11", {})
        eye1_params = eye1_ent.get("params", {})
        self._add_node(
            StoryNode(
                node_id="node_05_watcher_abyss",
                title="Watcher of the Abyss",
                distance=3500,
                act="Act II: Whispering Woods",
                entity_type="NPC",
                character_name=eye1_params.get("title", "Watcher of the Abyss"),
                sprite_path="assets/graphics/Evil Eye Beast For Itch/Idle",
                summary="The floating All-Seeing Eye of Andras, goading the player into violent surrender.",
                conversations={
                    "primary": eye1_params.get(
                        "text",
                        "Every skeleton you shatter was a mortal who refused my gift and crumbled. Break their bones, runner—prove you are worthy of the darkness!",
                    ),
                    "combat_taunts": [
                        "Yes, tear them apart! Why fight as a mortal when you can be a god?",
                        "Let them feel your wrath! Use my shadow!",
                        "Don't hold back. Give in to the void.",
                    ],
                    "death_line": "I see all... you cannot flee your own reflection...",
                    "corruption_low": "You hesitate! Weakness will rot you from within!",
                    "corruption_mid": "Good! The blood quickens your pulse!",
                    "corruption_high": "Now you see through my eye! Splendid carnage!",
                },
                source_file="level_1",
                source_key="entities.11",
            )
        )

        # ── 7. Node 7: Distance 4,000m — Candora's Silver Beacon
        cand_ent = entity_dict.get("npc_candora_messenger", {})
        cand_params = cand_ent.get("params", {})
        cand_dial = cand_params.get("dialogue", {})
        cand_corrupt = cand_dial.get("corruption_variants", {})
        self._add_node(
            StoryNode(
                node_id="node_06_candora_messenger",
                title="Candora's Silver Beacon",
                distance=4000,
                act="Act II: Whispering Woods",
                entity_type="NPC",
                character_name=cand_params.get("title", "Candora's Messenger"),
                sprite_path="assets/graphics/Wizard_NPC",
                summary="An emissary of the Moon Knight warning the player against yielding to the demon's pact.",
                conversations={
                    "primary": cand_params.get(
                        "text",
                        "Candora sent me to find the runner before he is lost. I may be too late. I am rarely early.",
                    ),
                    "combat_taunts": [
                        "Hold onto your honor, warrior!",
                        "Every time you summon his flame, your soul fades.",
                    ],
                    "death_line": "The light dims... but Candora never forgets...",
                    "corruption_low": cand_corrupt.get("low", "She still sees you. The light does not abandon the willing."),
                    "corruption_mid": cand_corrupt.get("mid", "She grieves for what you are becoming. But she has not looked away."),
                    "corruption_high": cand_corrupt.get("high", "I cannot reach you now. The void is too thick. But Candora... she still tries."),
                    "relic_branch": cand_dial.get(
                        "relic_branch",
                        {
                            "relic_id": "candoras_tear",
                            "text": "You carry her tear. She wept for you specifically. Do you understand what that means?",
                        },
                    ),
                },
                source_file="level_1",
                source_key="entities.npc_candora_messenger",
            )
        )

        # ── 8. Node 8: Distance 5,000m — Mural of the Scratched Face
        mural_ent = entity_dict.get("lore_faded_mural", {})
        self._add_node(
            StoryNode(
                node_id="node_07_mural",
                title="Mural of the Scratched Face",
                distance=5000,
                act="Act II: Whispering Woods",
                entity_type="LORE",
                character_name="Faded Mural",
                sprite_path="assets/graphics/UI/PNG/Exclamation_Yellow.png",
                summary="An ancient stone fresco of a hero whose face was deliberately erased.",
                conversations={
                    "primary": mural_ent.get("params", {}).get(
                        "text",
                        "A mural, half-collapsed. It shows a figure standing at a threshold. The figure's face has been scratched out.",
                    ),
                    "corruption_low": "The carving retains traces of human compassion.",
                    "corruption_mid": "Deep gouges mark the stone, freshly carved by clawed hands.",
                    "corruption_high": "The scratched face appears eerily familiar — it matches your own visage.",
                },
                source_file="level_1",
                source_key="entities.lore_faded_mural",
            )
        )

        # ── 9. Node 9: Distance 6,500m — The Previous Runner's Camp
        ronin_ent = entity_dict.get("npc_previous_runner", {})
        ronin_params = ronin_ent.get("params", {})
        ronin_dial = ronin_params.get("dialogue", {})
        ronin_corrupt = ronin_dial.get("corruption_variants", {})
        self._add_node(
            StoryNode(
                node_id="node_08_previous_runner",
                title="The Previous Runner's Camp",
                distance=6500,
                act="Act II: Whispering Woods",
                entity_type="NPC",
                character_name=ronin_params.get("title", "The Previous Runner"),
                sprite_path="assets/graphics/Ronin/spr_RoninIdle_strip8_frames",
                summary="The weathered Ronin who made the pact before you, warning of the trap of demonic strength.",
                conversations={
                    "primary": ronin_params.get(
                        "text",
                        "I recognise that mark. I wore it once. I thought it made me stronger. I was right. I was also wrong.",
                    ),
                    "combat_taunts": [
                        "Keep your guard raised, rookie!",
                        "Speed without purpose is merely a faster death!",
                    ],
                    "death_line": "The path claims another... forgive me...",
                    "corruption_low": ronin_corrupt.get("low", "You fight it better than I did. That is either strength or stubbornness. Either may save you."),
                    "corruption_mid": ronin_corrupt.get("mid", "This is where I started losing myself. The mid-point. It does not feel like a point of no return. That is the trap."),
                    "corruption_high": ronin_corrupt.get("high", "I cannot tell you apart from what I became. That frightens me more than Andras ever did."),
                    "relic_branch": ronin_dial.get(
                        "relic_branch",
                        {
                            "relic_id": "amalgam_core",
                            "text": "You found the core. Then you know what Andras intended both of us to become. Run. Or don't. It may not matter now.",
                        },
                    ),
                },
                source_file="level_1",
                source_key="entities.npc_previous_runner",
            )
        )

        # ── 10. Node 10: Distance 7,000m — The Scythe's Hunger
        scythe_ent = entity_dict.get("12", {})
        scythe_params = scythe_ent.get("params", {})
        self._add_node(
            StoryNode(
                node_id="node_09_scythe_hunger",
                title="The Scythe's Hunger",
                distance=7000,
                act="Act II: Whispering Woods",
                entity_type="NPC",
                character_name=scythe_params.get("title", "The Scythe's Hunger"),
                sprite_path="assets/graphics/Evil Eye Beast For Itch/Idle",
                summary="An embodiment of the demonic scythe demanding the souls of the threshold guardian ahead.",
                conversations={
                    "primary": scythe_params.get(
                        "text",
                        "Mere bone dust will not sate my hunger. The Gatekeeper ahead holds a concentrated mass of souls. Rip it from his chest!",
                    ),
                    "combat_taunts": [
                        "Harvest his life force! Gorge upon his spirit!",
                        "Let no marrow go unconsumed!",
                    ],
                    "death_line": "Starved... for now...",
                    "corruption_low": "You still hesitate before gorging on essence.",
                    "corruption_mid": "Your thirst matches my edge.",
                    "corruption_high": "Drink deep, host! We are famine incarnate!",
                },
                source_file="level_1",
                source_key="entities.12",
            )
        )

        # ── 11. Node 11: Distance 7,500m — Silence of the Void
        silence_ent = entity_dict.get("lore_void_sound", {})
        self._add_node(
            StoryNode(
                node_id="node_10_void_silence",
                title="Silence of the Void",
                distance=7500,
                act="Act II: Whispering Woods",
                entity_type="LORE",
                character_name="Void Silence",
                sprite_path="assets/graphics/UI/PNG/Exclamation_Yellow.png",
                summary="An acoustic dead-zone where all footsteps and heartbeat stop completely.",
                conversations={
                    "primary": silence_ent.get("params", {}).get(
                        "text",
                        "The world goes quiet. For three seconds, even your footsteps make no sound. Then it returns — louder than before.",
                    ),
                    "corruption_low": "The quiet feels unnatural and chilling.",
                    "corruption_mid": "In the silence, you hear Andras breathing beside you.",
                    "corruption_high": "The silence is comforting; mortal noise only irritates your senses.",
                },
                source_file="level_1",
                source_key="entities.lore_void_sound",
            )
        )

        # ── 12. Node 12: Distance 10,500m — The Moonstone Grove
        moon_ent = entity_dict.get("13", {})
        moon_params = moon_ent.get("params", {})
        self._add_node(
            StoryNode(
                node_id="node_11_moonstone_keeper",
                title="The Moonstone Grove",
                distance=10500,
                act="Act III: Threshold of Discord",
                entity_type="NPC",
                character_name=moon_params.get("title", "The Moonstone Keeper"),
                sprite_path="assets/graphics/Moonstone_Keeper Eldermoon_Grove - By SUCART/Idle-MoonstoneKeeper-SUCART/No BG",
                summary="Guardian of the moonlit sacred well, testing whether any humanity survives in the runner.",
                conversations={
                    "primary": moon_params.get(
                        "text",
                        "The dark flame cuts deep. Look inside: do you still remember who you were before you accepted my power, or just the blood?",
                    ),
                    "combat_taunts": [
                        "Steel yourself, runner. Truth is sharper than blades.",
                        "Candora's light judges all who step across this grove.",
                    ],
                    "death_line": "The grove falls dark... may mercy find you...",
                    "corruption_low": "Your heart still beats in human cadence. Hold onto it.",
                    "corruption_mid": "Shadow clouds your aura, yet your eyes still seek dawn.",
                    "corruption_high": "Only cold void remains in your chest. A pity.",
                },
                source_file="level_1",
                source_key="entities.13",
            )
        )

        # ── 13. Node 13: Distance 12,500m — Threshold of Discord (Boss: Gatekeeper)
        gatekeeper_dial = boss_dialogue.get("Gatekeeper", {})
        gatekeeper_corrupt = gatekeeper_dial.get("corruption_variants", {})
        self._add_node(
            StoryNode(
                node_id="node_12_gatekeeper",
                title="Threshold of Discord",
                distance=12500,
                act="Act III: Threshold of Discord",
                entity_type="BOSS",
                character_name="The Gatekeeper",
                sprite_path="assets/graphics/green_monster",
                summary="The colossal emerald sentinel guarding the boundary between the mortal woods and the abyss.",
                conversations={
                    "primary": "Nothing passes this threshold.",
                    "pre_fight": gatekeeper_dial.get(
                        "pre_fight",
                        [
                            "Nothing passes this threshold.",
                            "You bear his mark. And yet you hesitate. Pathetic.",
                        ],
                    ),
                    "combat_taunts": [
                        "Crush the worm!",
                        "His mark will not shield you from my stone!",
                        "Tear the runner limb from limb!",
                    ],
                    "death_line": gatekeeper_dial.get(
                        "death_line",
                        "The threshold... was never mine to hold...",
                    ),
                    "corruption_low": gatekeeper_corrupt.get("low", "Soft. He chose poorly with you."),
                    "corruption_mid": gatekeeper_corrupt.get("mid", "Halfway broken. I can see it in how you move."),
                    "corruption_high": gatekeeper_corrupt.get("high", "You already belong to him. Stop pretending otherwise."),
                },
                source_file="storyline",
                source_key="boss_dialogue.Gatekeeper",
            )
        )

        # ── 14. Node 14: Distance 16,500m — The Blood Pit (Mini-Boss: Blood Zombie)
        blood_dial = boss_dialogue.get("BloodZombie", {})
        blood_corrupt = blood_dial.get("corruption_variants", {})
        self._add_node(
            StoryNode(
                node_id="node_13_blood_zombie",
                title="The Blood Pit Ambush",
                distance=16500,
                act="Act IV: The Crimson Crucible",
                entity_type="MINI-BOSS",
                character_name="The Blood Zombie",
                sprite_path="assets/graphics/bloodZombie/Idle",
                summary="A hollowed, corrupted runner driven mad by Andras. Uncorks saucy, vulgar period & modern combat taunts.",
                conversations={
                    "primary": "I... remember being afraid of this. He told me the same things he told you. Do not become what I became.",
                    "pre_fight": blood_dial.get(
                        "pre_fight",
                        [
                            "I... remember being afraid of this.",
                            "He told me the same things he told you.",
                            "Do not become what I became.",
                        ],
                    ),
                    "combat_taunts": [
                        "Come on, pretty boy, bleed for me! Don't tell me you're getting winded already!",
                        "That all you got, you milk-livered bastard? My dead nan swung harder than that!",
                        "By the black rot, you're a clumsy piece of shit. Stand still and let me gut ya!",
                        "Ha! Call that a guard? Pure shite! I’ll carve that smug look right off your mug!",
                        "Thou callest that a swing?! Come closer, whelp, my teeth are thirsty!",
                    ],
                    "death_line": blood_dial.get(
                        "death_line",
                        "Finally... it ends. Do not... follow my path.",
                    ),
                    "corruption_low": blood_corrupt.get("low", "There is still time. I had this chance. I wasted it."),
                    "corruption_mid": blood_corrupt.get("mid", "You are halfway to what I was. Stop. Please."),
                    "corruption_high": blood_corrupt.get("high", "You are already further gone than I was at this point. I am sorry."),
                },
                source_file="storyline",
                source_key="boss_dialogue.BloodZombie",
            )
        )

        # ── 15. Node 15: Distance 25,000m — Sanctuary of Dying Embers (Boss: Fire Wizard)
        wiz_dial = boss_dialogue.get("FireWizard", {})
        wiz_corrupt = wiz_dial.get("corruption_variants", {})
        self._add_node(
            StoryNode(
                node_id="node_14_fire_wizard",
                title="Sanctuary of Dying Embers",
                distance=25000,
                act="Act IV: The Crimson Crucible",
                entity_type="BOSS",
                character_name="Fire Wizard",
                sprite_path="assets/wizard",
                summary="A former holy paragon consumed by living flames. Reflects the runner's hunger and inner combustion.",
                conversations={
                    "primary": "I was a guardian once. Before the fire consumed the man.",
                    "pre_fight": wiz_dial.get(
                        "pre_fight",
                        [
                            "I was a guardian once. Before the fire consumed the man.",
                            "I see the same hunger in your eyes that consumed mine.",
                        ],
                    ),
                    "combat_taunts": [
                        "Burn, runner! Feel the purity of agony!",
                        "Cinder and ash! That is all we leave behind!",
                    ],
                    "death_line": wiz_dial.get(
                        "death_line",
                        "The flame... dims. Perhaps now... I can rest.",
                    ),
                    "corruption_low": wiz_corrupt.get("low", "You still have light in you. I envy that. Protect it."),
                    "corruption_mid": wiz_corrupt.get("mid", "You walk the same edge I walked. I fell. You may not."),
                    "corruption_high": wiz_corrupt.get("high", "We are the same, you and I. That is why this hurts."),
                },
                source_file="storyline",
                source_key="boss_dialogue.FireWizard",
            )
        )

        # ── 16. Node 16: Distance 34,500m — The Fabricator's Citadel (Final Boss: Dark Ronin)
        ronin_boss_dial = boss_dialogue.get("DarkRonin", {})
        ronin_boss_corrupt = ronin_boss_dial.get("corruption_variants", {})
        self._add_node(
            StoryNode(
                node_id="node_15_dark_ronin",
                title="The Fabricator's Citadel",
                distance=34500,
                act="Act IV: The Crimson Crucible",
                entity_type="BOSS",
                character_name="Dark Ronin",
                sprite_path="assets/graphics/Ronin/spr_RoninIdle_strip8_frames",
                summary="The ultimate corrupted paragon and previous runner. The final obstacle before the demonic throne.",
                conversations={
                    "primary": "So. He sent another one.",
                    "pre_fight": ronin_boss_dial.get(
                        "pre_fight",
                        [
                            "So. He sent another one.",
                            "I was the last runner before you. I thought I was different.",
                            "Prove me right. Or prove me wrong. Either way, this ends here.",
                        ],
                    ),
                    "combat_taunts": [
                        "Show me what Andras promised you!",
                        "You swing like a desperate dog!",
                        "Is this the pinnacle of his new vessel?!",
                    ],
                    "death_line": ronin_boss_dial.get(
                        "death_line",
                        "You are not like me after all. Or... perhaps you are. Time will tell.",
                    ),
                    "corruption_low": ronin_boss_corrupt.get("low", "You fought this far and kept your soul. I did not think that was possible."),
                    "corruption_mid": ronin_boss_corrupt.get("mid", "Half-claimed. Andras will finish the rest. Unless you choose otherwise — now."),
                    "corruption_high": ronin_boss_corrupt.get("high", "You are already his. This fight is a formality. I hope you understand what you've become."),
                },
                source_file="storyline",
                source_key="boss_dialogue.DarkRonin",
            )
        )

        self.nodes.sort(key=lambda n: n.distance)

    def _add_node(self, node: StoryNode) -> None:
        self.nodes.append(node)
        self._node_map[node.node_id] = node

    def _extract_all_speech_items(self) -> None:
        """Deconstruct each node's conversations into individual SpeechItems."""
        self.speech_items.clear()
        for node in self.nodes:
            c = node.conversations

            # 1. Primary encounter speech
            if "primary" in c and c["primary"]:
                is_taunt_default = (node.entity_type in ("ENEMY", "MINI-BOSS") or "Grimoire" in node.character_name or "Abyss" in node.character_name)
                item_id = f"speech_{node.node_id}_primary"
                trig = "proximity" if node.entity_type == "NPC" else ("distance" if node.entity_type == "LORE" else ("proximity" if node.entity_type == "RELIC" else "distance"))
                cue = "npc_talk" if node.entity_type == "NPC" else ("lore_whisper" if node.entity_type == "LORE" else ("relic_found" if node.entity_type == "RELIC" else "whisper"))
                self.speech_items[item_id] = SpeechItem(
                    speech_id=item_id,
                    parent_node_id=node.node_id,
                    speaker_name=node.character_name,
                    text=c["primary"],
                    category="encounter",
                    is_taunt=is_taunt_default,
                    distance=node.distance,
                    act=node.act,
                    trigger_type=trig,
                    hold_duration=4.5 if node.entity_type == "NPC" else 4.0,
                    audio_cue=cue,
                )

            # 2. Combat taunts list
            taunts = c.get("combat_taunts", [])
            for idx, t in enumerate(taunts):
                item_id = f"speech_{node.node_id}_taunt_{idx}"
                cue = "boss_taunt" if node.entity_type in ("BOSS", "MINI-BOSS") else "enemy_taunt"
                self.speech_items[item_id] = SpeechItem(
                    speech_id=item_id,
                    parent_node_id=node.node_id,
                    speaker_name=node.character_name,
                    text=t,
                    category="combat_taunt",
                    is_taunt=True,  # Explicitly a combat taunt!
                    distance=node.distance,
                    act=node.act,
                    list_idx=idx,
                    trigger_type="combat_taunt",
                    hold_duration=3.5,
                    audio_cue=cue,
                )

            # 3. Pre-fight cutscene quotes
            pre_fights = c.get("pre_fight", [])
            for idx, pf in enumerate(pre_fights):
                item_id = f"speech_{node.node_id}_prefight_{idx}"
                self.speech_items[item_id] = SpeechItem(
                    speech_id=item_id,
                    parent_node_id=node.node_id,
                    speaker_name=node.character_name,
                    text=pf,
                    category="pre_fight",
                    is_taunt=False,  # Pre-fight cutscene dialogue
                    distance=node.distance,
                    act=node.act,
                    list_idx=idx,
                    trigger_type="pre_fight",
                    hold_duration=5.0,
                    audio_cue="boss_intro",
                )

            # 4. Death line
            if "death_line" in c and c["death_line"]:
                item_id = f"speech_{node.node_id}_death"
                self.speech_items[item_id] = SpeechItem(
                    speech_id=item_id,
                    parent_node_id=node.node_id,
                    speaker_name=node.character_name,
                    text=c["death_line"],
                    category="death_line",
                    is_taunt=False,
                    distance=node.distance,
                    act=node.act,
                    trigger_type="death_line",
                    hold_duration=4.0,
                    audio_cue="boss_death",
                )

            # 5. Corruption variants
            for c_level in ("low", "mid", "high"):
                key = f"corruption_{c_level}"
                if key in c and c[key]:
                    item_id = f"speech_{node.node_id}_{key}"
                    self.speech_items[item_id] = SpeechItem(
                        speech_id=item_id,
                        parent_node_id=node.node_id,
                        speaker_name=node.character_name,
                        text=c[key],
                        category=key,
                        is_taunt=(c_level == "high" and node.entity_type in ("BOSS", "MINI-BOSS")),
                        distance=node.distance,
                        act=node.act,
                        trigger_type="corruption",
                        hold_duration=4.0,
                        audio_cue="whisper",
                    )

            # 6. Relic branch
            if "relic_branch" in c and isinstance(c["relic_branch"], dict):
                rb = c["relic_branch"]
                item_id = f"speech_{node.node_id}_relic"
                self.speech_items[item_id] = SpeechItem(
                    speech_id=item_id,
                    parent_node_id=node.node_id,
                    speaker_name=node.character_name,
                    text=rb.get("text", ""),
                    category="relic",
                    is_taunt=False,
                    distance=node.distance,
                    act=node.act,
                    relic_id=rb.get("relic_id"),
                    trigger_type="proximity",
                    hold_duration=5.0,
                    audio_cue="relic_found",
                )

    # ══════════════════════════════════════════════════════════════════════════
    #  Unity-Style Hierarchical Tree Builders
    # ══════════════════════════════════════════════════════════════════════════

    def build_timeline_tree(self) -> TreeItem:
        """
        Builds Unity-style hierarchy by Timeline First:
        Root -> Act -> Distance Milestone -> Entity -> Speech / Taunt Lines.
        """
        root = TreeItem(
            item_id="tree_root_timeline",
            label="Pixel Runner Narrative Timeline",
            node_type="root",
            icon="🌐",
        )

        # Group nodes by Act
        act_map: Dict[str, List[StoryNode]] = {}
        for n in self.nodes:
            act_map.setdefault(n.act, []).append(n)

        for act_name, act_nodes in act_map.items():
            act_item = root.add_child(
                TreeItem(
                    item_id=f"act_{act_name}",
                    label=act_name,
                    node_type="act",
                    icon="📂",
                    badge=f"{len(act_nodes)} zones",
                    badge_color=(175, 75, 255),
                )
            )

            for node in act_nodes:
                d_str = f"{node.distance}m" if node.distance < 1000 else f"{node.distance/1000:.1f}km"
                milestone_item = act_item.add_child(
                    TreeItem(
                        item_id=f"ms_{node.node_id}",
                        label=f"{node.title}",
                        node_type="milestone",
                        data=node,
                        icon="📍",
                        badge=d_str,
                        badge_color=(255, 215, 75),
                    )
                )

                # Entity child
                ent_item = milestone_item.add_child(
                    TreeItem(
                        item_id=f"ent_{node.node_id}",
                        label=f"{node.character_name}",
                        node_type="entity",
                        data=node,
                        icon="👤",
                        badge=f"[{node.entity_type}]",
                        badge_color=(0, 220, 255),
                    )
                )

                # Attach Speech & Taunt items under entity
                for s_item in self._get_speeches_for_node(node.node_id):
                    self._create_speech_tree_child(ent_item, s_item)

        return root

    def build_entity_tree(self) -> TreeItem:
        """
        Builds Unity-style hierarchy by Entity First:
        Root -> Entity Category -> Entity -> Speeches mapped to Timeline Distance.
        """
        root = TreeItem(
            item_id="tree_root_entity",
            label="Pixel Runner Entity Roster",
            node_type="root",
            icon="👤",
        )

        categories = [
            ("BOSSES & MINI-BOSSES", ("BOSS", "MINI-BOSS"), "👑", (255, 215, 75)),
            ("NPCS & ALLIES", ("NPC",), "🧙", (0, 220, 255)),
            ("ENEMIES & MINIONS", ("ENEMY",), "💀", (240, 55, 75)),
            ("RELICS & LORE", ("RELIC", "LORE"), "📜", (175, 75, 255)),
        ]

        for cat_label, types, icon, color in categories:
            cat_nodes = [n for n in self.nodes if n.entity_type in types]
            if not cat_nodes:
                continue

            cat_item = root.add_child(
                TreeItem(
                    item_id=f"cat_{cat_label}",
                    label=cat_label,
                    node_type="entity_category",
                    icon=icon,
                    badge=f"{len(cat_nodes)} entities",
                    badge_color=color,
                )
            )

            for node in cat_nodes:
                d_str = f"{node.distance}m" if node.distance < 1000 else f"{node.distance/1000:.1f}km"
                ent_item = cat_item.add_child(
                    TreeItem(
                        item_id=f"ent_cat_{node.node_id}",
                        label=f"{node.character_name}",
                        node_type="entity",
                        data=node,
                        icon="👤",
                        badge=f"[{d_str}]",
                        badge_color=color,
                    )
                )

                for s_item in self._get_speeches_for_node(node.node_id):
                    self._create_speech_tree_child(ent_item, s_item)

        return root

    def _create_speech_tree_child(self, parent_item: TreeItem, s_item: SpeechItem) -> TreeItem:
        """Create a styled tree row for a speech or taunt item with clean badges."""
        if s_item.is_taunt:
            tag = "TAUNT"
            tag_col = (240, 55, 75)
            icon = "⚔"
        else:
            tag = "DIALOGUE"
            tag_col = (0, 220, 255)
            icon = "💬"

        # Short snippet
        preview = s_item.text.replace("\n", " ").strip()
        if len(preview) > 36:
            preview = preview[:33] + "..."

        child = parent_item.add_child(
            TreeItem(
                item_id=s_item.speech_id,
                label=f"{s_item.category.upper()}: \"{preview}\"",
                node_type="speech",
                data=s_item,
                icon=icon,
                badge=f"[{tag}]",
                badge_color=tag_col,
                is_taunt=s_item.is_taunt,
            )
        )
        return child

    def _get_speeches_for_node(self, node_id: str) -> List[SpeechItem]:
        return [s for s in self.speech_items.values() if s.parent_node_id == node_id]

    def flatten_tree(
        self,
        root: TreeItem,
        filter_text: str = "",
        type_filter: str = "ALL",  # "ALL", "TAUNT_ONLY", "DIALOGUE_ONLY"
    ) -> List[Tuple[TreeItem, int]]:
        """
        Recursively flattens visible rows based on expanded states and search filters.
        Returns list of (TreeItem, depth_level).
        """
        result: List[Tuple[TreeItem, int]] = []

        def _traverse(item: TreeItem, depth: int) -> None:
            # Root is usually not displayed directly
            if item.node_type != "root":
                # Check filtering for speech rows
                if item.node_type == "speech":
                    if type_filter == "TAUNT_ONLY" and not item.is_taunt:
                        return
                    if type_filter == "DIALOGUE_ONLY" and item.is_taunt:
                        return

                # Text filter check
                if filter_text:
                    ft = filter_text.lower()
                    if ft not in item.label.lower():
                        # If a parent, check if any descendants match
                        if not self._item_has_matching_descendant(item, ft):
                            return

                result.append((item, depth))

            if item.expanded:
                for child in item.children:
                    _traverse(child, depth + 1 if item.node_type != "root" else 0)

        _traverse(root, 0)
        return result

    def _item_has_matching_descendant(self, item: TreeItem, filter_text: str) -> bool:
        for child in item.children:
            if filter_text in child.label.lower():
                return True
            if self._item_has_matching_descendant(child, filter_text):
                return True
        return False

    def toggle_expand(self, item: TreeItem) -> None:
        """Toggle expanded/collapsed state of a tree row."""
        item.expanded = not item.expanded

    def expand_all(self, item: TreeItem) -> None:
        item.expanded = True
        for c in item.children:
            self.expand_all(c)

    def collapse_all(self, item: TreeItem) -> None:
        if item.node_type != "root":
            item.expanded = False
        for c in item.children:
            self.collapse_all(c)

    # ══════════════════════════════════════════════════════════════════════════
    #  Speech & Perception CRUD
    # ══════════════════════════════════════════════════════════════════════════

    def get_speech_item(self, speech_id: str) -> Optional[SpeechItem]:
        return self.speech_items.get(speech_id)

    def update_speech(
        self,
        speech_id: str,
        text: Optional[str] = None,
        is_taunt: Optional[bool] = None,
        category: Optional[str] = None,
        trigger_type: Optional[str] = None,
        hold_duration: Optional[float] = None,
        audio_cue: Optional[str] = None,
    ) -> bool:
        """Update text, taunt status, or category on a speech item."""
        s = self.get_speech_item(speech_id)
        if not s:
            return False

        if text is not None:
            s.text = text
        if is_taunt is not None:
            s.is_taunt = is_taunt
        if category is not None:
            s.category = category
        if trigger_type is not None:
            s.trigger_type = trigger_type
        if hold_duration is not None:
            s.hold_duration = hold_duration
        if audio_cue is not None:
            s.audio_cue = audio_cue

        # Sync back to parent node's conversations dict
        node = self._node_map.get(s.parent_node_id)
        if node:
            if s.category == "encounter":
                node.conversations["primary"] = s.text
            elif s.category == "combat_taunt" and s.list_idx is not None:
                taunts = node.conversations.get("combat_taunts", [])
                if 0 <= s.list_idx < len(taunts):
                    taunts[s.list_idx] = s.text
            elif s.category == "pre_fight" and s.list_idx is not None:
                pfs = node.conversations.get("pre_fight", [])
                if 0 <= s.list_idx < len(pfs):
                    pfs[s.list_idx] = s.text
            elif s.category == "death_line":
                node.conversations["death_line"] = s.text
            elif s.category.startswith("corruption_"):
                node.conversations[s.category] = s.text

        return True

    def add_speech_item(
        self,
        node_id: str,
        text: str,
        category: str = "combat_taunt",
        is_taunt: bool = True,
        trigger_type: Optional[str] = None,
        hold_duration: float = 4.0,
        audio_cue: Optional[str] = None,
    ) -> Optional[SpeechItem]:
        """Add a new speech line or combat taunt under an entity."""
        node = self._node_map.get(node_id)
        if not node:
            return None

        # Add to node conversations list
        if category == "combat_taunt":
            if "combat_taunts" not in node.conversations:
                node.conversations["combat_taunts"] = []
            node.conversations["combat_taunts"].append(text)
            list_idx = len(node.conversations["combat_taunts"]) - 1
            item_id = f"speech_{node_id}_taunt_{int(time.time()*1000)%100000}"
        else:
            list_idx = None
            item_id = f"speech_{node_id}_{category}_{int(time.time()*1000)%100000}"

        if trigger_type is None:
            trigger_type = "combat_taunt" if is_taunt else "distance"
        if audio_cue is None:
            trigger_cue = "boss_taunt" if (node.entity_type in ("BOSS", "MINI-BOSS") and is_taunt) else ("enemy_taunt" if is_taunt else "npc_talk")
        else:
            trigger_cue = audio_cue

        item = SpeechItem(
            speech_id=item_id,
            parent_node_id=node_id,
            speaker_name=node.character_name,
            text=text,
            category=category,
            is_taunt=is_taunt,
            distance=node.distance,
            act=node.act,
            list_idx=list_idx,
            trigger_type=trigger_type,
            hold_duration=hold_duration,
            audio_cue=trigger_cue,
        )
        self.speech_items[item_id] = item
        return item

    def delete_speech_item(self, speech_id: str) -> bool:
        """Remove a speech item from the active pool."""
        s = self.get_speech_item(speech_id)
        if not s:
            return False

        node = self._node_map.get(s.parent_node_id)
        if node and s.category == "combat_taunt" and s.list_idx is not None:
            taunts = node.conversations.get("combat_taunts", [])
            if 0 <= s.list_idx < len(taunts):
                taunts.pop(s.list_idx)

        self.speech_items.pop(speech_id, None)
        return True

    def get_nodes(self) -> List[StoryNode]:
        return self.nodes

    def get_node_by_id(self, node_id: str) -> Optional[StoryNode]:
        return self._node_map.get(node_id)

    def update_dialogue(
        self,
        node_id: str,
        dialogue_field: str,
        new_text: str,
        list_idx: Optional[int] = None,
    ) -> bool:
        node = self.get_node_by_id(node_id)
        if not node:
            return False

        if list_idx is not None and isinstance(node.conversations.get(dialogue_field), list):
            target_list = node.conversations[dialogue_field]
            if 0 <= list_idx < len(target_list):
                target_list[list_idx] = new_text
                return True
        else:
            node.conversations[dialogue_field] = new_text
            return True

        return False

    def add_combat_taunt(self, node_id: str, taunt: str) -> bool:
        node = self.get_node_by_id(node_id)
        if not node:
            return False
        if "combat_taunts" not in node.conversations:
            node.conversations["combat_taunts"] = []
        node.conversations["combat_taunts"].append(taunt)
        self._extract_all_speech_items()
        return True

    def remove_combat_taunt(self, node_id: str, index: int) -> bool:
        node = self.get_node_by_id(node_id)
        if not node or "combat_taunts" not in node.conversations:
            return False
        taunts = node.conversations["combat_taunts"]
        if 0 <= index < len(taunts):
            taunts.pop(index)
            self._extract_all_speech_items()
            return True
        return False

    def revert_node_dialogue(self, node_id: str) -> bool:
        node = self.get_node_by_id(node_id)
        if not node:
            return False
        node.conversations = copy.deepcopy(node.original_conversations)
        self._extract_all_speech_items()
        return True

    def save_perception(self) -> Tuple[bool, str]:
        """
        Persist all perception/conversation modifications back to disk.
        Automatically creates timestamped backups of modified files.
        """
        try:
            # 1. Update storyline_data for boss dialogues & relics
            if "boss_dialogue" not in self.storyline_data:
                self.storyline_data["boss_dialogue"] = {}

            for node in self.nodes:
                if node.source_file == "storyline" and node.source_key:
                    if node.source_key.startswith("boss_dialogue."):
                        boss_key = node.source_key.split(".", 1)[1]
                        if boss_key not in self.storyline_data["boss_dialogue"]:
                            self.storyline_data["boss_dialogue"][boss_key] = {}
                        bd = self.storyline_data["boss_dialogue"][boss_key]
                        if "pre_fight" in node.conversations:
                            bd["pre_fight"] = node.conversations["pre_fight"]
                        if "death_line" in node.conversations:
                            bd["death_line"] = node.conversations["death_line"]
                        if "combat_taunts" in node.conversations:
                            bd["combat_taunts"] = node.conversations["combat_taunts"]
                        if "corruption_variants" not in bd:
                            bd["corruption_variants"] = {}
                        bd["corruption_variants"]["low"] = node.conversations.get("corruption_low", "")
                        bd["corruption_variants"]["mid"] = node.conversations.get("corruption_mid", "")
                        bd["corruption_variants"]["high"] = node.conversations.get("corruption_high", "")

                    elif node.source_key.startswith("relics."):
                        relic_k = node.source_key.split(".", 1)[1]
                        if "relics" in self.storyline_data and relic_k in self.storyline_data["relics"]:
                            r_entry = self.storyline_data["relics"][relic_k]
                            r_entry["memory_text"] = node.conversations.get("primary", r_entry.get("memory_text", ""))
                            r_entry["lore"] = node.conversations.get("lore", r_entry.get("lore", ""))

                elif node.source_file == "level_1" and node.source_key:
                    if node.source_key.startswith("entities.") or node.source_key.startswith("world_events."):
                        ent_id = node.source_key.split(".", 1)[1]
                        world_events = self.level_data.get("world_events", [])
                        entities = self.level_data.get("entities", [])
                        for ent in (world_events + entities):
                            is_match = (str(ent.get("id")) == ent_id)
                            if not is_match and ent_id == "magic_book" and (ent.get("params", {}).get("is_magic_book") or ent.get("is_magic_book") or str(ent.get("id")) == "10"):
                                is_match = True
                            if is_match:
                                params = ent.get("params", {})
                                if "text" in params and "primary" in node.conversations:
                                    params["text"] = node.conversations["primary"]
                                if "dialogue" in params:
                                    d_block = params["dialogue"]
                                    if "default" in d_block:
                                        d_block["default"] = node.conversations["primary"]
                                    if "corruption_variants" in d_block:
                                        cv = d_block["corruption_variants"]
                                        cv["low"] = node.conversations.get("corruption_low", cv.get("low", ""))
                                        cv["mid"] = node.conversations.get("corruption_mid", cv.get("mid", ""))
                                        cv["high"] = node.conversations.get("corruption_high", cv.get("high", ""))
                                if "combat_taunts" in node.conversations:
                                    params["combat_taunts"] = node.conversations["combat_taunts"]

            self._save_with_backup(self.storyline_path, self.storyline_data)
            self._save_with_backup(self.level_path, self.level_data)

            self.revision += 1
            return True, "Story tree perception successfully saved with timestamped backups!"
        except Exception as e:
            return False, f"Failed to save story tree perception: {e}"

    def _save_with_backup(self, file_path: str, data: Dict[str, Any]) -> None:
        if not file_path or not data:
            return
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup_{int(time.time())}"
            try:
                with open(file_path, "r", encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            except Exception:
                pass

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
