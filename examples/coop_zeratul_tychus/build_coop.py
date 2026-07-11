# -*- coding: utf-8 -*-
"""Generate a 2-player SC2-style co-op map (Zeratul & Tychus vs Amon) on the
Mar Sara (Ashworld) terrain, entirely from Python via the claude-scmap engine.

Players hold the top-left; Amon attacks from the right. Light macro + hero
squads with NATIVE spellcaster abilities (no beacons). Ten escalating waves,
then a boss. Heroes revive; you lose only when all your buildings are gone.

    python examples/coop_zeratul_tychus/build_coop.py
"""
import os, sys, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from engine import SCMap
from engine.triggerbuild import TriggerBuilder, C, A

BASE = r'G:/Documents/StarCraft/Maps/Download/Mar Sara 1-5 (2P).scm'
OUT = r'G:/Documents/StarCraft/Maps/Download/Mars Coop - Zeratul vs Amon.scx'

ZER, TYC, ENEMY = 'Player1', 'Player2', 'Player3'
NEUTRAL = 11            # resource owner
AGGRO = 13             # Spider Mine death-count = enemy re-order clock
ANYWHERE = 64          # Mar Sara's full-map location index
ANY_UNIT = 229         # special condition/order group
BUILDINGS = 231        # special "Buildings" group (for the lose check)

# waves: (time_s, [(unit, count_per_spawn)], announce). Amon = corrupted Zerg+Protoss.
WAVES = [
    (30,  [('Zergling', 6)], 'Wave 1 - Amon sends the swarm!'),
    (95,  [('Zergling', 9)], 'Wave 2 - the swarm grows.'),
    (165, [('Hydralisk', 5)], 'Wave 3 - Hydralisks!'),
    (240, [('Zealot', 5)], 'Wave 4 - corrupted Zealots.'),
    (320, [('Mutalisk', 4), ('Zergling', 6)], 'Wave 5 - Mutalisks from the sky!'),
    (405, [('Hydralisk', 6), ('Dragoon', 3)], 'Wave 6 - void artillery.'),
    (495, [('Ultralisk', 3)], 'Wave 7 - Ultralisks charging!'),
    (590, [('Dark Templar', 4), ('Hydralisk', 6)], 'Wave 8 - shadows strike.'),
    (690, [('Ultralisk', 3), ('Archon', 2)], 'Wave 9 - hold the line!'),
    (800, [('Zergling', 10), ('Hydralisk', 8), ('Mutalisk', 4)], 'Wave 10 - the final surge.'),
]
BOSS_TIME = 900


def T(tx, ty):
    return tx * 32 + 16, ty * 32 + 16


