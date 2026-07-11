"""Self-contained MPQ (v0) reader/writer for StarCraft .scx/.scm maps.

Zero third-party dependencies. Supports the compression/encryption schemes
StarCraft maps actually use: PKWARE implode (via blast), zlib, bzip2, MPQ
encryption with FIX_KEY. The writer emits plain SINGLE_UNIT, uncompressed,
unencrypted blocks -- the most compatible form, readable by StarCraft, ScmDraft
and every MPQ tool.
"""
import struct, zlib

try:
    from . import blast
except ImportError:  # allow running as a loose script
    import blast

# ---------------------------------------------------------------- crypto tables
def _prepare_table():
    t = {}
    seed = 0x00100001
    for i in range(256):
        index = i
        for _ in range(5):
            seed = (seed * 125 + 3) % 0x2AAAAB
            a = (seed & 0xFFFF) << 0x10
            seed = (seed * 125 + 3) % 0x2AAAAB
            b = seed & 0xFFFF
            t[index] = a | b
            index += 0x100
    return t
_ET = _prepare_table()

_HT = {'OFFSET': 0, 'HASH_A': 0x100, 'HASH_B': 0x200, 'TABLE': 0x300}

def _hash(s, kind):
    s1, s2 = 0x7FED7FED, 0xEEEEEEEE
    for ch in s.upper().encode('latin1'):
        s1 = (_ET[_HT[kind] + ch] ^ ((s1 + s2) & 0xFFFFFFFF)) & 0xFFFFFFFF
        s2 = (ch + s1 + s2 + (s2 << 5) + 3) & 0xFFFFFFFF
    return s1

def _decrypt(data, key):
    s1, s2 = key & 0xFFFFFFFF, 0xEEEEEEEE
    n = len(data) // 4
    out = []
    for v in struct.unpack('<%dI' % n, data[:n * 4]):
        s2 = (s2 + _ET[0x400 + (s1 & 0xFF)]) & 0xFFFFFFFF
        c = (v ^ (s1 + s2)) & 0xFFFFFFFF
        out.append(c)
        s1 = ((((~s1) << 0x15) & 0xFFFFFFFF) + 0x11111111) | (s1 >> 0x0B)
        s1 &= 0xFFFFFFFF
        s2 = (c + s2 + (s2 << 5) + 3) & 0xFFFFFFFF
    return struct.pack('<%dI' % n, *out) + data[n * 4:]

def _encrypt(data, key):
    s1, s2 = key & 0xFFFFFFFF, 0xEEEEEEEE
    n = len(data) // 4
    out = []
    for v in struct.unpack('<%dI' % n, data[:n * 4]):
        s2 = (s2 + _ET[0x400 + (s1 & 0xFF)]) & 0xFFFFFFFF
        c = (v ^ (s1 + s2)) & 0xFFFFFFFF
        out.append(c)
        s1 = ((((~s1) << 0x15) & 0xFFFFFFFF) + 0x11111111) | (s1 >> 0x0B)
        s1 &= 0xFFFFFFFF
        s2 = (v + s2 + (s2 << 5) + 3) & 0xFFFFFFFF
    return struct.pack('<%dI' % n, *out) + data[n * 4:]

# ------------------------------------------------------------------- flag bits
F_IMPLODE   = 0x00000100
F_COMPRESS  = 0x00000200
F_ENCRYPTED = 0x00010000
F_FIXKEY    = 0x00020000
F_SINGLE    = 0x01000000
F_CRC       = 0x04000000
F_EXISTS    = 0x80000000

def _decompress(data):
    ctype = data[0]
    body = data[1:]
    if ctype == 0:
        return body
    if ctype & 0x02:
        return zlib.decompress(body)
    if ctype & 0x08:
        return blast.explode(body)
    if ctype & 0x10:
        import bz2
        return bz2.decompress(body)
    raise RuntimeError('unsupported MPQ compression 0x%02X' % ctype)


