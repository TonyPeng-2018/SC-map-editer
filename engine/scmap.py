"""High-level API for reading and editing StarCraft maps.

    from engine import SCMap
    m = SCMap.open("map.scx")
    print(m.name, m.trigger_count)
    m.rescale_time(0.35)                 # 70-min map -> ~25-min map
    m.translate({33: "Creature found: Mars Lizard"})
    m.save("map_out.scx")

The object caches its editable sections (strings, triggers, units) and flushes
them back into the CHK on ``save()``.
"""
import struct

try:
    from . import mpq
    from .chk import CHK, StringTable
    from .triggers import TriggerSection, player_name
    from .units import UnitSection
except ImportError:
    import mpq
    from chk import CHK, StringTable
    from triggers import TriggerSection, player_name
    from units import UnitSection

CHK_PATH = 'staredit\\scenario.chk'

RACE = {'Zerg': 0, 'Terran': 1, 'Protoss': 2, 'Independent': 3, 'Neutral': 4,
        'UserSelectable': 5, 'Inactive': 7}
OWNER = {'Inactive': 0, 'RescuePassive': 3, 'Computer': 5, 'Human': 6, 'Neutral': 7}


class SCMap:
    def __init__(self, archive, chk):
        self._archive = archive
        self.chk = chk
        self._extra = {}
        self._strings = None
        self._strings_dirty = False
        self._triggers = None
        self._units = None

    # ---------------------------------------------------------------- open/save
    @classmethod
    def open(cls, path):
        arc = mpq.MPQArchive(path)
        raw = arc.read_file(CHK_PATH)
        if raw is None:
            raise ValueError('no scenario.chk in %r (is it a StarCraft map?)' % path)
        m = cls(arc, CHK(raw))
        for name in arc.list_files():
            if name in (CHK_PATH, '(listfile)', '(attributes)'):
                continue
            data = arc.read_file(name)
            if data is not None:
                m._extra[name] = data
        return m

    def _flush(self):
        # Only write sections that actually changed, so an unmodified open->save
        # is byte-identical. Trigger/Unit serialization is exact, so compare;
        # string-table serialization re-lays-out offsets, so use a dirty flag.
        if self._strings is not None and self._strings_dirty:
            self.chk.set_strings(self._strings)
        if self._triggers is not None:
            s = self._triggers.serialize()
            if s != (self.chk.get('TRIG') or b''):
                self.chk.set('TRIG', s)
        if self._units is not None:
            s = self._units.serialize()
            if s != (self.chk.get('UNIT') or b''):
                self.chk.set('UNIT', s)

    def save(self, path):
        self._flush()
        files = {CHK_PATH: self.chk.serialize()}
        files.update(self._extra)
        names = [n for n in files if not n.startswith('(')]
        files['(listfile)'] = ('\r\n'.join(names) + '\r\n').encode('latin1')
        return mpq.build(files, path)

    # ----------------------------------------------------------- cached sections
    @property
    def strings(self):
        if self._strings is None:
            self._strings = self.chk.strings()
        return self._strings

    @property
    def triggers(self):
        if self._triggers is None:
            payload = self.chk.get('TRIG') or b''
            self._triggers = TriggerSection(payload)
        return self._triggers

    @property
    def units(self):
        if self._units is None:
            self._units = UnitSection(self.chk.get('UNIT') or b'')
        return self._units

    # ----------------------------------------------------------------- metadata
    @property
    def name(self):
        sprp = self.chk.get('SPRP')
        if sprp and len(sprp) >= 2:
            sid = struct.unpack('<H', sprp[:2])[0]
            if sid:
                return self.strings.get(sid)
        return self.strings.get(1)

    @property
    def trigger_count(self):
        return len(self.triggers)

    @property
    def locations(self):
        return self.chk.locations()

    # ------------------------------------------------------------- string edits
    def translate(self, mapping, encoding='cp949'):
        for idx, text in mapping.items():
            self.strings.set(idx, text, encoding=encoding)
        self._strings_dirty = True
        return len(mapping)

    def add_string(self, text, encoding='cp949'):
        st = self.strings
        idx = st.count + 1
        st.set(idx, text, encoding=encoding)
        self._strings_dirty = True
        return idx

    def rescale_time(self, factor, min_seconds=1):
        return self.triggers.rescale_time(factor, min_seconds=min_seconds)

    def find_korean_strings(self):
        out = {}
        for i, text in self.strings.items():
            if any('가' <= ch <= '힣' or '㄰' <= ch <= '㆏' for ch in text):
                out[i] = text
        return out

    # ------------------------------------------------------------- player setup
    def set_player(self, player, owner=None, race=None):
        """player: 0-based index (0=Player1). owner/race by name or int."""
        if owner is not None:
            ownr = bytearray(self.chk.get('OWNR') or b'\x00' * 12)
            ownr[player] = OWNER.get(owner, owner) if not isinstance(owner, int) else owner
            self.chk.set('OWNR', bytes(ownr))
            iown = bytearray(self.chk.get('IOWN') or bytes(ownr))
            iown[player] = ownr[player]
            self.chk.set('IOWN', bytes(iown))
        if race is not None:
            side = bytearray(self.chk.get('SIDE') or b'\x00' * 12)
            side[player] = RACE.get(race, race) if not isinstance(race, int) else race
            self.chk.set('SIDE', bytes(side))

    def set_forces(self, player_force, names=None, flags=None):
        """player_force: dict {player0based: force0based(0..3)}.
        names: optional {force0based: 'Name'}. flags: optional {force0based: int}."""
        forc = bytearray(self.chk.get('FORC') or (b'\x00' * 8 + b'\x00' * 8 + b'\x00' * 4))
        forc = (forc + bytearray(20))[:20]
        for p, f in player_force.items():
            forc[p] = f
        if names:
            strids = list(struct.unpack('<4H', bytes(forc[8:16])))
            for f, nm in names.items():
                strids[f] = self.add_string(nm)
            forc[8:16] = struct.pack('<4H', *strids)
        if flags:
            for f, fl in flags.items():
                forc[16 + f] = fl & 0xFF
        self.chk.set('FORC', bytes(forc))

    # ----------------------------------------------------------------- locations
    def add_location(self, name, left, top, right, bottom, elevation=0):
        """Fill the next empty MRGN slot (pixel coords). Returns 1-based index."""
        mrgn = bytearray(self.chk.get('MRGN') or b'')
        count = len(mrgn) // 20
        anywhere = count  # last slot is 'Anywhere'
        slot = None
        for i in range(count):
            l, t, r, b, sid, el = struct.unpack('<IIIIHH', mrgn[i * 20:i * 20 + 20])
            if i == anywhere - 1:
                continue
            if l == 0 and t == 0 and r == 0 and b == 0 and sid == 0:
                slot = i
                break
        if slot is None:
            slot = count
            mrgn += bytearray(20)
        sid = self.add_string(name)
        struct.pack_into('<IIIIHH', mrgn, slot * 20, left, top, right, bottom, sid, elevation)
        self.chk.set('MRGN', bytes(mrgn))
        return slot + 1  # 1-based index used by triggers

    def add_point_location(self, name, tile_x, tile_y, radius_tiles=1):
        cx, cy = tile_x * 32 + 16, tile_y * 32 + 16
        r = radius_tiles * 32
        return self.add_location(name, cx - r, cy - r, cx + r, cy + r)

    # ------------------------------------------------------------------- tech
    def enable_all_tech(self):
        """Unlock every special ability (tech) as available + already-researched
        for all players. PTEC/PTEx are flag arrays (available/researched/uses-
        default per player+tech); filling them with 0x01 turns everything on, so
        preplaced spellcasters can cast immediately in Use-Map-Settings games."""
        for sec in ('PTEC', 'PTEx'):
            data = self.chk.get(sec)
            if data:
                self.chk.set(sec, b'\x01' * len(data))

    # ----------------------------------------------------------------- triggers
    def append_triggers(self, trig_bytes):
        payload = self.chk.get('TRIG') or b''
        self.chk.set('TRIG', payload + trig_bytes)
        self._triggers = None  # invalidate cache
        return len(trig_bytes) // 2400

    def set_triggers(self, trig_bytes):
        self.chk.set('TRIG', trig_bytes)
        self._triggers = None
