"""Decode / edit the TRIG (and MBRF) section.

Each trigger is exactly 2400 bytes:
    16 conditions x 20 bytes  = 320
    64 actions    x 32 bytes  = 2048
    uint32 flags + 27 exec-player bytes + 1 current-action byte = 32
Triggers keep their raw bytes; edits patch individual fields in place so
untouched triggers round-trip byte-for-byte.
"""
import struct

TRIGGER_SIZE = 2400
COND_OFF, COND_SIZE, COND_N = 0, 20, 16
ACT_OFF, ACT_SIZE, ACT_N = 320, 32, 64

CONDITIONS = {
    0: 'NoCondition', 1: 'CountdownTimer', 2: 'Command', 3: 'Bring',
    4: 'Accumulate', 5: 'Kills', 6: 'CommandTheMost', 7: 'CommandTheMostAt',
    8: 'MostKills', 9: 'HighestScore', 10: 'MostResources', 11: 'Switch',
    12: 'ElapsedTime', 13: 'Briefing', 14: 'Opponents', 15: 'Deaths',
    16: 'CommandTheLeast', 17: 'CommandTheLeastAt', 18: 'LeastKills',
    19: 'LowestScore', 20: 'LeastResources', 21: 'Score', 22: 'Always',
    23: 'Never',
}
ACTIONS = {
    0: 'NoAction', 1: 'Victory', 2: 'Defeat', 3: 'PreserveTrigger', 4: 'Wait',
    5: 'PauseGame', 6: 'UnpauseGame', 7: 'Transmission', 8: 'PlayWAV',
    9: 'DisplayText', 10: 'CenterView', 11: 'CreateUnitWithProperties',
    12: 'SetMissionObjectives', 13: 'SetSwitch', 14: 'SetCountdownTimer',
    15: 'RunAIScript', 16: 'RunAIScriptAtLocation', 17: 'LeaderboardControlAtLocation',
    18: 'LeaderboardControl', 19: 'LeaderboardResources', 20: 'LeaderboardKills',
    21: 'LeaderboardPoints', 22: 'KillUnit', 23: 'KillUnitAtLocation',
    24: 'RemoveUnit', 25: 'RemoveUnitAtLocation', 26: 'SetResources',
    27: 'SetScore', 28: 'MinimapPing', 29: 'TalkingPortrait', 30: 'MuteUnitSpeech',
    31: 'UnmuteUnitSpeech', 32: 'LeaderboardComputerPlayers', 33: 'LeaderboardGoalControl',
    34: 'LeaderboardGoalControlAtLocation', 35: 'LeaderboardGoalResources',
    36: 'LeaderboardGoalKills', 37: 'LeaderboardGoalPoints', 38: 'MoveLocation',
    39: 'MoveUnit', 40: 'LeaderboardGreed', 41: 'SetNextScenario', 42: 'SetDoodadState',
    43: 'SetInvincibility', 44: 'CreateUnit', 45: 'SetDeaths', 46: 'Order',
    47: 'Comment', 48: 'GiveUnitsToPlayer', 49: 'ModifyUnitHitPoints',
    50: 'ModifyUnitEnergy', 51: 'ModifyUnitShields', 52: 'ModifyUnitResourceAmount',
    53: 'ModifyUnitHangarCount', 54: 'PauseTimer', 55: 'UnpauseTimer', 56: 'Draw',
    57: 'SetAllianceStatus',
}
# numeric comparison (conditions)
COMPARISON = {0: 'AtLeast', 1: 'AtMost', 10: 'Exactly'}
# amount modifier (SetDeaths/SetResources/SetScore actions)
AMOUNT_MOD = {7: 'SetTo', 8: 'Add', 9: 'Subtract'}
PLAYERS = {
    0: 'Player1', 1: 'Player2', 2: 'Player3', 3: 'Player4', 4: 'Player5',
    5: 'Player6', 6: 'Player7', 7: 'Player8', 8: 'Player9', 9: 'Player10',
    10: 'Player11', 11: 'Player12', 12: 'unused', 13: 'CurrentPlayer',
    14: 'Foes', 15: 'Allies', 16: 'NeutralPlayers', 17: 'AllPlayers',
    18: 'Force1', 19: 'Force2', 20: 'Force3', 21: 'Force4',
    26: 'NonAlliedVictoryPlayers',
}


def player_name(n):
    return PLAYERS.get(n, 'Player?%d' % n)


