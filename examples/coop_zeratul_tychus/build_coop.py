# -*- coding: utf-8 -*-
"""Generate a 2-player SC2-style co-op map (Zeratul & Tychus vs Amon) on the
Mar Sara (Ashworld) terrain, entirely from Python via the claude-scmap engine.

    python examples/coop_zeratul_tychus/build_coop.py

Layout matches the base map's natural geography: the two commanders hold the
top-left (a Terran and a Protoss base site), Amon's forces pour in from the
right. Light macro (income + one production building each) plus hero micro, ten
escalating waves, then a boss.
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
COUNTER = 13  # Spider Mine death-count = a pure cooldown counter

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

    # ---- wipe the campaign's preplaced units, keep resources + start locations
    removed = m.units.remove_where(
        lambda u: u['uid'] not in (176, 177, 178, 188, 214))
    print('removed %d campaign units (kept resources/starts)' % removed)

    # ---- players / races / forces ----
    m.set_player(0, owner='Human', race='Protoss')   # Zeratul
    m.set_player(1, owner='Human', race='Terran')    # Tychus
    m.set_player(2, owner='Computer', race='Zerg')   # Amon
    for p in range(3, 8):
        m.set_player(p, owner='Inactive', race='Inactive')
    m.set_forces({0: 0, 1: 0, 2: 1},
                 names={0: 'Survivors', 1: "Amon's Forces"},
                 flags={0: 0x0E, 1: 0x00})

    # ---- locations (tiles). Players top-left, Amon right. ----
    L_zer   = m.add_point_location('Zeratul Base', 28, 8, 3)
    L_tyc   = m.add_point_location('Tychus Base', 16, 8, 3)
    L_front = m.add_point_location('Front Line', 46, 20, 3)
    L_s1    = m.add_point_location('Spawn North', 115, 8, 2)
    L_s2    = m.add_point_location('Spawn South', 115, 55, 2)
    L_s3    = m.add_point_location('Spawn East', 120, 30, 2)
    L_zbeac = m.add_point_location('Void Beacon', 32, 10, 1)
    L_tbeac = m.add_point_location('Drop Beacon', 20, 10, 1)
    L_strike = m.add_point_location('Strike Point', 60, 20, 3)
    L_boss  = m.add_point_location('Boss Arena', 90, 30, 4)
    SPAWNS = [L_s1, L_s2, L_s3]

    U = m.units
    # give each commander a little starting economy (minerals near base)
    for i in range(6):
        U.add(176, *T(24 + i % 3, 3 + i // 3), owner=11, resource=1500)  # near Zeratul
        U.add(176, *T(11 + i % 3, 3 + i // 3), owner=11, resource=1500)  # near Tychus

    # Zeratul (Protoss) base -- top-left
    U.add('Nexus', *T(28, 8), owner=0)
    U.add('Zeratul (Dark Templar)', *T(30, 9), owner=0)
    for i in range(4): U.add('Probe', *T(26 + i, 6), owner=0)
    U.add('Pylon', *T(29, 7), owner=0); U.add('Gateway', *T(31, 7), owner=0)
    for i in range(2): U.add('Dark Templar', *T(31 + i, 10), owner=0)
    for i in range(2): U.add('Dragoon', *T(29 + i, 11), owner=0)
    U.add('Zealot', *T(32, 11), owner=0)
    U.add('Photon Cannon', *T(34, 12), owner=0)
    U.add('Protoss Beacon', *T(32, 10), owner=0)

    # Tychus (Terran) base -- top-left
    U.add('Command Center', *T(16, 8), owner=1)
    U.add('Jim Raynor (Marine)', *T(18, 9), owner=1)  # Tychus
    for i in range(3): U.add('SCV', *T(14 + i, 6), owner=1)
    U.add('Supply Depot', *T(15, 11), owner=1); U.add('Barracks', *T(18, 7), owner=1)
    for i in range(3): U.add('Marine', *T(19 + i, 9), owner=1)
    U.add('Firebat', *T(19, 10), owner=1); U.add('Medic', *T(20, 10), owner=1)
    U.add('Bunker', *T(21, 8), owner=1)
    U.add('Terran Beacon', *T(20, 10), owner=1)

    # ---- triggers ----
    tb = TriggerBuilder()
    s_obj = m.add_string('\x04Mars Co-op vs Amon: survive 10 waves, then kill the boss.\r\n'
                         '\x04P1 Zeratul (Void Beacon) | P2 Tychus (Drop Beacon)')
    s_intro = m.add_string('\x0cMars Co-op: Zeratul & Tychus vs Amon. Hold the west!')
    tb.add([ZER], [C.always()], [
        A.set_resources(ZER, 'SetTo', 250), A.set_resources(TYC, 'SetTo', 250),
        A.set_mission_objectives(s_obj), A.display_text(s_intro), A.center_view(L_zer),
    ])
    # hyper trigger keeps recurring triggers snappy
    tb.add([ENEMY], [C.always()], [A.wait(0)] * 12 + [A.preserve()])
    # cooldown clock + income drip
    tb.add([ZER], [C.always()], [A.set_deaths(ZER, COUNTER, 'Add', 1), A.preserve()])
    tb.add([TYC], [C.always()], [A.set_deaths(TYC, COUNTER, 'Add', 1), A.preserve()])
    tb.add([ZER], [C.always()], [A.set_resources(ZER, 'Add', 3), A.preserve()])
    tb.add([TYC], [C.always()], [A.set_resources(TYC, 'Add', 3), A.preserve()])

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
        A.order(ENEMY, 'Hydralisk', L_boss, L_front, 2),
        A.set_switch(1, 'set'),
    ])

    # Zeratul ability: Void Strike (~30s cd)
    s_void = m.add_string('\x0cZeratul: Void Strike! Dark Templar deployed.')
    tb.add([ZER],
           [C.bring(ZER, 'AtLeast', 1, 'Zeratul (Dark Templar)', L_zbeac),
            C.deaths(ZER, 'AtLeast', 15, COUNTER)],
           [A.display_text(s_void), A.create_unit(ZER, 'Dark Templar', 3, L_strike),
            A.minimap_ping(L_strike), A.set_deaths(ZER, COUNTER, 'SetTo', 0), A.preserve()])

    # Tychus ability: Reinforce Drop (~30s cd)
    s_drop = m.add_string('\x0cTychus: Outlaws drop in! Reinforcements arrive.')
    tb.add([TYC],
           [C.bring(TYC, 'AtLeast', 1, 'Jim Raynor (Marine)', L_tbeac),
            C.deaths(TYC, 'AtLeast', 15, COUNTER)],
           [A.display_text(s_drop), A.create_unit(TYC, 'Marine', 4, L_tbeac),
            A.create_unit(TYC, 'Medic', 1, L_tbeac),
            A.set_deaths(TYC, COUNTER, 'SetTo', 0), A.preserve()])

    # hero revive: on death, reconstitute at base after ~12s (heroes are not lost)
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

    # win: boss (Torrasque) killed after it spawned
    s_win = m.add_string("\x0cAmon's assault is broken. Mars is safe. Victory!")
    tb.add(['Force1'],
           [C.switch(1, 'set'), C.deaths(ENEMY, 'AtLeast', 1, 'Torrasque (Ultralisk)')],
           [A.display_text(s_win), A.victory()])

    # lose: the allied force has no buildings left (unit id 231 = "Buildings")
    s_lose = m.add_string('\x08All structures destroyed. Mars is lost...')
    tb.add(['Force1'],
           [C.elapsed('AtLeast', 8), C.command('Force1', 'AtMost', 0, 231)],
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
