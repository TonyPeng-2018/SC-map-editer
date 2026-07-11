# -*- coding: utf-8 -*-
"""Generate a 2-player SC2-style co-op map (Zeratul & Tychus) on a Big Game
Hunters terrain base, entirely from Python via the claude-scmap engine.

    python examples/coop_zeratul_tychus/build_coop.py

Design: two allied commanders defend the left side of the map against escalating
Zerg waves, then kill a boss to win. Light macro (income drip + a production
building each) plus hero micro. One signature ability each via a beacon.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from engine import SCMap
from engine.triggerbuild import TriggerBuilder, C, A

BASE = r'G:/Documents/StarCraft/Maps/Download/!(8)Big Game Hunters redone.scm'
OUT = r'G:/Documents/StarCraft/Maps/Download/Mars Coop - Zeratul & Tychus.scx'

# players
ZER, TYC, ENEMY = 'Player1', 'Player2', 'Player3'
COUNTER = 13  # Spider Mine death-count used as a pure cooldown counter

# ------------------------------------------------------------------- wave table
# (time_seconds, [(unit, count_per_spawn), ...], announce)
WAVES = [
    (30,  [('Zergling', 6)], 'Wave 1 - Zerglings incoming!'),
    (95,  [('Zergling', 9)], 'Wave 2 - the swarm grows.'),
    (165, [('Hydralisk', 5)], 'Wave 3 - Hydralisks!'),
    (240, [('Hydralisk', 8)], 'Wave 4 - Hydralisk pack.'),
    (320, [('Mutalisk', 4), ('Zergling', 6)], 'Wave 5 - Mutalisks from the sky!'),
    (405, [('Hydralisk', 6), ('Lurker', 2)], 'Wave 6 - Lurkers burrowed in.'),
    (495, [('Ultralisk', 3)], 'Wave 7 - Ultralisks charging!'),
    (590, [('Hydralisk', 8), ('Mutalisk', 4)], 'Wave 8 - full assault.'),
    (690, [('Ultralisk', 4), ('Hydralisk', 6)], 'Wave 9 - hold the line!'),
    (800, [('Zergling', 12), ('Hydralisk', 8), ('Mutalisk', 5)], 'Wave 10 - the final surge.'),
]
BOSS_TIME = 900


def main():
    m = SCMap.open(BASE)

    # ---- players / races / forces ----
    m.set_player(0, owner='Human', race='Protoss')   # Zeratul
    m.set_player(1, owner='Human', race='Terran')    # Tychus
    m.set_player(2, owner='Computer', race='Zerg')   # Mars Swarm
    for p in range(3, 8):
        m.set_player(p, owner='Inactive', race='Inactive')
    m.set_forces({0: 0, 1: 0, 2: 1},
                 names={0: 'Survivors', 1: 'Mars Swarm'},
                 flags={0: 0x0E, 1: 0x00})  # Force1 = allied + allied-victory + shared vision

    # ---- locations (tile coords on the 128x128 map) ----
    L_zer   = m.add_point_location('Zeratul Base', 12, 7, 3)
    L_tyc   = m.add_point_location('Tychus Base', 10, 48, 3)
    L_front = m.add_point_location('Front Line', 16, 28, 2)
    L_s1    = m.add_point_location('Spawn North', 115, 9, 2)
    L_s2    = m.add_point_location('Spawn South', 116, 81, 2)
    L_s3    = m.add_point_location('Spawn East', 115, 45, 2)
    L_zbeac = m.add_point_location('Void Beacon', 18, 10, 1)
    L_tbeac = m.add_point_location('Drop Beacon', 15, 48, 1)
    L_strike = m.add_point_location('Strike Point', 45, 30, 3)
    L_boss  = m.add_point_location('Boss Arena', 64, 64, 4)
    SPAWNS = [L_s1, L_s2, L_s3]

    # ---- preplaced units ----
    U = m.units
    def T(tx, ty): return tx * 32 + 16, ty * 32 + 16

    # Zeratul (Protoss) base
    x, y = T(12, 7); U.add('Nexus', x, y, 0)
    U.add('Zeratul (Dark Templar)', *T(14, 8), owner=0)
    for i in range(4): U.add('Probe', *T(10 + i, 5), owner=0)
    U.add('Pylon', *T(13, 6), owner=0); U.add('Gateway', *T(15, 6), owner=0)
    for i in range(2): U.add('Dark Templar', *T(15 + i, 9), owner=0)
    for i in range(2): U.add('Dragoon', *T(13 + i, 10), owner=0)
    U.add('Zealot', *T(16, 10), owner=0)
    U.add('Photon Cannon', *T(18, 14), owner=0)
    U.add('Protoss Beacon', *T(18, 10), owner=0)

    # Tychus (Terran) base
    U.add('Command Center', *T(10, 48), owner=1)
    U.add('Jim Raynor (Marine)', *T(12, 49), owner=1)  # Tychus
    for i in range(3): U.add('SCV', *T(8 + i, 46), owner=1)
    U.add('Supply Depot', *T(9, 51), owner=1); U.add('Barracks', *T(12, 46), owner=1)
    for i in range(3): U.add('Marine', *T(13 + i, 49), owner=1)
    U.add('Firebat', *T(13, 50), owner=1); U.add('Medic', *T(14, 50), owner=1)
    U.add('Bunker', *T(15, 47), owner=1)
    U.add('Terran Beacon', *T(15, 48), owner=1)

    # ---- triggers ----
    tb = TriggerBuilder()

    # init (run once): resources, objectives, leaderboard, intro
    s_obj = m.add_string('\x04Mars Co-op: survive 10 waves, then kill the boss.\r\n'
                         '\x04P1 Zeratul (Void Beacon) | P2 Tychus (Drop Beacon)')
    s_intro = m.add_string('\x0cMars Co-op - Zeratul & Tychus. Defend the west!')
    s_lead = m.add_string('Enemies remaining')
    tb.add([ZER], [C.always()], [
        A.set_resources(ZER, 'SetTo', 250), A.set_resources(TYC, 'SetTo', 250),
        A.set_mission_objectives(s_obj), A.display_text(s_intro),
        A.center_view(L_zer),
    ])

    # hyper trigger (computer player) to keep recurring triggers snappy
    tb.add([ENEMY], [C.always()], [A.wait(0)] * 12 + [A.preserve()])

    # cooldown clock: tick each cycle for both commanders
    tb.add([ZER], [C.always()], [A.set_deaths(ZER, COUNTER, 'Add', 1), A.preserve()])
    tb.add([TYC], [C.always()], [A.set_deaths(TYC, COUNTER, 'Add', 1), A.preserve()])

    # income drip
    tb.add([ZER], [C.always()], [A.set_resources(ZER, 'Add', 3), A.preserve()])
    tb.add([TYC], [C.always()], [A.set_resources(TYC, 'Add', 3), A.preserve()])

    # waves (one-shot each: no PreserveTrigger)
    for t, comp, msg in WAVES:
        sid = m.add_string('\x13\x08' + msg)
        acts = [A.display_text(sid), A.minimap_ping(L_front)]
        for unit, cnt in comp:
            for loc in SPAWNS:
                acts.append(A.create_unit(ENEMY, unit, cnt, loc))
                acts.append(A.order(ENEMY, unit, loc, L_front, order_type=2))
        # actions cap at 64; each wave stays well under
        tb.add([ENEMY], [C.elapsed('AtLeast', t)], acts[:64])

    # boss spawn (one-shot)
    s_boss = m.add_string('\x13\x08BOSS: the Torrasque and Infested Kerrigan awaken!!')
    tb.add([ENEMY], [C.elapsed('AtLeast', BOSS_TIME)], [
        A.display_text(s_boss), A.minimap_ping(L_boss),
        A.create_unit(ENEMY, 'Torrasque (Ultralisk)', 1, L_boss),
        A.create_unit(ENEMY, 'Infested Kerrigan', 1, L_boss),
        A.create_unit(ENEMY, 'Hydralisk', 8, L_boss),
        A.order(ENEMY, 'Torrasque (Ultralisk)', L_boss, L_front, 2),
        A.order(ENEMY, 'Infested Kerrigan', L_boss, L_front, 2),
        A.order(ENEMY, 'Hydralisk', L_boss, L_front, 2),
        A.set_switch(1, 'set'),  # switch 1 = boss active
    ])

    # ---- Zeratul ability: Void Strike (30s cd) ----
    s_void = m.add_string('\x0cZeratul: Void Strike! Dark Templar deployed.')
    tb.add([ZER],
           [C.bring(ZER, 'AtLeast', 1, 'Zeratul (Dark Templar)', L_zbeac),
            C.deaths(ZER, 'AtLeast', 15, COUNTER)],
           [A.display_text(s_void),
            A.create_unit(ZER, 'Dark Templar', 3, L_strike),
            A.minimap_ping(L_strike),
            A.set_deaths(ZER, COUNTER, 'SetTo', 0), A.preserve()])

    # ---- Tychus ability: Reinforce Drop (30s cd) ----
    s_drop = m.add_string('\x0cTychus: Outlaws drop in! Reinforcements arrive.')
    tb.add([TYC],
           [C.bring(TYC, 'AtLeast', 1, 'Jim Raynor (Marine)', L_tbeac),
            C.deaths(TYC, 'AtLeast', 15, COUNTER)],
           [A.display_text(s_drop),
            A.create_unit(TYC, 'Marine', 4, L_tbeac),
            A.create_unit(TYC, 'Medic', 1, L_tbeac),
            A.set_deaths(TYC, COUNTER, 'SetTo', 0), A.preserve()])

    # ---- win: boss active and Torrasque killed ----
    s_win = m.add_string('\x0cThe swarm is broken. Mars is safe. Victory!')
    tb.add(['Force1'],
           [C.switch(1, 'set'), C.deaths(ENEMY, 'AtLeast', 1, 'Torrasque (Ultralisk)')],
           [A.display_text(s_win), A.victory()])

    # ---- lose: a commander falls ----
    s_lz = m.add_string('\x08Zeratul has fallen. The defense collapses...')
    s_lt = m.add_string('\x08Tychus has fallen. The defense collapses...')
    tb.add(['Force1'], [C.deaths(ZER, 'AtLeast', 1, 'Zeratul (Dark Templar)')],
           [A.display_text(s_lz), A.defeat()])
    tb.add(['Force1'], [C.deaths(TYC, 'AtLeast', 1, 'Jim Raynor (Marine)')],
           [A.display_text(s_lt), A.defeat()])

    # replace triggers wholesale (base map's 15 triggers are BGH melee cruft)
    m.set_triggers(tb.serialize())

    # ---- map name ----
    s_name = m.add_string('Mars Co-op: Zeratul & Tychus')
    sprp = bytearray(m.chk.get('SPRP') or b'\x00\x00\x00\x00')
    import struct
    struct.pack_into('<H', sprp, 0, s_name)
    m.chk.set('SPRP', bytes(sprp))

    m.save(OUT)
    print('built', len(tb), 'triggers,', len(U), 'units')
    print('saved ->', OUT)

    # verify
    m2 = SCMap.open(OUT)
    print('reopen name     :', m2.name)
    print('reopen triggers :', m2.trigger_count)
    print('reopen locations:', len([1 for i, n in m2.locations.items() if not n.startswith('Location')]))
    print('OWNR:', list(m2.chk.get('OWNR'))[:4], 'SIDE:', list(m2.chk.get('SIDE'))[:4])


if __name__ == '__main__':
    main()
