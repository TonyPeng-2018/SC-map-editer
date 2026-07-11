"""Programmatically author StarCraft triggers (conditions + actions -> 2400 bytes).

Byte layouts and flag values are copied from real shipped maps (see the sampled
templates in the repo history), so generated triggers load in StarCraft exactly
like editor-made ones.

    from engine.triggerbuild import TriggerBuilder, C, A
    tb = TriggerBuilder()
    tb.add(players=["Player3"],
           conditions=[C.elapsed("AtLeast", 60)],
           actions=[A.create_unit("Player3", "Zergling", 6, loc=5),
                    A.preserve()])
    trig_bytes = tb.serialize()      # append to an existing TRIG payload
"""
import struct

try:
    from .units import unit_id
except ImportError:
    from units import unit_id

TRIGGER_SIZE = 2400

PLAYER_GROUP = {
    "Player1": 0, "Player2": 1, "Player3": 2, "Player4": 3, "Player5": 4,
    "Player6": 5, "Player7": 6, "Player8": 7, "Player9": 8, "Player10": 9,
    "Player11": 10, "Player12": 11, "CurrentPlayer": 13, "Foes": 14,
    "Allies": 15, "NeutralPlayers": 16, "AllPlayers": 17, "Force1": 18,
    "Force2": 19, "Force3": 20, "Force4": 21, "NonAlliedVictoryPlayers": 26,
}
COMPARISON = {"AtLeast": 0, "AtMost": 1, "Exactly": 10}
SWITCH_STATE = {"set": 2, "cleared": 3, "Set": 2, "Cleared": 3}
SWITCH_ACTION = {"set": 4, "clear": 5, "toggle": 6, "randomize": 11}
AMOUNT_MOD = {"SetTo": 7, "Add": 8, "Subtract": 9}


def _group(p):
    if isinstance(p, int):
        return p
    return PLAYER_GROUP[p]


# --------------------------------------------------------------------- Condition
def _cond(ctype, location=0, player=0, amount=0, unit=0, comparison=0,
          restype=0, flags=0):
    return struct.pack('<IIIHBBBBH', location, player, amount, unit,
                       comparison & 0xFF, ctype & 0xFF, restype & 0xFF,
                       flags & 0xFF, 0)


class C:
    @staticmethod
    def always():
        return _cond(22)

    @staticmethod
    def never():
        return _cond(23)

    @staticmethod
    def elapsed(cmp, seconds):
        return _cond(12, amount=seconds, comparison=COMPARISON[cmp])

    @staticmethod
    def countdown(cmp, seconds):
        return _cond(1, amount=seconds, comparison=COMPARISON[cmp])

    @staticmethod
    def switch(number, state):
        return _cond(11, comparison=SWITCH_STATE[state], restype=number)

    @staticmethod
    def bring(player, cmp, amount, unit, loc):
        return _cond(3, location=loc, player=_group(player), amount=amount,
                     unit=unit_id(unit), comparison=COMPARISON[cmp], flags=0x10)

    @staticmethod
    def command(player, cmp, amount, unit):
        return _cond(2, player=_group(player), amount=amount, unit=unit_id(unit),
                     comparison=COMPARISON[cmp], flags=0x10)

    @staticmethod
    def deaths(player, cmp, amount, unit):
        return _cond(15, player=_group(player), amount=amount, unit=unit_id(unit),
                     comparison=COMPARISON[cmp], flags=0x10)

    @staticmethod
    def kills(player, cmp, amount, unit):
        return _cond(5, player=_group(player), amount=amount, unit=unit_id(unit),
                     comparison=COMPARISON[cmp], flags=0x10)

    @staticmethod
    def score(player, cmp, amount, score_type=7):
        # score_type 7 = custom
        return _cond(21, player=_group(player), amount=amount,
                     comparison=COMPARISON[cmp], restype=score_type)


# ----------------------------------------------------------------------- Action
def _act(atype, location=0, string=0, wav=0, time=0, player=0, number=0,
         unit=0, modifier=0, flags=0x04):
    return struct.pack('<IIIIIIHBBBBH', location, string, wav, time, player,
                       number, unit, atype & 0xFF, modifier & 0xFF,
                       flags & 0xFF, 0, 0)


