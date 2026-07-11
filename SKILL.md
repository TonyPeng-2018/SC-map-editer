---
name: scmap
description: Read, understand, translate and edit StarCraft (Brood War) .scx/.scm maps from natural language. Use when the user wants to inspect a StarCraft map's triggers/strings/mechanics, translate a map to another language, shorten or lengthen a map's timeline, or otherwise edit a StarCraft map programmatically. Triggers on ".scx", ".scm", "StarCraft map", "triggers", "CHK", "MPQ", "ScmDraft".
---

# scmap — edit StarCraft maps from natural language

A pure-Python, zero-dependency engine for StarCraft: Brood War map files. It
unpacks the MPQ archive, decodes the CHK (strings, triggers, locations, units),
lets you edit, and repacks a playable `.scx`/`.scm`.

## When to use

- "What does this map do / how does its oxygen / spawn / timer work?" → analyze
- "Translate this Korean map to English" → translate strings
- "Make this 60-minute map ~25 minutes" → rescale the timeline
- "List every spawn / victory / timer trigger" → dump triggers
- Any programmatic StarCraft map edit

## Setup

Nothing to install — the `engine/` folder is pure Python 3.8+. Run the CLI from
the repo root (`python -m engine.cli ...`) or import `from engine import SCMap`.

## Core workflow

1. **Inspect first.** Always start by understanding the map before editing:
   ```
   python -m engine.cli info "MAP.scx"
   python -m engine.cli strings "MAP.scx" --korean        # strings needing translation
   python -m engine.cli triggers "MAP.scx" --grep Victory  # find specific logic
   ```
   Report the mechanics back to the user (timeline length, victory/defeat
   conditions, spawn structure) before proposing changes.

2. **Confirm the change** (target language, target length, which version) — these
   are user decisions; ask if unspecified.

3. **Edit via the API** (preferred for anything non-trivial) or the CLI:
   ```python
   from engine import SCMap
   m = SCMap.open("MAP.scx")
   m.rescale_time(0.35)                          # 70 min -> ~25 min
   m.translate({33: "Creature discovered: Mars Lizard", ...})
   m.save("MAP_out.scx")
   ```

4. **Verify** by reopening the output and re-running `info` — confirm
   `korean strs: 0`, the timeline is the intended length, and the map name is
   right. The engine round-trips byte-for-byte for untouched data, so a diff of
   `info` before/after shows exactly what changed.

## Key facts about the format (so you edit correctly)

- **Timeline** is driven by `ElapsedTime` conditions (seconds) and
  `SetCountdownTimer` actions. `rescale_time(factor)` scales all of them; the
  relative difficulty curve is preserved. Wave spawns and boss timing follow.
- **Strings** are indexed (1-based) and referenced by index from triggers,
  locations and map properties. Preserve indices — `translate()` does. Korean
  maps use **cp949**; leading `\x0N` bytes are colour codes, keep them.
- **Triggers** are 2400 bytes each: 16 conditions + 64 actions + exec players.
  Common patterns: oxygen/score via `SetScore` (custom score), spawns via
  `CreateUnit` at spawn locations, death-counters used as timers/rate-limiters.
- Rebuilt archives store files uncompressed+unencrypted (single unit) — smaller
  effort, fully compatible with StarCraft, ScmDraft and every MPQ tool.

## Translating a whole map (recipe)

1. `python -m engine.cli strings MAP --korean --json korean.json`
2. Produce an English `{index: text}` mapping (translate each unique text, reuse
   for duplicate indices; keep leading colour codes and `\r\n`).
3. `python -m engine.cli translate MAP mapping.json --out MAP_ENG.scx`
4. Reopen and confirm `korean strs: 0`.

See `examples/survival_in_mars/` for a complete worked example (translate +
shorten a 70-minute Korean survival map into a 25-minute English one).

## Authoring new content (units, triggers, whole maps)

Beyond editing, the engine can *author* content on a terrain base:

```python
from engine import SCMap
from engine.triggerbuild import TriggerBuilder, C, A
m = SCMap.open("base.scm")
m.set_player(2, owner="Computer", race="Zerg")
loc = m.add_point_location("Spawn", 115, 9, 2)
m.units.add("Zeratul (Dark Templar)", 12*32, 7*32, owner=0)
tb = TriggerBuilder()
tb.add(["Player3"], [C.elapsed("AtLeast", 60)],
       [A.create_unit("Player3", "Zergling", 6, loc), A.preserve()])
m.append_triggers(tb.serialize())
m.save("out.scx")
```

`examples/coop_zeratul_tychus/` generates a full SC2-style 2-player co-op map
this way. Generated triggers/units are byte-verified against shipped maps, but
**runtime behaviour (alliances, AI aggression, ability timing, balance) must be
playtested by the user** — note this when delivering a generated map.

## Guardrails

- Always keep the original file; write to a new filename.
- The engine does not yet deprotect heavily-protected maps or model every CHK
  section richly — for untouched sections it preserves raw bytes, which is safe.
- The user must test the output in StarCraft; you cannot launch the game.
