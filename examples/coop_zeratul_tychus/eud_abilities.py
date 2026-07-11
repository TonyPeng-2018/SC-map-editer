# -*- coding: utf-8 -*-
"""First real EUD abilities (TrgUnit/CUnit based, no input detection needed):
 - Amon (Torrasque) is a genuinely tanky, hard-hitting boss (real max-HP/armor).
 - enemy units gain HP + damage over time (real stat scaling).
 - Tychus (Jim Raynor) auto-heals toward his max HP (regen, not invincible).
"""
import os, shutil
from eudplib import *

SRC = r'C:/Users/tonypeng/AppData/Local/Temp/claude/G--Documents-StarCraft-Maps-Download/ad41515a-2359-4f64-9e6b-ba2c148a3379/scratchpad/coop_base.scx'
OUT = r'G:/Documents/StarCraft/Maps/Download/Mars Coop EUD.scx'

CompressPayload(True)
LoadMap(SRC)

TORRASQUE = 48
JIM_RAYNOR = 20
ZERATUL = 75
ENEMY = [37, 38, 39, 43, 44, 45, 46, 47]  # zerg wave units
# player armies (Protoss = Zeratul side, Terran = Tychus side)
PLAYER_UNITS = [61, 62, 63, 65, 66, 67, 68, 75, 86,   # protoss
                0, 1, 2, 9, 20, 28, 32, 34]           # terran

def main():
    started = EUDVariable(0)
    tick = EUDVariable(0)
    healTick = EUDVariable(0)
    buffTick = EUDVariable(0)

    if EUDInfLoop()():
        # --- one-time init: make Amon a real tanky boss ---
        if EUDIf()(started == 0):
            started << 1
            tor = TrgUnit(TORRASQUE)
            tor.maxHp = 2000 * 256        # 600 -> 2000 HP
            tor.armor = 10                # heavy armor
            TrgUnit(JIM_RAYNOR).maxHp = 350 * 256   # Tychus -> 350 HP
            # guarantee starting economy via EUD (independent of map triggers)
            DoActions([
                SetResources(Player1, SetTo, 300, Ore),
                SetResources(Player2, SetTo, 300, Ore),
            ])
            DisplayTextAll("\x07[EUD] Amon awakened as a mighty boss.\n")
        EUDEndIf()

        # --- enemy stat scaling: every ~1500 frames (~1 min) bump HP + armor ---
        tick += 1
        if EUDIf()(tick >= 1500):
            tick << 0
            for uid in ENEMY:
                u = TrgUnit(uid)
                u.maxHp += 20 * 256       # +20 HP each minute
                u.armor += 1              # +1 armor each minute
            tor2 = TrgUnit(TORRASQUE)
            tor2.maxHp += 500 * 256       # Amon keeps getting tankier
            DisplayTextAll("\x08[EUD] Amon's forces grow stronger...\n")
        EUDEndIf()

        # --- player army progression: +1 armor every ~90s (real EUD upgrade) ---
        buffTick += 1
        if EUDIf()(buffTick >= 2160):
            buffTick << 0
            for uid in PLAYER_UNITS:
                TrgUnit(uid).armor += 1
            DisplayTextAll("\x07[EUD] Your forces harden: +1 armor to all units.\n")
        EUDEndIf()

        # --- passive auto-heal: +20 HP/sec; Zeratul regens shields when HP full ---
        healTick += 1
        if EUDIf()(healTick >= 24):     # ~1 second at fastest speed
            healTick << 0
            raynorMax = TrgUnit(JIM_RAYNOR).maxHp
            for uptr, uepd in EUDLoopPlayerUnit(1):     # yields (ptr, epd); Player2 = Tychus
                u = CUnit(uepd, ptr=uptr)
                if EUDIf()(u.unitType == JIM_RAYNOR):
                    if EUDIf()(u.hp < raynorMax):
                        u.hp += 30 * 256    # +30 HP/sec
                    EUDEndIf()
                EUDEndIf()
            zerHp = TrgUnit(ZERATUL).maxHp
            zerSh = TrgUnit(ZERATUL).maxShield
            for uptr, uepd in EUDLoopPlayerUnit(0):     # Player1 = Zeratul
                u = CUnit(uepd, ptr=uptr)
                if EUDIf()(u.unitType == ZERATUL):
                    if EUDIf()(u.hp < zerHp):
                        u.hp += 20 * 256
                    EUDEndIf()
                    if EUDIf()(u.hp >= zerHp):       # HP full -> regen shields
                        if EUDIf()(u.shield < zerSh):
                            u.shield += 20 * 256
                        EUDEndIf()
                    EUDEndIf()
                EUDEndIf()
        EUDEndIf()

        EUDDoEvents()
    EUDEndInfLoop()

SaveMap(OUT, main)
print('COMPILED ->', OUT, os.path.getsize(OUT), 'bytes')