class A:
    @staticmethod
    def preserve():
        return _act(3)

    @staticmethod
    def victory():
        return _act(1)

    @staticmethod
    def defeat():
        return _act(2)

    @staticmethod
    def wait(ms):
        return _act(4, time=ms)

    @staticmethod
    def display_text(string_id):
        return _act(9, string=string_id)

    @staticmethod
    def center_view(loc):
        return _act(10, location=loc)

    @staticmethod
    def minimap_ping(loc):
        return _act(28, location=loc)

    @staticmethod
    def create_unit(player, unit, count, loc):
        return _act(44, location=loc, player=_group(player), unit=unit_id(unit),
                    modifier=count, flags=0x14)

    @staticmethod
    def kill_unit_at(player, unit, count, loc):
        # count 0 = all
        return _act(23, location=loc, player=_group(player), unit=unit_id(unit),
                    modifier=count, flags=0x14)

    @staticmethod
    def remove_unit_at(player, unit, count, loc):
        return _act(25, location=loc, player=_group(player), unit=unit_id(unit),
                    modifier=count, flags=0x14)

    @staticmethod
    def give_units(from_player, to_player, unit, count, loc):
        return _act(48, location=loc, player=_group(from_player),
                    number=_group(to_player), unit=unit_id(unit),
                    modifier=count, flags=0x14)

    @staticmethod
    def set_deaths(player, unit, mod, amount):
        return _act(45, player=_group(player), number=amount, unit=unit_id(unit),
                    modifier=AMOUNT_MOD[mod], flags=0x14)

    @staticmethod
    def set_resources(player, mod, amount, restype=0):
        # restype 0 = ore, 1 = gas
        return _act(26, player=_group(player), number=amount, unit=restype,
                    modifier=AMOUNT_MOD[mod])

    @staticmethod
    def set_score(player, mod, amount, score_type=7):
        return _act(27, player=_group(player), number=amount, unit=score_type,
                    modifier=AMOUNT_MOD[mod])

    @staticmethod
    def set_switch(number, action):
        return _act(13, number=number, modifier=SWITCH_ACTION[action])

    @staticmethod
    def set_countdown(mod, seconds):
        return _act(14, time=seconds, modifier=AMOUNT_MOD[mod])

    @staticmethod
    def run_ai_script_at(player, script, loc):
        # script is a 4-char AI script id (e.g. b"TMCu"); stored in string field
        s = struct.unpack('<I', script[:4].ljust(4, b' '))[0] if isinstance(script, bytes) else script
        return _act(16, location=loc, player=_group(player), number=s)

    @staticmethod
    def move_location(player, src_loc, dst_loc, unit=0):
        return _act(38, location=dst_loc, player=_group(player), number=src_loc,
                    unit=unit_id(unit) if unit else 0)

    @staticmethod
    def order(player, unit, src_loc, dst_loc, order_type=1):
        # order_type: 0 move, 1 patrol, 2 attack
        return _act(46, location=src_loc, player=_group(player), number=dst_loc,
                    unit=unit_id(unit), modifier=order_type, flags=0x14)

    @staticmethod
    def leaderboard_score(string_id, score_type=7):
        return _act(21, string=string_id, unit=score_type)

    @staticmethod
    def talking_portrait(unit, ms):
        return _act(29, time=ms, unit=unit_id(unit), flags=0x14)

    @staticmethod
    def set_mission_objectives(string_id):
        return _act(12, string=string_id)

    @staticmethod
    def modify_unit_hp(player, unit, percent, loc, count=0):
        # count 0 = all matching units; percent is the new HP %
        return _act(49, location=loc, player=_group(player), number=percent,
                    unit=unit_id(unit), modifier=count, flags=0x14)

    @staticmethod
    def set_invincibility(player, unit, loc, on=True):
        return _act(43, location=loc, player=_group(player), unit=unit_id(unit),
                    modifier=4 if on else 5, flags=0x14)


class TriggerBuilder:
    def __init__(self):
        self.triggers = []  # list of bytes(2400)

    def add(self, players, conditions, actions):
        conds = list(conditions)[:16]
        acts = list(actions)[:64]
        buf = bytearray(TRIGGER_SIZE)
        for i, c in enumerate(conds):
            buf[i * 20:(i + 1) * 20] = c
        for i, a in enumerate(acts):
            buf[320 + i * 32:320 + (i + 1) * 32] = a
        base = 320 + 64 * 32  # 2368
        for p in players:
            buf[base + 4 + _group(p)] = 1
        self.triggers.append(bytes(buf))
        return self

    def serialize(self):
        return b''.join(self.triggers)

    def __len__(self):
        return len(self.triggers)
