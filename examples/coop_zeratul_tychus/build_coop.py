# -*- coding: utf-8 -*-
"""Generate a 2-player SC2-style co-op map: Zeratul & Tychus vs Amon, on the
Mar Sara (Ashworld / Mars) terrain, entirely from Python via claude-scmap.

Placement is validated against a buildability map derived from the terrain
(engine.terrain), so buildings never land on cliffs. Players hold the west;
Amon attacks from the east in three escalating, timed phases.

    python examples/coop_zeratul_tychus/build_coop.py
"""
import os, sys, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from engine import SCMap
from engine.terrain import Terrain, FOOTPRINT
from engine.triggerbuild import TriggerBuilder, C, A
from engine.units import unit_id

BASE = r'G:/Documents/StarCraft/Maps/Download/Mar Sara 1-5 (2P).scm'
OUT = r'G:/Documents/StarCraft/Maps/Download/Mars Coop - Zeratul vs Amon.scx'

ZER, TYC, ENEMY = 'Player1', 'Player2', 'Player3'
NEUTRAL = 11
ANYWHERE = 64
ANY_UNIT = 229
BUILDINGS = 231
AGGRO, HEALCD, TURRETCD = 13, 33, 14   # dummy unit death-counters used as clocks
TOR = 'Torrasque (Ultralisk)'


def T(tx, ty):
    return tx * 32 + 16, ty * 32 + 16


