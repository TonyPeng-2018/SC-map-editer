# claude-scmap

**Read, understand and edit StarCraft: Brood War maps (`.scx` / `.scm`) from
natural language — a pure-Python engine plus a Claude Code skill.**

StarCraft maps are MPQ archives wrapping a binary `CHK` scenario file. All of a
custom map's logic — spawns, timers, oxygen/score systems, victory conditions —
lives in ~2400-byte *triggers* and an indexed *string table*. Editing that by
hand means a GUI like ScmDraft and a lot of clicking. `claude-scmap` makes it
scriptable, so you (or Claude) can say *"translate this Korean map to English"*
or *"make this 70-minute map 25 minutes"* and get a playable file back.

- 🐍 **Zero dependencies.** Pure Python 3.8+. No StormLib, no native DLLs.
  Includes a from-scratch PKWARE *explode* so it reads real, compressed maps.
- 🔁 **Byte-exact round-trips.** Untouched data is preserved verbatim; a rebuilt
  archive is verified readable by independent MPQ tools and StarCraft.
- 🌏 **Translation-aware.** Handles the cp949 Korean codepage and preserves
  StarCraft colour codes and string indices.
- ⏱️ **Timeline rescaling.** Scale every `ElapsedTime` / countdown value at once
  to shorten or lengthen a map while keeping its difficulty curve.
- 🤖 **Claude Code skill.** `SKILL.md` teaches Claude the inspect → confirm →
  edit → verify workflow.

## Install

```bash
git clone https://github.com/<you>/claude-scmap
cd claude-scmap
# that's it — pure Python
```

As a Claude Code skill, drop the repo into your skills directory (or point
Claude at `SKILL.md`).

## Quickstart (CLI)

```bash
python -m engine.cli info      "MyMap.scx"                 # name, triggers, timeline
python -m engine.cli strings   "MyMap.scx" --korean         # strings needing translation
python -m engine.cli triggers  "MyMap.scx" --grep Victory   # find specific logic
python -m engine.cli rescale   "MyMap.scx" 0.35 --out "Short.scx"
python -m engine.cli translate "MyMap.scx" en.json --out "English.scx"
python -m engine.cli extract-chk "MyMap.scx" --out scenario.chk
```

## Quickstart (API)

```python
from engine import SCMap

m = SCMap.open("MyMap.scx")
print(m.name, m.trigger_count, len(m.locations))

# understand
for t in m.triggers:
    for a in t.actions:
        if a.type_name == "CreateUnit":
            ...  # inspect spawns

# edit
m.rescale_time(0.35)                    # 70 min -> ~25 min, curve preserved
m.translate({33: "Creature discovered: Mars Lizard"})  # index -> text
m.save("MyMap_out.scx")
```

## How it works

```
.scx / .scm  (MPQ archive)
    └─ staredit\scenario.chk   (CHK: flat list of named sections)
          ├─ STR    string table  (indexed, cp949/utf-8)   → engine/chk.py
          ├─ TRIG   triggers       (2400 bytes each)         → engine/triggers.py
          ├─ MRGN   locations
          └─ UNIT / UNIx / UPGx / … (units, upgrades, …)
```

| Module | Responsibility |
|--------|----------------|
| `engine/mpq.py`   | MPQ read/write (encryption, zlib/bzip2), pure-Python. Writer emits maximally-compatible uncompressed single-unit blocks. |
| `engine/blast.py` | PKWARE DCL *explode* (from-scratch port of Mark Adler's `blast.c`) so compressed maps read. |
| `engine/chk.py`   | CHK section parse/rebuild + the `STR ` string table (index-preserving, dedup on write). |
| `engine/triggers.py` | Decode/edit `TRIG`; in-place field edits keep untouched triggers byte-identical. `rescale_time()`. |
| `engine/scmap.py` | High-level `SCMap`: `open`, `translate`, `rescale_time`, `find_korean_strings`, `save`. |
| `engine/cli.py`   | `python -m engine.cli …` |

## Worked example: *Survival In Mars*

`examples/survival_in_mars/` turns a 70-minute Korean survival map into a
25-minute English one:

```bash
python examples/survival_in_mars/build_short_english.py
# translated 310 string slots (171 unique)
# rescaled 223 timeline values (x0.35); latest event now ~1470 s (24.5 min)
# reopen korean left: 0
```

The map's decoded mechanics (documented in the example):

- **Oxygen** = the player's *custom score* (leaderboard "Oxygen(%)"), starts 70,
  capped at 100; refilled by carrying a robot unit + kills, drained periodically.
- **Defeat** when the player force's SCV count hits 0.
- **Spawns** escalate by unit type at `ElapsedTime` thresholds from 4 monster
  spawn points; death-counters throttle spawn rate.
- **Victory** at `ElapsedTime ≥ 4200 s` by evacuating an SCV to the center — the
  value `rescale_time(0.35)` rewrites to `1470 s`.

## Roadmap

- Optional **StormLib** fallback backend, auto-used only for exotic/protected
  maps our pure-Python reader can't handle (keeps zero-install as default).
- Richer CHK section models (units, upgrades, forces) for full editing.
- **Phase 2 — SC2-style co-op** map generator (e.g. Zeratul / Tychus commanders)
  built on the trigger-generation engine.

## Credits & references

- CHK / trigger / MPQ formats: the StarEdit Network wiki.
- PKWARE explode: Mark Adler's `blast.c`.

## License

MIT — see [LICENSE](LICENSE).
