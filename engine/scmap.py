"""High-level API for reading and editing StarCraft maps.

    from engine import SCMap
    m = SCMap.open("map.scx")
    print(m.name, m.trigger_count)
    m.rescale_time(0.35)                 # 70-min map -> ~25-min map
    m.translate({33: "Creature found: Mars Lizard"})
    m.save("map_out.scx")
"""
import struct

try:
    from . import mpq
    from .chk import CHK
    from .triggers import TriggerSection, player_name
except ImportError:
    import mpq
    from chk import CHK
    from triggers import TriggerSection, player_name

CHK_PATH = 'staredit\\scenario.chk'


class SCMap:
    def __init__(self, archive, chk):
        self._archive = archive       # MPQArchive (source)
        self.chk = chk                # CHK object
        self._extra = {}              # other files to preserve on save

    # ---------------------------------------------------------------- open/save
    @classmethod
    def open(cls, path):
        arc = mpq.MPQArchive(path)
        raw = arc.read_file(CHK_PATH)
        if raw is None:
            raise ValueError('no scenario.chk in %r (is it a StarCraft map?)' % path)
        m = cls(arc, CHK(raw))
        # preserve any other real files (e.g. embedded WAVs) so save() keeps them
        for name in arc.list_files():
            if name in (CHK_PATH, '(listfile)', '(attributes)'):
                continue
            data = arc.read_file(name)
            if data is not None:
                m._extra[name] = data
        return m

    def save(self, path):
        files = {CHK_PATH: self.chk.serialize()}
        files.update(self._extra)
        names = [n for n in files if not n.startswith('(')]
        files['(listfile)'] = ('\r\n'.join(names) + '\r\n').encode('latin1')
        return mpq.build(files, path)

    # ----------------------------------------------------------------- metadata
    @property
    def strings(self):
        return self.chk.strings()

    @property
    def name(self):
        sprp = self.chk.get('SPRP')
        if sprp and len(sprp) >= 2:
            sid = struct.unpack('<H', sprp[:2])[0]
            if sid:
                return self.strings.get(sid)
        return self.strings.get(1)

    @property
    def triggers(self):
        payload = self.chk.get('TRIG')
        return TriggerSection(payload) if payload else TriggerSection(b'')

    @property
    def trigger_count(self):
        payload = self.chk.get('TRIG')
        return len(payload) // 2400 if payload else 0

    @property
    def locations(self):
        return self.chk.locations()

    # ------------------------------------------------------------------- edits
    def translate(self, mapping, encoding='cp949'):
        """Replace strings by index. ``mapping``: {index: new_text}."""
        st = self.strings
        for idx, text in mapping.items():
            st.set(idx, text, encoding=encoding)
        self.chk.set_strings(st)
        return len(mapping)

    def rescale_time(self, factor, min_seconds=1):
        """Scale all timeline values; writes the modified TRIG back. Returns changes."""
        ts = self.triggers
        changes = ts.rescale_time(factor, min_seconds=min_seconds)
        self.chk.set('TRIG', ts.serialize())
        return changes

    # ------------------------------------------------------------------- report
    def find_korean_strings(self):
        """Return {index: text} for strings containing Hangul (need translation)."""
        out = {}
        for i, text in self.strings.items():
            if any('가' <= ch <= '힣' or '㄰' <= ch <= '㆏' for ch in text):
                out[i] = text
        return out
