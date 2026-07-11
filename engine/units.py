"""StarCraft: Brood War unit IDs (units.dat order) and the UNIT section codec.

The id<->name table follows the canonical units.dat ordering. Anchors verified
against real maps and the StarEdit wiki (Marine=0, Kerrigan/Ghost=16,
Jim Raynor/Marine=20, Dark Templar Hero=74, Zeratul=75; Mineral Fields=176-178,
Vespene Geyser=188, Start Location=214).
"""
import struct

UNIT_NAMES = {
    0: "Marine", 1: "Ghost", 2: "Vulture", 3: "Goliath", 4: "Goliath Turret",
    5: "Siege Tank (Tank Mode)", 6: "Tank Turret (Tank Mode)", 7: "SCV",
    8: "Wraith", 9: "Science Vessel", 10: "Gui Montag (Firebat)", 11: "Dropship",
    12: "Battlecruiser", 13: "Spider Mine", 14: "Nuclear Missile", 15: "Civilian",
    16: "Sarah Kerrigan (Ghost)", 17: "Alan Schezar (Goliath)", 18: "Schezar Turret",
    19: "Jim Raynor (Vulture)", 20: "Jim Raynor (Marine)", 21: "Tom Kazansky (Wraith)",
    22: "Magellan (Science Vessel)", 23: "Edmund Duke (Tank)", 24: "Duke Turret (Tank)",
    25: "Edmund Duke (Siege)", 26: "Duke Turret (Siege)", 27: "Arcturus Mengsk (BC)",
    28: "Hyperion (BC)", 29: "Norad II (BC)", 30: "Siege Tank (Siege Mode)",
    31: "Tank Turret (Siege Mode)", 32: "Firebat", 33: "Scanner Sweep", 34: "Medic",
    35: "Larva", 36: "Egg", 37: "Zergling", 38: "Hydralisk", 39: "Ultralisk",
    40: "Broodling", 41: "Drone", 42: "Overlord", 43: "Mutalisk", 44: "Guardian",
    45: "Queen", 46: "Defiler", 47: "Scourge", 48: "Torrasque (Ultralisk)",
    49: "Matriarch (Queen)", 50: "Infested Terran", 51: "Infested Kerrigan",
    52: "Unclean One (Defiler)", 53: "Hunter Killer (Hydralisk)",
    54: "Devouring One (Zergling)", 55: "Kukulza (Mutalisk)", 56: "Kukulza (Guardian)",
    57: "Yggdrasill (Overlord)", 58: "Valkyrie", 59: "Cocoon", 60: "Corsair",
    61: "Dark Templar", 62: "Devourer", 63: "Dark Archon", 64: "Probe",
    65: "Zealot", 66: "Dragoon", 67: "High Templar", 68: "Archon", 69: "Shuttle",
    70: "Scout", 71: "Arbiter", 72: "Carrier", 73: "Interceptor",
    74: "Dark Templar (Hero)", 75: "Zeratul (Dark Templar)", 76: "Tassadar/Zeratul (Archon)",
    77: "Fenix (Zealot)", 78: "Fenix (Dragoon)", 79: "Tassadar (Templar)",
    80: "Mojo (Scout)", 81: "Warbringer (Reaver)", 82: "Gantrithor (Carrier)",
    83: "Reaver", 84: "Observer", 85: "Scarab", 86: "Danimoth (Arbiter)",
    87: "Aldaris (Templar)", 88: "Artanis (Scout)", 89: "Rhynadon", 90: "Bengalaas",
    91: "Cargo Ship", 92: "Mercenary Gunship", 93: "Scantid", 94: "Kakaru",
    95: "Ragnasaur", 96: "Ursadon", 97: "Lurker Egg", 98: "Raszagal",
    99: "Samir Duran (Ghost)", 100: "Alexei Stukov (Ghost)", 101: "Map Revealer (Hero)",
    102: "Gerard DuGalle (BC)", 103: "Lurker", 104: "Infested Duran",
    105: "Disruption Web", 106: "Command Center", 107: "Comsat Station",
    108: "Nuclear Silo", 109: "Supply Depot", 110: "Refinery", 111: "Barracks",
    112: "Academy", 113: "Factory", 114: "Starport", 115: "Control Tower",
    116: "Science Facility", 117: "Covert Ops", 118: "Physics Lab", 120: "Machine Shop",
    122: "Engineering Bay", 123: "Armory", 124: "Missile Turret", 125: "Bunker",
    130: "Infested Command Center", 131: "Hatchery", 132: "Lair", 133: "Hive",
    134: "Nydus Canal", 135: "Hydralisk Den", 136: "Defiler Mound", 137: "Greater Spire",
    138: "Queen's Nest", 139: "Evolution Chamber", 140: "Ultralisk Cavern", 141: "Spire",
    142: "Spawning Pool", 143: "Creep Colony", 144: "Spore Colony", 146: "Sunken Colony",
    149: "Extractor", 154: "Nexus", 155: "Robotics Facility", 156: "Pylon",
    157: "Assimilator", 159: "Observatory", 160: "Gateway", 162: "Photon Cannon",
    163: "Citadel of Adun", 164: "Cybernetics Core", 165: "Templar Archives",
    166: "Forge", 167: "Stargate", 169: "Fleet Beacon", 170: "Arbiter Tribunal",
    171: "Robotics Support Bay", 172: "Shield Battery",
    176: "Mineral Field (Type 1)", 177: "Mineral Field (Type 2)", 178: "Mineral Field (Type 3)",
    188: "Vespene Geyser", 194: "Zerg Beacon", 195: "Terran Beacon", 196: "Protoss Beacon",
    197: "Zerg Flag Beacon", 198: "Terran Flag Beacon", 199: "Protoss Flag Beacon",
    214: "Start Location", 215: "Flag", 216: "Young Chrysalis", 217: "Psi Emitter",
    218: "Data Disc", 219: "Khaydarin Crystal", 228: "Map Revealer",
    # special condition groups (usable in Command/Bring/Deaths conditions)
    229: "Any Unit", 230: "Men", 231: "Buildings", 232: "Factories",
}
# name -> id (first spelling wins; also accept a few friendly aliases)
NAME_TO_ID = {v: k for k, v in UNIT_NAMES.items()}
NAME_TO_ID.update({
    "Zeratul": 75, "Tychus": 20, "Jim Raynor": 20, "Dark Templar Hero": 74,
    "Start Loc": 214, "Mineral Field": 176, "Geyser": 188,
})


