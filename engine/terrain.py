"""Terrain buildability analysis from a map's own tile data.

StarCraft stores per-tile buildability in the tileset's CV5 files, which live in
the game's data archives (not in the map). When those aren't available we derive
a good-enough buildability map from the CHK itself: every tile a *building* sits
on is buildable by definition, so the set of tile-groups used under the map's
preplaced buildings identifies the buildable groups. Any tile whose group is in
that set is treated as buildable.

    t = Terrain.from_map(scmap)     # learns buildable groups from preplaced bldgs
    t.is_buildable(tx, ty)
    t.footprint_ok(tx, ty, w, h)    # w,h in tiles (building footprint)
    print(t.render())               # ASCII buildability map
"""
import struct

# building footprints (width, height) in tiles, keyed by unit id
FOOTPRINT = {
    106: (4, 3), 107: (3, 2), 108: (2, 2), 109: (3, 2), 110: (4, 2), 111: (4, 3),
    112: (3, 2), 113: (4, 3), 114: (4, 3), 115: (3, 2), 116: (4, 3), 117: (3, 2),
    118: (3, 2), 120: (3, 2), 122: (4, 3), 123: (3, 2), 124: (2, 2), 125: (3, 2),
    131: (3, 3), 132: (3, 3), 133: (3, 3), 142: (3, 2), 149: (4, 2),
    154: (4, 3), 155: (3, 2), 156: (2, 2), 157: (4, 2), 159: (3, 2), 160: (4, 3),
    162: (2, 2), 163: (3, 2), 164: (3, 2), 165: (3, 2), 166: (3, 2), 167: (4, 3),
    169: (4, 2), 170: (3, 2), 171: (3, 2), 172: (3, 2),
    # geyser / resources占 4x2 / 2x1 footprints for placement purposes
    188: (4, 2), 176: (2, 1), 177: (2, 1), 178: (2, 1),
}


class Terrain:
    def __init__(self, width, height, tiles, buildable_groups):
        self.w = width
        self.h = height
        self.tiles = tiles
        self.buildable = set(buildable_groups)

    @classmethod
    def from_map(cls, scmap):
        dim = scmap.chk.get('DIM')
        w, h = struct.unpack('<HH', dim[:4])
        mtxm = scmap.chk.get('MTXM')
        tiles = struct.unpack('<%dH' % (w * h), mtxm[:w * h * 2])
        groups = {}
        for u in scmap.units.list():
            if 106 <= u['uid'] <= 172:              # a building -> buildable tile
                g = tiles[(u['y'] // 32) * w + (u['x'] // 32)] >> 4
                groups[g] = groups.get(g, 0) + 1
        buildable = {g for g, c in groups.items() if c >= 1}
        return cls(w, h, tiles, buildable)

    def group(self, tx, ty):
        return self.tiles[ty * self.w + tx] >> 4

    def is_buildable(self, tx, ty):
        if not (0 <= tx < self.w and 0 <= ty < self.h):
            return False
        return self.group(tx, ty) in self.buildable

    def footprint_ok(self, cx, cy, w, h):
        """cx,cy = tile of the unit *center*; check the whole footprint buildable."""
        x0 = cx - w // 2
        y0 = cy - h // 2
        return all(self.is_buildable(x, y)
                   for x in range(x0, x0 + w) for y in range(y0, y0 + h))

    def unit_ok(self, uid, cx, cy):
        w, h = FOOTPRINT.get(uid, (1, 1))
        return self.footprint_ok(cx, cy, w, h)

    def find_spot(self, uid, cx, cy, radius=6):
        """Find the nearest tile to (cx,cy) where uid's footprint fits."""
        if self.unit_ok(uid, cx, cy):
            return cx, cy
        for r in range(1, radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if self.unit_ok(uid, cx + dx, cy + dy):
                        return cx + dx, cy + dy
        return None

    def render(self, step=2, mark=None):
        mark = mark or {}
        lines = []
        for ty in range(0, self.h, step):
            row = []
            for tx in range(0, self.w, step):
                if (tx, ty) in mark:
                    row.append(mark[(tx, ty)])
                else:
                    row.append('#' if self.is_buildable(tx, ty) else '.')
            lines.append('%3d %s' % (ty, ''.join(row)))
        return '\n'.join(lines)
