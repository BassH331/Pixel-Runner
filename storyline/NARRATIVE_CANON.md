# Pixel Runner — Narrative Canon

## Status

This document is the highest-level narrative rulebook for Pixel Runner. All story documents, in-game writing, character dialogue, relic text, cutscenes, endings, level events, narrative configuration, and AI-agent instructions must agree with it.

This is a working canon. Details marked **UNDECIDED** must not be invented by contributors or AI agents. The author must settle them before they become facts.

## 1. The One Governing Truth

The story is about a warrior entering a dangerous forest and being offered power by Andras. The offer appears to solve his problem, but the power gradually begins to master the person who accepts it.

The central danger is not merely dying in the forest. It is gaining what the warrior wants while losing command of himself.

The forest tests what the warrior loves, trusts, fears, and is willing to sacrifice. The player's choices must reveal character and carry consequences.

The story must ultimately expose the deception behind Andras's offer. The player should be able to recognise the pattern of the lie through encounters, evidence, dialogue, relics, and the effects of using the power—not only through a final explanation.

## 2. Religious Foundation: Subliminal, Never Preachy

The narrative is guided by Christian truth and biblical themes, but the game must communicate them indirectly. Do not explicitly name Jesus or God in in-game dialogue, narration, item descriptions, menus, or endings.

Express the underlying themes through story and consequence:

- **Temptation:** a promise is shaped around a real desire and hides its true cost.
- **Deception:** evil presents bondage as freedom, pride as strength, and surrender as victory.
- **The heart:** what the warrior chooses, loves, trusts, and serves reveals who he is becoming.
- **Truth:** lies are exposed by their fruit, contradictions, witnesses, and consequences.
- **Self-control:** strength includes the ability to refuse an easy but destructive path.
- **Courage and sacrifice:** doing what is right may be harder and more costly than taking power.
- **Hope and restoration:** corruption is serious, but the story must not treat darkness as the only possible destiny.

Do not turn characters into sermon-delivery devices. Let the audience discover the meaning through action, imagery, repeated motifs, and consequences. Subliminal does not mean vague: the moral cause and effect must remain understandable.

## 3. The Core Story Rules

1. **Andras is the source of the central temptation.** His offers must be useful and attractive enough that accepting them makes sense to the warrior. His true purpose must not be explained too early.
2. **Power has a cost.** Using Andras's power must have a meaningful connection to corruption, dependence, loss, or a reduced ability to choose freely. Mechanics and story text must not contradict one another.
3. **Refusal is a real path, not an easy path.** Rejecting the offer does not guarantee safety. The warrior may have to endure greater danger, rely on his own ability, or risk death.
4. **Every major encounter must serve the story.** Enemies, allies, bosses, and environmental events must reveal something about the forest, the offer, the warrior, or the consequences of previous choices.
5. **Every relic must matter.** A relic must reveal evidence, memory, temptation, warning, consequence, or a meaningful choice. It must not introduce unrelated lore.
6. **Choices must have consequences.** Do not present a moral choice and then ignore it in later dialogue, mechanics, or endings.
7. **The truth is discovered, not dumped.** Reveal it in a clear progression: question, clue, contradiction, consequence, recognition.
8. **No decorative lore that breaks canon.** Cool names, bosses, factions, powers, symbols, and backstories are rejected or revised if they compete with the central story.
9. **Do not invent missing facts.** If the protagonist's past, Andras's full plan, the forest's origin, or the final truth is not yet author-approved, mark it UNDECIDED.
10. **Keep the existing game intact unless asked otherwise.** Narrative unification is not permission to redesign gameplay, add levels, replace characters, or modify code.

## 4. The Current Narrative Anchor

The current Level 1 foundation includes:

- The Dark Forest.
- The Sealed Book, which introduces a warning that the forest changes those who enter it.
- A mysterious encounter shortly after the book.
- Skeletons and other threats that test the warrior's ability to survive.
- The Blood Zombie, who can serve as evidence of what Andras's offer can do to a person.
- The Watcher of the Abyss and other existing encounters that tempt the warrior toward greater darkness.
- Relics and a corruption system that can show the growing cost of power.

These are existing game elements, not permission to invent their full backstories. Their exact narrative roles must be checked against the author's approved storyline and the current implementation before changing their dialogue or behavior.

## 5. One Name, One Truth

The repository currently contains conflicting names and lore, including Andras, Voragis, Candora, Kaelen, Elysia, and competing descriptions of the protagonist's past and the larger plot.

Until the author explicitly approves otherwise:

- Andras is the name used for the central tempter in the current story direction.
- Do not silently substitute another demon, deity, contract system, lost relative, or origin story.
- Do not treat older conflicting lore as canon simply because it appears in a Markdown file or config.
- Preserve useful characters and assets where possible, but revise their narrative roles to fit the approved canon.
- Do not delete or rename implementation identifiers casually; first determine whether they are referenced by code, saved data, tests, or editors.

The protagonist's name, exact past, initial wound or desire, the stranger's identity, the forest's origin, the precise lie Andras tells, and the final revelation remain **UNDECIDED** unless approved in the primary story bible.

## 6. Repository-Wide Consistency Rules

Before editing any narrative-related file:

1. Read this canon and the current primary story bible.
2. Inspect the relevant implementation and configuration so the writing describes what the game actually does.
3. Identify any conflict with established facts, terminology, mechanics, character motivations, or the religious foundation.
4. Propose a minimal correction that preserves the current game structure.
5. Update all affected narrative references together. Do not fix one file while leaving the old contradiction in another.
6. Validate structured data such as JSON after edits.
7. Report what changed, which files remain inconsistent, and which story questions still require the author's decision.

If a feature cannot fit the canon, do not invent a second truth to justify it. Flag it for the author to decide whether it should be reframed, postponed, or removed.

## 7. Source-of-Truth Order

When documents conflict, use this order:

1. The author's explicitly approved decisions.
2. This Narrative Canon for governing principles.
3. The approved primary story bible for plot, character facts, and chronology.
4. The level-by-level narrative outline.
5. In-game dialogue, relic text, cutscenes, and ending text.
6. Configuration comments, developer notes, agent skills, README descriptions, and scratch files.

This order does not authorise agents to overwrite the story bible with assumptions. Any conflict with an approved decision must be reported and resolved at the source.

## 8. Content That Must Never Drift

Every part of Pixel Runner must answer at least one of these questions:

- What does the warrior want badly enough to risk himself?
- How does Andras use that desire to tempt him?
- What does the warrior believe at this point, and what evidence challenges it?
- What does the use or refusal of power cost him?
- What does this encounter reveal about the forest or a previous victim?
- How does this moment expose the state of the warrior's heart?
- How does this prepare the player to recognise the central deception?

If a piece of content answers none of these questions and adds no necessary gameplay clarity, it probably does not belong in the narrative.

## 9. Current Work Order

Do not rewrite every file at once. First, reconcile the primary story bible with the author's handwritten storyline and explicitly approved decisions. Then establish a concise level-by-level outline. Only after that should the team align the narrative skill instructions, Level 1 events, relic text, dialogue, cutscenes, endings, and supporting documentation.

No gameplay code changes, character removals, level redesigns, or irreversible lore decisions are authorised by this document alone.
