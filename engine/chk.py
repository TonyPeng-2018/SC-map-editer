"""Parse and rebuild a StarCraft CHK (scenario) file.

A CHK is a flat sequence of chunks: 4-char name, int32 length, then payload.
When a name repeats, StarCraft uses the *last* occurrence, so we keep them in
order and expose last-wins lookup. Only the sections we touch are decoded; the
rest are preserved byte-for-byte on rebuild.
"""
import struct

# Sections whose 4-char id is shorter visually but is always space-padded.
STR = 'STR '


class CHK:
    def __init__(self, data):
        self.data = bytes(data)
        self.chunks = []  # list of [name, payload_bytes]
        p = 0
        d = self.data
        while p + 8 <= len(d):
            name = d[p:p + 4].decode('latin1')
            size = struct.unpack('<i', d[p + 4:p + 8])[0]
            p += 8
            if size < 0 or p + size > len(d):
                # tolerate a truncated/oversized trailing chunk
                size = max(0, min(size, len(d) - p))
            self.chunks.append([name, d[p:p + size]])
            p += size

    # ---- section access (last-wins, matching StarCraft) ----
    def get(self, name):
        name = _pad(name)
        for n, payload in reversed(self.chunks):
            if n == name:
                return payload
        return None

    def set(self, name, payload):
        name = _pad(name)
        for chunk in reversed(self.chunks):
            if chunk[0] == name:
                chunk[1] = bytes(payload)
                return
        self.chunks.append([name, bytes(payload)])

    def serialize(self):
        out = bytearray()
        for name, payload in self.chunks:
            out += name.encode('latin1')[:4].ljust(4, b' ')
            out += struct.pack('<i', len(payload))
            out += payload
        return bytes(out)

    # ---- string table (STR ) ----
    def strings(self):
        return StringTable(self.get(STR))

    def set_strings(self, table):
        self.set(STR, table.serialize())

    # ---- locations (MRGN) ----
    def locations(self):
        mrgn = self.get('MRGN')
        strs = self.strings()
        locs = {}
        if not mrgn:
            return locs
        for i in range(len(mrgn) // 20):
            l, t, r, b, sid, elev = struct.unpack('<IIIIHH', mrgn[i * 20:i * 20 + 20])
            name = strs.get(sid) if sid else ''
            locs[i + 1] = name or ('Location %d' % (i + 1))
        return locs


def _pad(name):
    return name.encode('latin1')[:4].ljust(4, b' ').decode('latin1')


class StringTable:
    """The STR section: uint16 count, count*uint16 offsets, then C strings.

    Indices are 1-based (0 means "no string"). Byte payloads are kept raw so
    callers can decode with whatever codepage the map uses (cp949 for Korean).
    """
    def __init__(self, section):
        self.entries = {}  # index(1-based) -> raw bytes
        if not section:
            self.count = 0
            return
        self.count = struct.unpack('<H', section[:2])[0]
        offs = struct.unpack('<%dH' % self.count, section[2:2 + 2 * self.count])
        for i, o in enumerate(offs):
            if o == 0 or o >= len(section):
                continue
            end = section.find(b'\x00', o)
            if end < 0:
                end = len(section)
            self.entries[i + 1] = section[o:end]

    def get(self, index, encoding='cp949'):
        b = self.entries.get(index)
        if b is None:
            return ''
        for enc in (encoding, 'utf-8', 'latin1'):
            try:
                return b.decode(enc)
            except UnicodeDecodeError:
                continue
        return b.decode('latin1')

    def get_raw(self, index):
        return self.entries.get(index)

    def set(self, index, text, encoding='cp949'):
        if isinstance(text, str):
            text = text.encode(encoding)
        self.entries[index] = bytes(text)
        self.count = max(self.count, index)

    def items(self, encoding='cp949'):
        for i in sorted(self.entries):
            yield i, self.get(i, encoding)

    def serialize(self):
        count = self.count
        # dedup identical byte strings to save space, preserving indices
        blob = bytearray()
        blob_offsets = {}  # bytes -> offset
        offsets = [0] * (count + 1)  # index 0 unused
        header_size = 2 + 2 * count
        for idx in range(1, count + 1):
            b = self.entries.get(idx)
            if b is None:
                offsets[idx] = 0
                continue
            if b in blob_offsets:
                offsets[idx] = blob_offsets[b]
            else:
                off = header_size + len(blob)
                blob_offsets[b] = off
                offsets[idx] = off
                blob += b + b'\x00'
        out = bytearray()
        out += struct.pack('<H', count)
        for idx in range(1, count + 1):
            out += struct.pack('<H', offsets[idx])
        out += blob
        return bytes(out)