def unit_name(uid):
    return UNIT_NAMES.get(uid, "Unit%d" % uid)


def unit_id(name):
    if isinstance(name, int):
        return name
    return NAME_TO_ID[name]


UNIT_ENTRY = 36  # bytes per UNIT record

# "valid elements" flags (offset 14): which of owner/hp/shield/energy/resource/
# hangar this record specifies. Real maps use 0x0003 (owner+HP) for placed units.
VALID_OWNER = 0x0001
VALID_HP = 0x0002
VALID_SHIELD = 0x0004
VALID_ENERGY = 0x0008
VALID_RESOURCE = 0x0010
VALID_HANGAR = 0x0020

# "special properties" word (offset 12) as shipped maps write it.
SPECIAL_UNIT = 0x0018
SPECIAL_BUILDING = 0x0014

BUILDING_IDS = set(range(106, 173))


class UnitSection:
    """Reader/writer for the UNIT section (list of preplaced units)."""

    def __init__(self, payload=b""):
        self.records = [payload[i:i + UNIT_ENTRY]
                        for i in range(0, len(payload) - UNIT_ENTRY + 1, UNIT_ENTRY)]

    def serialize(self):
        return b"".join(self.records)

    def __len__(self):
        return len(self.records)

    @staticmethod
    def _decode(rec):
        serial, x, y, uid, link = struct.unpack_from('<IHHHH', rec, 0)
        owner = rec[16]
        return dict(serial=serial, x=x, y=y, uid=uid, owner=owner)

    def list(self):
        return [self._decode(r) for r in self.records]

    def remove_where(self, pred):
        """Drop records for which pred(decoded_dict) is True; returns count removed."""
        keep, removed = [], 0
        for r in self.records:
            if pred(self._decode(r)):
                removed += 1
            else:
                keep.append(r)
        self.records = keep
        return removed

    def add(self, uid, x, y, owner, hp=100, resource=0, energy=0, serial=None):
        """Append a preplaced unit. x/y are pixel coordinates. Byte layout copies
        exactly what shipped maps write, so StarCraft loads it verbatim.
        ``energy`` (0-100) lets preplaced spellcasters start charged."""
        uid = unit_id(uid)
        if serial is None:
            serial = len(self.records)
        special = SPECIAL_BUILDING if uid in BUILDING_IDS else SPECIAL_UNIT
        valid = VALID_OWNER | VALID_HP
        if resource:
            valid |= VALID_RESOURCE
        if energy:
            valid |= VALID_ENERGY
        rec = struct.pack(
            '<IHHHHHHBBBBIHHII',
            serial & 0xFFFFFFFF,  # 0  class instance serial
            x, y,                 # 4  x, 6 y (pixels)
            uid,                  # 8  unit id
            0,                    # 10 link to another building
            special,              # 12 special properties word
            valid,                # 14 valid-elements flags
            owner,                # 16 owner
            hp, 0, energy,        # 17 hp%, 18 shield%, 19 energy%
            resource,             # 20 resource amount
            0,                    # 24 units in hangar
            0,                    # 26 unit state flags
            0,                    # 28 unused
            0,                    # 32 related unit serial
        )
        assert len(rec) == UNIT_ENTRY, len(rec)
        self.records.append(rec)
        return serial