class Condition:
    def __init__(self, buf, off):
        self.buf = buf
        self.off = off

    def _u32(self, o): return struct.unpack_from('<I', self.buf, self.off + o)[0]
    def _set_u32(self, o, v): struct.pack_into('<I', self.buf, self.off + o, v & 0xFFFFFFFF)
    def _u16(self, o): return struct.unpack_from('<H', self.buf, self.off + o)[0]
    def _u8(self, o): return self.buf[self.off + o]

    @property
    def type(self): return self._u8(15)
    @property
    def type_name(self): return CONDITIONS.get(self.type, 'Cond%d' % self.type)
    @property
    def location(self): return self._u32(0)
    @property
    def player(self): return self._u32(4)
    @property
    def amount(self): return self._u32(8)
    @amount.setter
    def amount(self, v): self._set_u32(8, v)
    @property
    def unit(self): return self._u16(12)
    @property
    def comparison(self): return self._u8(14)
    @property
    def restype(self): return self._u8(16)  # resource / score type / switch number
    @property
    def flags(self): return self._u8(17)


class Action:
    def __init__(self, buf, off):
        self.buf = buf
        self.off = off

    def _u32(self, o): return struct.unpack_from('<I', self.buf, self.off + o)[0]
    def _set_u32(self, o, v): struct.pack_into('<I', self.buf, self.off + o, v & 0xFFFFFFFF)
    def _u16(self, o): return struct.unpack_from('<H', self.buf, self.off + o)[0]
    def _u8(self, o): return self.buf[self.off + o]

    @property
    def type(self): return self._u8(26)
    @property
    def type_name(self): return ACTIONS.get(self.type, 'Act%d' % self.type)
    @property
    def location(self): return self._u32(0)
    @property
    def string_id(self): return self._u32(4)
    @property
    def wav_id(self): return self._u32(8)
    @property
    def time(self): return self._u32(12)
    @time.setter
    def time(self, v): self._set_u32(12, v)
    @property
    def player(self): return self._u32(16)
    @property
    def number(self): return self._u32(20)
    @number.setter
    def number(self, v): self._set_u32(20, v)
    @property
    def unit(self): return self._u16(24)
    @property
    def modifier(self): return self._u8(27)


class Trigger:
    def __init__(self, buf):
        self.buf = bytearray(buf)

    @property
    def conditions(self):
        for i in range(COND_N):
            c = Condition(self.buf, COND_OFF + i * COND_SIZE)
            if c.type != 0:
                yield c

    @property
    def actions(self):
        for i in range(ACT_N):
            a = Action(self.buf, ACT_OFF + i * ACT_SIZE)
            if a.type != 0:
                yield a

    @property
    def exec_players(self):
        base = ACT_OFF + ACT_N * ACT_SIZE  # 2368
        flags = struct.unpack_from('<I', self.buf, base)[0]
        players = [i for i in range(27) if self.buf[base + 4 + i]]
        return players

    def serialize(self):
        return bytes(self.buf)


class TriggerSection:
    def __init__(self, payload):
        self.triggers = [Trigger(payload[i:i + TRIGGER_SIZE])
                         for i in range(0, len(payload) - TRIGGER_SIZE + 1, TRIGGER_SIZE)]

    def serialize(self):
        return b''.join(t.serialize() for t in self.triggers)

    def __len__(self):
        return len(self.triggers)

    def __iter__(self):
        return iter(self.triggers)

    # ---------- high level edits ----------
    def rescale_time(self, factor, min_seconds=1):
        """Multiply every time-based value by ``factor`` to shorten/lengthen a map.

        Affects ElapsedTime & CountdownTimer *conditions* (seconds) and
        SetCountdownTimer *actions* (seconds). Returns a list of (kind, old, new).
        """
        changes = []
        for t in self.triggers:
            for c in t.conditions:
                if c.type in (12, 1):  # ElapsedTime, CountdownTimer
                    old = c.amount
                    if old > 0:
                        new = max(min_seconds, round(old * factor))
                        if new != old:
                            c.amount = new
                            changes.append((c.type_name, old, new))
            for a in t.actions:
                if a.type == 14:  # SetCountdownTimer (seconds in time field)
                    old = a.time
                    if old > 0:
                        new = max(min_seconds, round(old * factor))
                        if new != old:
                            a.time = new
                            changes.append(('SetCountdownTimer', old, new))
        return changes
