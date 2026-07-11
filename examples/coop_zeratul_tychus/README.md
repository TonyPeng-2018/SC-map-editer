# Example: SC2-style Co-op — Zeratul & Tychus (Phase 2)

Generates a **complete, playable 2-player co-op map from scratch in Python** —
no GUI editor. It demonstrates the full authoring side of the engine: placing
units, setting players/races/forces, creating locations, and generating triggers
(waves, boss, economy, hero abilities, win/lose).

```bash
python examples/coop_zeratul_tychus/build_coop.py
# built 22 triggers, 267 units
# saved -> .../Mars Coop - Zeratul & Tychus.scx
```

## Concept

Two allied commanders defend the west side of a Big Game Hunters map against ten
escalating Zerg waves, then kill a boss to win.

| | **Zeratul** (Player 1) | **Tychus** (Player 2) |
|---|---|---|
| Race | Protoss | Terran |
| Hero | Zeratul (Dark Templar) | Jim Raynor (Marine), renamed Tychus |
| Start army | 2 Dark Templar, 2 Dragoons, Zealot, Nexus, Gateway, Cannon | 3 Marines, Firebat, Medic, CC, Barracks, Bunker |
| Signature ability | **Void Strike** — walk Zeratul onto the Void Beacon → 3 Dark Templar strike at the front (30s cd) | **Reinforce Drop** — walk Tychus onto the Drop Beacon → 4 Marines + Medic drop in (30s cd) |

- **Economy:** starting 250 minerals + a passive income drip.
- **Waves:** every ~70–110 s from three eastern spawn points, attack-moving to
  the front line; unit types escalate Zergling → Hydralisk → Mutalisk → Lurker →
  Ultralisk → mixed.
- **Boss:** at 15:00 the Torrasque + Infested Kerrigan awaken.
- **Win:** kill the Torrasque after the boss wave. **Lose:** either commander dies.

## How it's built (engine features used)

| Step | API |
|------|-----|
| Players / races | `m.set_player(i, owner=..., race=...)` |
| Alliance | `m.set_forces({0:0,1:0,2:1}, names=..., flags={0:0x0E})` |
| Locations | `m.add_point_location(name, tile_x, tile_y, radius)` |
| Units | `m.units.add("Zeratul (Dark Templar)", x, y, owner)` |
| Triggers | `TriggerBuilder` + `C.*` conditions + `A.*` actions |
| Strings | `m.add_string(text)` |
| Save | `m.save(path)` |

Cooldowns use the classic UMS trick: a per-player death counter (`Spider Mine`)
ticked every trigger cycle by a clock trigger; an ability checks the counter and
resets it. A hyper-trigger keeps recurring triggers responsive.

## ⚠️ Verified vs. needs playtesting

**Verified structurally** (parses, correct IDs, triggers decode to the intended
logic, round-trips): everything the generator emits.

**NOT verified — please test in StarCraft: Remastered** (the engine can't launch
the game):

1. **Loads** and starts as a 2-player UMS/use-map-settings game.
2. **Alliance:** P1 and P2 are allied (shared control not required) and both
   hostile to the Zerg. If not, the Force-1 "allied" flag may need a
   `SetAllianceStatus` init trigger.
3. **Waves** spawn and actually attack-move west (computer P3 has no AI script;
   if units idle after reaching the front, add periodic re-orders or an AI
   script action).
4. **Abilities** fire when the hero stands on the beacon, and respect the ~30s
   cooldown.
5. **Win** triggers after the Torrasque dies; **lose** triggers on a commander's
   death (currently no revive — harsh by design for the MVP).
6. **Balance/timing** — wave sizes and the 15-minute boss are first-pass guesses.

Tuning any of these is just editing `build_coop.py` and re-running — the whole
map regenerates deterministically.

## Ideas for next iterations

- Hero **revive** instead of instant defeat (respawn at base on a timer).
- Commander **leveling** (unlock upgrades at score thresholds).
- A real enemy **AI script** so idle units re-engage.
- More abilities per commander; a second boss.
