# Example: Survival In Mars → 25-minute English edition

Turns the Korean map **Survival In Mars 3.5 Solo 1.3** (a ~70-minute survival
map) into a ~25-minute, fully English version — demonstrating the whole
`claude-scmap` engine end to end.

## Run

```bash
python build_short_english.py
```

Edit the `SRC` / `DST` paths at the top of `build_short_english.py` to point at
your copy of the map.

Expected output:

```
translated 310 string slots (171 unique)
rescaled 223 timeline values (x0.35); latest event now ~1470 s (24.5 min)
saved -> .../Survival In Mars 25min ENG.scx
reopen korean left: 0
```

## Files

| File | What it is |
|------|-----------|
| `korean_strings.json` | The 171 unique Korean strings (with the indices that share each), exported via `cli strings --korean --json`. |
| `translations.py`     | `TRANS`: English for each unique text, keyed by first index. Leading `\x0N` colour codes and `\r\n` line breaks are preserved. |
| `build_short_english.py` | open → translate → `rescale_time(0.35)` → save → verify. |

## Decoded mechanics

| System | How it works |
|--------|--------------|
| **Oxygen** | Player's *custom score* (leaderboard "Oxygen(%)"). Starts 70, capped at 100. Refilled by carrying a robot unit to your SCV + kills; drained periodically (and faster during solar storms). |
| **Defeat** | Player force's SCV count reaches 0. |
| **Spawns** | 4 monster spawn points; unit type escalates at `ElapsedTime` thresholds; death-counters throttle spawn rate. Creature-discovery messages announce each new wave. |
| **Solar storm** | Periodic event — shelter your SCV in the Bunker or die; also drains oxygen / blinds vision. |
| **Victory** | `ElapsedTime ≥ 4200 s` **and** evacuate an SCV (scientist) to the center. `rescale_time(0.35)` rewrites 4200 → 1470 s. |

## Notes

- The original map is *not* protected — standard MPQ with PKWARE-imploded
  sectors, which the engine reads natively.
- Only `STR ` (strings) and `TRIG` (timeline) are modified; every other section
  is preserved byte-for-byte.
- Test the output in StarCraft: Remastered or Brood War before sharing.