def main():
    m = SCMap.open(BASE)
    terr = Terrain.from_map(m)

    # record valid resource tiles near each base BEFORE wiping
    tyc_min = [(u['x'] // 32, u['y'] // 32) for u in m.units.list()
               if u['uid'] in (176, 177, 178) and u['x'] // 32 < 16 and u['y'] // 32 < 16]
    zer_min = [(u['x'] // 32, u['y'] // 32) for u in m.units.list()
               if u['uid'] in (176, 177, 178) and u['x'] // 32 < 16 and u['y'] // 32 >= 64]

    m.units.remove_where(lambda u: u['uid'] != 214)
    m.enable_all_tech()

    # players / forces
    m.set_player(0, owner='Human', race='Protoss')
    m.set_player(1, owner='Human', race='Terran')
    m.set_player(2, owner='Computer', race='Zerg')
    for p in range(3, 8):
        m.set_player(p, owner='Inactive', race='Inactive')
    m.set_forces({0: 0, 1: 0, 2: 1}, names={0: 'Survivors', 1: "Amon's Forces"},
                 flags={0: 0x0E, 1: 0x00})

    U = m.units
    occ = set()

    def place_building(uid, cx, cy):
        uid = unit_id(uid)
        spot = terr.find_spot(uid, cx, cy, radius=10)
        w, h = FOOTPRINT.get(uid, (1, 1))
        tries = 0
        while spot and any((x, y) in occ for x in range(spot[0]-w//2, spot[0]-w//2+w)
                           for y in range(spot[1]-h//2, spot[1]-h//2+h)) and tries < 40:
            spot = terr.find_spot(uid, spot[0] + 2, spot[1], radius=10); tries += 1
        if not spot:
            print('  WARN no spot for unit %d near (%d,%d)' % (uid, cx, cy)); return None
        for x in range(spot[0]-w//2, spot[0]-w//2+w):
            for y in range(spot[1]-h//2, spot[1]-h//2+h):
                occ.add((x, y))
        U.add(uid, *T(*spot), owner=None if False else _owner_ctx[0])
        return spot

    _owner_ctx = [0]

    def place_unit(uid, cx, cy, owner, energy=0, air=False):
        uid = unit_id(uid)
        if air:
            spot = (cx, cy)
        else:
            spot = terr.find_spot(uid, cx, cy, radius=8) or (cx, cy)
        U.add(uid, *T(*spot), owner=owner, energy=energy)

    # ---- resources (re-added at proven-valid tiles) ----
    for tx, ty in tyc_min:
        U.add(176, *T(tx, ty), owner=NEUTRAL, resource=1500)
    for tx, ty in zer_min:
        U.add(176, *T(tx, ty), owner=NEUTRAL, resource=1500)

    # ---- Tychus (Terran) base, top-left ----
    _owner_ctx[0] = 1
    place_building(106, 8, 7)    # Command Center
    place_building(111, 14, 7)   # Barracks
    place_building(109, 5, 11)   # Supply Depot
    place_building(122, 10, 12)  # Engineering Bay
    place_building(125, 16, 10)  # Bunker
    place_building(112, 4, 9)    # Academy
    gy = terr.find_spot(188, 13, 2, 10) or (13, 2)
    U.add(188, *T(*gy), owner=NEUTRAL, resource=5000)
    place_unit(20, 8, 5, 1)                 # Tychus (Jim Raynor Marine)
    place_unit(28, 11, 4, 1, air=True)      # Hyperion (Battlecruiser) - Yamato snipe
    place_unit(2, 7, 5, 1)                  # Vulture - Spider Mine grenade
    place_unit(34, 9, 5, 1, energy=100)     # Medic - auto heal
    for i in range(3):
        place_unit(0, 6 + i, 4, 1)          # Marines
    place_unit(32, 6, 5, 1)                 # Firebat
    for i in range(3):
        place_unit(7, 4, 6 + i, 1)          # SCVs

    # ---- Zeratul (Protoss) base, bottom-left ----
    _owner_ctx[0] = 0
    place_building(154, 9, 85)   # Nexus
    place_building(160, 15, 85)  # Gateway
    place_building(156, 6, 88)   # Pylon
    place_building(166, 12, 89)  # Forge
    place_building(162, 19, 87)  # Photon Cannon
    place_building(162, 4, 82)   # Photon Cannon 2
    gz = terr.find_spot(188, 3, 85, 10) or (3, 85)
    U.add(188, *T(*gz), owner=NEUTRAL, resource=5000)
    place_unit(75, 9, 83, 0)                # Zeratul - cloaked assassin
    place_unit(86, 12, 83, 0, air=True)     # Arbiter (Danimoth) - Recall teleport
    place_unit(67, 11, 84, 0, energy=100)   # High Templar - Psi Storm = whirlwind
    for i in range(2):
        place_unit(61, 7 + i, 83, 0)        # Dark Templar
    for i in range(2):
        place_unit(66, 13 + i, 84, 0)       # Dragoon
    place_unit(65, 10, 84, 0)               # Zealot
    for i in range(3):
        place_unit(64, 6 + i, 90, 0)        # Probes

    # ---- locations ----
    L_tyc = m.add_point_location('Tychus Base', 8, 7, 4)
    L_zer = m.add_point_location('Zeratul Base', 9, 85, 4)
    L_rally = m.add_point_location('Battlefront', 55, 45, 4)
    L_s1 = m.add_point_location('Amon Spawn N', 108, 8, 3)
    L_s2 = m.add_point_location('Amon Spawn S', 100, 83, 3)
    L_s3 = m.add_point_location('Amon Spawn E', 113, 33, 3)
    L_boss = m.add_point_location('Amon Gate', 62, 40, 4)
    L_shard = m.add_point_location('Void Shard', 50, 24, 3)
    L_turret = m.add_point_location('Turret Post', 40, 40, 2)
    SPAWNS = [L_s1, L_s2, L_s3]

    # ---- triggers ----
    tb = TriggerBuilder()
    s_obj = m.add_string('\x04Zeratul & Tychus vs AMON. Survive 3 escalating phases;\r\n'
                         '\x04kill each Amon form in time. Heroes revive; lose only if all\r\n'
                         '\x04buildings fall. Win by 20:00.')
    s_intro = m.add_string('\x0cMars Co-op: Zeratul & Tychus vs Amon. Hold the west!')
    tb.add([ZER], [C.always()], [
        A.set_resources(ZER, 'SetTo', 300), A.set_resources(TYC, 'SetTo', 300),
        A.set_mission_objectives(s_obj), A.display_text(s_intro), A.center_view(L_zer),
    ])
    tb.add([ENEMY], [C.always()], [A.wait(0)] * 12 + [A.preserve()])          # hyper
    tb.add([ZER], [C.always()], [A.set_resources(ZER, 'Add', 4), A.preserve()])  # income
    tb.add([TYC], [C.always()], [A.set_resources(TYC, 'Add', 4), A.preserve()])
    tb.add([ENEMY], [C.always()], [A.set_deaths(ENEMY, AGGRO, 'Add', 1), A.preserve()])
    tb.add([TYC], [C.always()], [A.set_deaths(TYC, HEALCD, 'Add', 1),
                                 A.set_deaths(TYC, TURRETCD, 'Add', 1), A.preserve()])
    # aggressive AI: relentlessly push the battlefront
    tb.add([ENEMY], [C.deaths(ENEMY, 'AtLeast', 80, AGGRO)],
           [A.order(ENEMY, ANY_UNIT, ANYWHERE, L_rally, 2),
            A.set_deaths(ENEMY, AGGRO, 'SetTo', 0), A.preserve()])
    # Tychus auto-heal
    tb.add([TYC], [C.deaths(TYC, 'AtLeast', 45, HEALCD)],
           [A.modify_unit_hp(TYC, 20, 100, ANYWHERE),      # Jim Raynor Marine -> 100%
            A.set_deaths(TYC, HEALCD, 'SetTo', 0), A.preserve()])
    # Tychus 1-min anti-air turret
    tb.add([TYC], [C.deaths(TYC, 'AtLeast', 320, TURRETCD)],
           [A.create_unit(TYC, 124, 1, L_turret),          # Missile Turret
            A.set_deaths(TYC, TURRETCD, 'SetTo', 0), A.preserve()])

    # escalating waves (one-shot)
    WAVES = [
        (30,  [('Zergling', 6)]), (120, [('Zergling', 8), ('Hydralisk', 3)]),
        (210, [('Hydralisk', 6)]), (360, [('Mutalisk', 4), ('Zergling', 6)]),
        (480, [('Hydralisk', 6), ('Zealot', 3)]), (660, [('Ultralisk', 3)]),
        (840, [('Hydralisk', 6), ('Dragoon', 3)]), (1050, [('Ultralisk', 3), ('Mutalisk', 4)]),
    ]
    for t, comp in WAVES:
        acts = [A.minimap_ping(L_rally)]
        for unit, cnt in comp:
            for loc in SPAWNS:
                acts.append(A.create_unit(ENEMY, unit, cnt, loc))
                acts.append(A.order(ENEMY, unit, loc, L_rally, 2))
        tb.add([ENEMY], [C.elapsed('AtLeast', t)], acts[:64])

    def boss_wave(n_tor, extra, msg):
        acts = [A.display_text(msg), A.minimap_ping(L_boss)]
        acts.append(A.create_unit(ENEMY, TOR, n_tor, L_boss))
        acts.append(A.order(ENEMY, TOR, L_boss, L_rally, 2))
        for unit, cnt in extra:
            acts.append(A.create_unit(ENEMY, unit, cnt, L_boss))
            acts.append(A.order(ENEMY, unit, L_boss, L_rally, 2))
        return acts

    s_p1 = m.add_string('\x13\x08AMON - PHASE 1 has manifested! Destroy it before 10:00.')
    tb.add([ENEMY], [C.elapsed('AtLeast', 300)],
           boss_wave(1, [('Hydralisk', 6)], s_p1))
    # phase 2 gate at 10:00
    s_fail = m.add_string('\x13\x08You failed to destroy Amon in time. Mars is lost...')
    tb.add(['Force1'], [C.elapsed('AtLeast', 600), C.deaths(ENEMY, 'AtMost', 0, TOR)],
           [A.display_text(s_fail), A.defeat()])
    s_p2 = m.add_string('\x13\x08AMON evolves - PHASE 2: tougher and deadlier. Kill it by 15:00.')
    tb.add([ENEMY], [C.elapsed('AtLeast', 600), C.deaths(ENEMY, 'AtLeast', 1, TOR)],
           boss_wave(3, [('Infested Kerrigan', 1), ('Hydralisk', 8), ('Ultralisk', 2)], s_p2))
    # phase 3 gate at 15:00
    tb.add(['Force1'], [C.elapsed('AtLeast', 900), C.deaths(ENEMY, 'AtMost', 3, TOR)],
           [A.display_text(s_fail), A.defeat()])
    s_p3 = m.add_string('\x13\x08AMON - FINAL FORM! Destroy it before 20:00 to win!')
    tb.add([ENEMY], [C.elapsed('AtLeast', 900), C.deaths(ENEMY, 'AtLeast', 4, TOR)],
           boss_wave(5, [('Infested Kerrigan', 2), ('Ultralisk', 3), ('Mutalisk', 5)], s_p3))
    # final deadline 20:00
    tb.add(['Force1'], [C.elapsed('AtLeast', 1200), C.deaths(ENEMY, 'AtMost', 8, TOR)],
           [A.display_text(s_fail), A.defeat()])
    # WIN
    s_win = m.add_string('\x0cAMON is destroyed. Mars is saved. VICTORY!')
    tb.add(['Force1'], [C.deaths(ENEMY, 'AtLeast', 9, TOR)],
           [A.display_text(s_win), A.victory()])

    # hero revive (~12s)
    s_rz = m.add_string('\x0cZeratul reconstitutes from the void...')
    tb.add([ZER], [C.deaths(ZER, 'AtLeast', 1, 'Zeratul (Dark Templar)')],
           [A.display_text(s_rz), A.wait(12000),
            A.create_unit(ZER, 'Zeratul (Dark Templar)', 1, L_zer),
            A.set_deaths(ZER, 'Zeratul (Dark Templar)', 'SetTo', 0), A.preserve()])
    s_rt = m.add_string('\x0cTychus respawns at base...')
    tb.add([TYC], [C.deaths(TYC, 'AtLeast', 1, 20)],
           [A.display_text(s_rt), A.wait(12000),
            A.create_unit(TYC, 20, 1, L_tyc),
            A.set_deaths(TYC, 20, 'SetTo', 0), A.preserve()])

    # Void Shard: spawn a cloaked shard periodically; Zeratul reaching it buffs the team
    s_shard = m.add_string('\x0cA Void Shard appeared! Reach it with Zeratul (see ping).')
    for t in (240, 540, 840):
        tb.add([ENEMY], [C.elapsed('AtLeast', t)],
               [A.create_unit('Player12', 'Dark Templar', 1, L_shard),
                A.display_text(s_shard), A.minimap_ping(L_shard)])
    s_got = m.add_string('\x0cVoid Shard recovered! +200 minerals, forces healed and surging!')
    tb.add([ZER],
           [C.bring(ZER, 'AtLeast', 1, 'Zeratul (Dark Templar)', L_shard),
            C.bring('Player12', 'AtLeast', 1, 'Dark Templar', L_shard)],
           [A.remove_unit_at('Player12', 'Dark Templar', 0, L_shard),
            A.set_resources(ZER, 'Add', 200), A.set_resources(TYC, 'Add', 200),
            A.modify_unit_hp(ZER, ANY_UNIT, 100, ANYWHERE),
            A.modify_unit_hp(TYC, ANY_UNIT, 100, ANYWHERE),
            A.order(ZER, ANY_UNIT, ANYWHERE, L_rally, 2),
            A.display_text(s_got), A.preserve()])

    # lose: all buildings destroyed
    s_lose = m.add_string('\x08All structures destroyed. Mars is lost...')
    tb.add(['Force1'], [C.elapsed('AtLeast', 8), C.command('Force1', 'AtMost', 0, BUILDINGS)],
           [A.display_text(s_lose), A.defeat()])

    m.set_triggers(tb.serialize())

    s_name = m.add_string('Mars Co-op: Zeratul & Tychus vs Amon')
    sprp = bytearray(m.chk.get('SPRP') or b'\x00\x00\x00\x00')
    struct.pack_into('<H', sprp, 0, s_name)
    m.chk.set('SPRP', bytes(sprp))

    # ---- terrain self-check: every building on buildable ground ----
    bad = 0
    for u in U.list():
        if 106 <= u['uid'] <= 172:
            if not terr.unit_ok(u['uid'], u['x'] // 32, u['y'] // 32):
                bad += 1
                print('  !! building %d at (%d,%d) on bad terrain' %
                      (u['uid'], u['x'] // 32, u['y'] // 32))
    print('terrain check: %d buildings on bad ground' % bad)

    m.save(OUT)
    print('built %d triggers, %d units -> %s' % (len(tb), len(U), OUT))
    m2 = SCMap.open(OUT)
    print('reopen name:', m2.name, '| triggers:', m2.trigger_count,
          '| OWNR:', list(m2.chk.get('OWNR'))[:4])


if __name__ == '__main__':
    main()
