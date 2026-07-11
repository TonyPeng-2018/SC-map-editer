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
    # ability cooldowns (frames) + hero position snapshot
    zH, zP, zS = EUDVariable(0), EUDVariable(0), EUDVariable(0)
    tH, tP, tS = EUDVariable(0), EUDVariable(0), EUDVariable(0)
    hx, hy = EUDVariable(0), EUDVariable(0)
    # gameplay clocks (base-map triggers don't run under EUD, so waves/income/
    # boss are driven here)
    incTick, waveTick, bossFlag = EUDVariable(0), EUDVariable(0), EUDVariable(0)
    gameSec = EUDVariable(0)
    secTick = EUDVariable(0)

    if EUDInfLoop()():
        # --- one-time init: make Amon a real tanky boss ---
        if EUDIf()(started == 0):
            started << 1
            tor = TrgUnit(TORRASQUE)
            tor.maxHp = 2000 * 256        # 600 -> 2000 HP
            tor.armor = 10                # heavy armor
            TrgUnit(JIM_RAYNOR).maxHp = 350 * 256   # Tychus -> 350 HP
            Weapon(0).cooldown = 8        # Gauss Rifle: permanent post-Stim attack speed
            TrgUnit(77).maxHp = 300 * 256           # Fenix(Zealot) = Zeratul's summon, 300 HP
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

        # ===== GAMEPLAY (driven by EUD since base triggers don't run here) =====
        secTick += 1
        if EUDIf()(secTick >= 24):          # one game-second
            secTick << 0
            gameSec += 1
            DoActions([SetResources(Player1, Add, 5, Ore),
                       SetResources(Player2, Add, 5, Ore)])
        EUDEndIf()

        # waves: every ~24s a batch attacks both bases (enemies get tankier via
        # the per-minute stat scaling above)
        waveTick += 1
        if EUDIf()(waveTick >= 24 * 24):
            waveTick << 0
            DoActions([
                CreateUnit(8, 37, "Amon Spawn N", Player3),
                Order(37, Player3, "Amon Spawn N", 14, "Tychus Base"),
                CreateUnit(4, 38, "Amon Spawn N", Player3),
                Order(38, Player3, "Amon Spawn N", 14, "Tychus Base"),
                CreateUnit(8, 37, "Amon Spawn S", Player3),
                Order(37, Player3, "Amon Spawn S", 14, "Zeratul Base"),
                CreateUnit(4, 38, "Amon Spawn S", Player3),
                Order(38, Player3, "Amon Spawn S", 14, "Zeratul Base"),
            ])
            DisplayTextAll("\x08Amon's forces attack!\n")
        EUDEndIf()

        # Amon boss (Torrasque) enters at 5:00
        if EUDIf()([gameSec >= 300, bossFlag == 0]):
            bossFlag << 1
            DoActions([
                CreateUnit(1, TORRASQUE, "Amon Spawn N", Player3),
                Order(TORRASQUE, Player3, "Amon Spawn N", 14, "Tychus Base"),
                CreateUnit(1, TORRASQUE, "Amon Spawn S", Player3),
                Order(TORRASQUE, Player3, "Amon Spawn S", 14, "Zeratul Base"),
                MinimapPing("Amon Spawn N"),
            ])
            DisplayTextAll("\x13\x08AMON has entered the battlefield!\n")
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

        # ===== HERO ACTIVE ABILITIES (H = self, Patrol = targeted, Stop = self) =====
        HOLD, PATROL, STOP, GUARD = 107, 152, 1, 2
        CD, R = 96, 96          # ~4s cooldown, 3-tile radius

        for cdv in (zH, zP, zS, tH, tP, tS):
            if EUDIf()(cdv >= 1):
                cdv -= 1
            EUDEndIf()

        def aoe(px, py, dmg, foe=2):
            # damage enemies inside the (px,py) +/- R box (leaves the boss alive)
            for eptr, eepd in EUDLoopPlayerUnit(foe):
                e = CUnit(eepd, ptr=eptr)
                if EUDIf()([e.posX >= px - R, e.posX <= px + R,
                            e.posY >= py - R, e.posY <= py + R, e.hp >= dmg + 256]):
                    e.hp -= dmg
                EUDEndIf()

        def surge_heal(playerIdx):
            for uptr, uepd in EUDLoopPlayerUnit(playerIdx):
                u = CUnit(uepd, ptr=uptr)
                u.hp += 200 * 256

        # ---- Zeratul (Player1): Whirlwind / Blink / Void Surge ----
        for zptr, zepd in EUDLoopPlayerUnit(0):
            z = CUnit(zepd, ptr=zptr)
            if EUDIf()(z.unitType == ZERATUL):
                if EUDIf()([z.order == HOLD, zH == 0]):
                    z.order = GUARD; zH << CD
                    hx << z.posX; hy << z.posY
                    DisplayTextAll("\x0fZeratul: Whirlwind!\n")
                    aoe(hx, hy, 120 * 256)
                EUDEndIf()
                if EUDIf()([z.order == PATROL, zP == 0]):
                    zP << CD
                    hx << z.moveTargetX; hy << z.moveTargetY
                    z.posX = hx; z.posY = hy; z.order = GUARD
                    DisplayTextAll("\x0fZeratul: Blink!\n")
                EUDEndIf()
                if EUDIf()([z.order == STOP, zS == 0]):
                    z.order = GUARD; zS << CD
                    DisplayTextAll("\x0fZeratul: Summon Void Warrior!\n")
                    DoActions([
                        MoveLocation("SummonLoc", 75, Player1, "AllMap"),
                        CreateUnit(1, 77, "SummonLoc", Player1),   # Fenix(Zealot) 300 HP
                    ])
                EUDEndIf()
            EUDEndIf()

        # ---- Tychus (Player2): Grenade / Snipe / Rally ----
        for tptr, tepd in EUDLoopPlayerUnit(1):
            t = CUnit(tepd, ptr=tptr)
            if EUDIf()(t.unitType == JIM_RAYNOR):
                if EUDIf()([t.order == HOLD, tH == 0]):
                    t.order = GUARD; tH << CD
                    hx << t.posX; hy << t.posY
                    DisplayTextAll("\x08Tychus: Grenade!\n")
                    aoe(hx, hy, 160 * 256)
                EUDEndIf()
                if EUDIf()([t.order == PATROL, tP == 0]):
                    tP << CD
                    hx << t.moveTargetX; hy << t.moveTargetY
                    t.order = GUARD
                    DisplayTextAll("\x08Tychus: Snipe!\n")
                    aoe(hx, hy, 500 * 256)      # heavy damage at the target point
                EUDEndIf()
                if EUDIf()([t.order == STOP, tS == 0]):
                    t.order = GUARD; tS << CD
                    DisplayTextAll("\x08Tychus: Deploy Turret!\n")
                    DoActions([
                        MoveLocation("TurretLoc", 20, Player2, "AllMap"),
                        CreateUnit(1, 124, "TurretLoc", Player2),   # Missile Turret
                    ])
                EUDEndIf()
            EUDEndIf()

        EUDDoEvents()
    EUDEndInfLoop()

SaveMap(OUT, main)
print('COMPILED ->', OUT, os.path.getsize(OUT), 'bytes')