class MPQArchive:
    """Read files out of an existing MPQ archive."""

    def __init__(self, path_or_bytes):
        if isinstance(path_or_bytes, (bytes, bytearray)):
            self.raw = bytes(path_or_bytes)
        else:
            with open(path_or_bytes, 'rb') as f:
                self.raw = f.read()
        # A map may carry an MPQ user-data header (0x1B) before the real header.
        off = self.raw.find(b'MPQ\x1a')
        if off < 0:
            raise ValueError('not an MPQ archive')
        self.base = off
        (_magic, self.hsize, self.asize, self.fmt, self.sshift,
         htpos, btpos, self.htcount, self.btcount) = struct.unpack(
            '<4sIIHHIIII', self.raw[off:off + 32])
        self.htpos = off + htpos
        self.btpos = off + btpos
        self.ht = _decrypt(self.raw[self.htpos:self.htpos + self.htcount * 16],
                           _hash('(hash table)', 'TABLE'))
        self.bt = _decrypt(self.raw[self.btpos:self.btpos + self.btcount * 16],
                           _hash('(block table)', 'TABLE'))

    def _find_block(self, name):
        ha, hb = _hash(name, 'HASH_A'), _hash(name, 'HASH_B')
        i = _hash(name, 'OFFSET') & (self.htcount - 1)
        for _ in range(self.htcount):
            na, nb, _loc, _pl, bidx = struct.unpack('<IIHHI', self.ht[i * 16:i * 16 + 16])
            if bidx == 0xFFFFFFFF:
                return None
            if na == ha and nb == hb and bidx < self.btcount:
                return bidx
            i = (i + 1) % self.htcount
        return None

    def has_file(self, name):
        return self._find_block(name) is not None

    def read_file(self, name):
        bidx = self._find_block(name)
        if bidx is None:
            return None
        boff, bsize, fsize, flags = struct.unpack('<IIII', self.bt[bidx * 16:bidx * 16 + 16])
        boff += self.base
        data = self.raw[boff:boff + bsize]
        key = None
        if flags & F_ENCRYPTED:
            key = _hash(name.split('\\')[-1], 'TABLE')
            if flags & F_FIXKEY:
                key = ((key + (boff - self.base)) ^ fsize) & 0xFFFFFFFF
        ssz = 512 << self.sshift
        if flags & F_SINGLE:
            if key is not None:
                data = _decrypt(data, key)
            if flags & (F_COMPRESS | F_IMPLODE) and fsize > bsize:
                data = _decompress(data)
            return data[:fsize]
        nsec = (fsize + ssz - 1) // ssz
        ntab = nsec + 1 + (1 if flags & F_CRC else 0)
        tbl = data[:ntab * 4]
        if key is not None:
            tbl = _decrypt(tbl, (key - 1) & 0xFFFFFFFF)
        pos = struct.unpack('<%dI' % ntab, tbl)
        out = bytearray()
        left = fsize
        for i in range(nsec):
            sd = data[pos[i]:pos[i + 1]]
            if key is not None:
                sd = _decrypt(sd, (key + i) & 0xFFFFFFFF)
            exp = min(ssz, left)
            if flags & (F_COMPRESS | F_IMPLODE) and len(sd) < exp:
                sd = _decompress(sd)
            out += sd[:exp]
            left -= exp
        return bytes(out)

    def list_files(self):
        """Return files found via (listfile), plus always-checked well-known names."""
        names = set()
        lf = self.read_file('(listfile)')
        if lf:
            for line in lf.replace(b'\r\n', b'\n').split(b'\n'):
                line = line.strip()
                if line:
                    names.add(line.decode('latin1'))
        for wk in ('staredit\\scenario.chk', '(listfile)', '(attributes)', '(signature)'):
            if self.has_file(wk):
                names.add(wk)
        return sorted(names)


def build(files, out_path=None, sector_shift=3):
    """Build a fresh MPQ from ``files`` (dict name->bytes).

    Blocks are stored SINGLE_UNIT, uncompressed, unencrypted -- maximally
    compatible. Returns the archive bytes; also writes to ``out_path`` if given.
    """
    HDR = 32
    htcount = 16
    while htcount < len(files) * 2:
        htcount <<= 1

    blob = bytearray()
    blocks = []
    cur = HDR
    for name, content in files.items():
        content = bytes(content)
        blob += content
        blocks.append((name, cur, len(content), len(content), F_EXISTS | F_SINGLE))
        cur += len(content)

    ht = bytearray(b'\xff' * (htcount * 16))
    for idx, (name, boff, arch, fsize, flags) in enumerate(blocks):
        i = _hash(name, 'OFFSET') & (htcount - 1)
        while True:
            _na, _nb, _loc, _pl, bidx = struct.unpack('<IIHHI', ht[i * 16:i * 16 + 16])
            if bidx == 0xFFFFFFFF:
                ht[i * 16:i * 16 + 16] = struct.pack(
                    '<IIHHI', _hash(name, 'HASH_A'), _hash(name, 'HASH_B'), 0, 0, idx)
                break
            i = (i + 1) % htcount

    bt = bytearray()
    for (name, boff, arch, fsize, flags) in blocks:
        bt += struct.pack('<IIII', boff, arch, fsize, flags)

    htpos = HDR + len(blob)
    btpos = htpos + len(ht)
    ht_enc = _encrypt(bytes(ht), _hash('(hash table)', 'TABLE'))
    bt_enc = _encrypt(bytes(bt), _hash('(block table)', 'TABLE'))
    total = btpos + len(bt_enc)
    hdr = struct.pack('<4sIIHHIIII', b'MPQ\x1a', HDR, total, 0, sector_shift,
                      htpos, btpos, htcount, len(blocks))
    archive = bytes(hdr) + bytes(blob) + bytes(ht_enc) + bytes(bt_enc)
    if out_path:
        with open(out_path, 'wb') as f:
            f.write(archive)
    return archive