def main():
    m = SCMap.open(BASE)

    # ---- wipe ALL campaign units incl. resources; keep only start locations ----
    removed = m.units.remove_where(lambda u: u['uid'] != 214)
    print('removed %d campaign units (incl. old resources)' % removed)

    # ---- players / races / forces ----
    m.set_player(0, owner='Human', race='Protoss')   # Zeratul
    m.set_player(1, owner='Human', race='Terran')    # Tychus
    m.set_player(2, owner='Computer', race='Zerg')   # Amon
    for p in range(3, 8):
        m.set_player(p, owner='Inactive', race='Inactive')
    m.set_forces({0: 0, 1: 0, 2: 1},
                 names={0: 'Survivors', 1: "Amon's Forces"},
                 flags={0: 0x0E, 1: 0x00})

    # ---- locations (all on campaign-verified walkable tiles) ----
    L_zer   = m.add_point_location('Zeratul Base', 32, 9, 3)
    L_tyc   = m.add_point_location('Tychus Base', 12, 9, 3)
    L_front = m.add_point_location('Front Line', 40, 18, 3)   # players' doorstep
    L_s1    = m.add_point_location('Spawn North', 110, 13, 2)  # old P8 nexus area
    L_s2    = m.add_point_location('Spawn South', 110, 84, 2)  # old P6 nexus area
    L_s3    = m.add_point_location('Spawn East', 113, 33, 2)   # old P8 forge area
    L_boss  = m.add_point_location('Boss Arena', 58, 38, 4)    # old central hive
    SPAWNS = [L_s1, L_s2, L_s3]

    U = m.units

    # ---- clean economy: minerals + a geyser near each base (owner = neutral) ----
    for i in range(8):
        U.add(176, *T(4 + i, 2), owner=NEUTRAL, resource=1500)    # Tychus minerals
        U.add(176, *T(27 + i, 2), owner=NEUTRAL, resource=1500)   # Zeratul minerals
    U.add('Vespene Geyser', *T(13, 3), owner=NEUTRAL, resource=5000)
    U.add('Vespene Geyser', *T(36, 3), owner=NEUTRAL, resource=5000)

    # ---- Tychus (Terran) base, top-left, spaced buildings ----
    U.add('Command Center', *T(9, 7), owner=1)
    U.add('Barracks', *T(16, 7), owner=1)
    U.add('Supply Depot', *T(9, 12), owner=1)
    U.add('Engineering Bay', *T(15, 12), owner=1)
    U.add('Bunker', *T(22, 10), owner=1)
    U.add('Jim Raynor (Marine)', *T(12, 9), owner=1)             # Tychus
    U.add('Ghost', *T(11, 10), owner=1, energy=100)              # Lockdown
    U.add('Science Vessel', *T(10, 8), owner=1, energy=100)      # Defensive Matrix / Irradiate
    U.add('Medic', *T(13, 10), owner=1, energy=100)
    for i in range(3): U.add('Marine', *T(13 + i, 11), owner=1)
    U.add('Firebat', *T(12, 11), owner=1)
    for i in range(3): U.add('SCV', *T(6 + i, 9), owner=1)

    # ---- Zeratul (Protoss) base, top-left, spaced buildings ----
    U.add('Nexus', *T(30, 7), owner=0)
    U.add('Gateway', *T(37, 7), owner=0)
    U.add('Pylon', *T(30, 12), owner=0)
    U.add('Forge', *T(37, 12), owner=0)
    U.add('Photon Cannon', *T(34, 10), owner=0)
    U.add('Zeratul (Dark Templar)', *T(33, 9), owner=0)          # cloaked assassin
    U.add('High Templar', *T(36, 9), owner=0, energy=100)        # Psionic Storm
    U.add('Dark Archon', *T(31, 9), owner=0, energy=100)         # Maelstrom / Feedback
    for i in range(2): U.add('Dark Templar', *T(34 + i, 8), owner=0)
    for i in range(2): U.add('Dragoon', *T(31 + i, 10), owner=0)
    U.add('Zealot', *T(33, 10), owner=0)
    for i in range(3): U.add('Probe', *T(27 + i, 10), owner=0)

    # ---- triggers ----
    tb = TriggerBuilder()
    s_obj = m.add_string('\x04Mars Co-op vs Amon: survive 10 waves, then kill the boss.\r\n'
                         '\x04Heroes revive. You lose only when all buildings fall.')
    s_intro = m.add_string('\x0cMars Co-op: Zeratul & Tychus vs Amon. Hold the west!')
    tb.add([ZER], [C.always()], [
        A.set_resources(ZER, 'SetTo', 250), A.set_resources(TYC, 'SetTo', 250),
        A.set_mission_objectives(s_obj), A.display_text(s_intro), A.center_view(L_zer),
    ])
    # hyper trigger keeps recurring triggers snappy
    tb.add([ENEMY], [C.always()], [A.wait(0)] * 12 + [A.preserve()])
    # income drip
    tb.add([ZER], [C.always()], [A.set_resources(ZER, 'Add', 3), A.preserve()])
    tb.add([TYC], [C.always()], [A.set_resources(TYC, 'Add', 3), A.preserve()])

    # aggressive AI: tick a clock, and every ~15 ticks re-order ALL Amon units to
    # attack-move the front line, so they relentlessly push into the players.
    tb.add([ENEMY], [C.always()], [A.set_deaths(ENEMY, AGGRO, 'Add', 1), A.preserve()])
    tb.add([ENEMY], [C.deaths(ENEMY, 'AtLeast', 90, AGGRO)],
           [A.order(ENEMY, ANY_UNIT, ANYWHERE, L_front, order_type=2),
            A.set_deaths(ENEMY, AGGRO, 'SetTo', 0), A.preserve()])

    # waves (one-shot each)
    for t, comp, msg in WAVES:
        sid = m.add_string('\x13\x08' + msg)
        acts = [A.display_text(sid), A.minimap_ping(L_front)]
        for unit, cnt in comp:
            for loc in SPAWNS:
                acts.append(A.create_unit(ENEMY, unit, cnt, loc))
                acts.append(A.order(ENEMY, unit, loc, L_front, order_type=2))
        tb.add([ENEMY], [C.elapsed('AtLeast', t)], acts[:64])

    # boss
    s_boss = m.add_string('\x13\x08BOSS: Amon unleashes the Torrasque and Infested Kerrigan!!')
    tb.add([ENEMY], [C.elapsed('AtLeast', BOSS_TIME)], [
        A.display_text(s_boss), A.minimap_ping(L_boss),
        A.create_unit(ENEMY, 'Torrasque (Ultralisk)', 1, L_boss),
        A.create_unit(ENEMY, 'Infested Kerrigan', 1, L_boss),
        A.create_unit(ENEMY, 'Hydralisk', 8, L_boss),
        A.order(ENEMY, 'Torrasque (Ultralisk)', L_boss, L_front, 2),
        A.order(ENEMY, 'Infested Kerrigan', L_boss, L_front, 2),
        A.set_switch(1, 'set'),
    ])

    # hero revive (~12s at base)
    s_rz = m.add_string('\x0cZeratul reconstitutes from the void...')
    tb.add([ZER], [C.deaths(ZER, 'AtLeast', 1, 'Zeratul (Dark Templar)')],
           [A.display_text(s_rz), A.wait(12000),
            A.create_unit(ZER, 'Zeratul (Dark Templar)', 1, L_zer),
            A.set_deaths(ZER, 'Zeratul (Dark Templar)', 'SetTo', 0), A.preserve()])
    s_rt = m.add_string('\x0cTychus respawns at base...')
    tb.add([TYC], [C.deaths(TYC, 'AtLeast', 1, 'Jim Raynor (Marine)')],
           [A.display_text(s_rt), A.wait(12000),
            A.create_unit(TYC, 'Jim Raynor (Marine)', 1, L_tyc),
            A.set_deaths(TYC, 'Jim Raynor (Marine)', 'SetTo', 0), A.preserve()])

    # win / lose
    s_win = m.add_string("\x0cAmon's assault is broken. Mars is safe. Victory!")
    tb.add(['Force1'],
           [C.switch(1, 'set'), C.deaths(ENEMY, 'AtLeast', 1, 'Torrasque (Ultralisk)')],
           [A.display_text(s_win), A.victory()])
    s_lose = m.add_string('\x08All structures destroyed. Mars is lost...')
    tb.add(['Force1'],
           [C.elapsed('AtLeast', 8), C.command('Force1', 'AtMost', 0, BUILDINGS)],
           [A.display_text(s_lose), A.defeat()])

    m.set_triggers(tb.serialize())

    # map name
    s_name = m.add_string('Mars Co-op: Zeratul & Tychus vs Amon')
    sprp = bytearray(m.chk.get('SPRP') or b'\x00\x00\x00\x00')
    struct.pack_into('<H', sprp, 0, s_name)
    m.chk.set('SPRP', bytes(sprp))

    m.save(OUT)
    print('built %d triggers, %d units -> %s' % (len(tb), len(U), OUT))
    m2 = SCMap.open(OUT)
    print('reopen name:', m2.name, '| triggers:', m2.trigger_count,
          '| OWNR:', list(m2.chk.get('OWNR'))[:4], '| SIDE:', list(m2.chk.get('SIDE'))[:4])


if __name__ == '__main__':
    main()
