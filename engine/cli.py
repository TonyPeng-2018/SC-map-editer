# -*- coding: utf-8 -*-
"""Command line entry point for claude-scmap.

    python -m engine.cli info        MAP
    python -m engine.cli strings     MAP [--korean] [--json OUT]
    python -m engine.cli triggers    MAP [--grep TEXT] [--limit N]
    python -m engine.cli extract-chk MAP --out FILE
    python -m engine.cli rescale     MAP FACTOR --out MAP2
    python -m engine.cli translate   MAP MAPPING.json --out MAP2 [--encoding cp949]

The engine is pure Python with no third-party dependencies.
"""
import argparse, json, sys

try:
    from .scmap import SCMap
    from .triggers import CONDITIONS, ACTIONS, COMPARISON, AMOUNT_MOD, player_name
except ImportError:
    from scmap import SCMap
    from triggers import CONDITIONS, ACTIONS, COMPARISON, AMOUNT_MOD, player_name


def _fmt_trigger(tr, idx, strings, locs):
    out = []
    players = ','.join(player_name(p) for p in tr.exec_players)
    out.append('### Trigger %d  players=[%s]' % (idx, players))
    for c in tr.conditions:
        loc = locs.get(c.location, '') if c.location else ''
        cmp = COMPARISON.get(c.comparison, '')
        out.append('   IF %-14s player=%s %s amount=%d unit=%d res=%d loc=%s'
                   % (c.type_name, player_name(c.player), cmp, c.amount, c.unit, c.restype, loc))
    for a in tr.actions:
        s = strings.get(a.string_id).replace('\r', ' ').replace('\n', ' ') if a.string_id else ''
        if len(s) > 55:
            s = s[:55] + '...'
        loc = locs.get(a.location, '') if a.location else ''
        mod = AMOUNT_MOD.get(a.modifier, '')
        bits = ['   DO %s:' % a.type_name]
        if a.player:
            bits.append('player=%s' % player_name(a.player))
        if a.number:
            bits.append('num=%d' % a.number)
        if a.unit:
            bits.append('unit=%d' % a.unit)
        if a.time:
            bits.append('time=%d' % a.time)
        if mod:
            bits.append('mod=%s' % mod)
        if loc:
            bits.append('loc=%s' % loc)
        if s:
            bits.append('"%s"' % s)
        out.append(' '.join(bits))
    return '\n'.join(out)


def cmd_info(a):
    m = SCMap.open(a.map)
    ts = m.triggers
    times = []
    for t in ts:
        for c in t.conditions:
            if c.type in (12, 1) and c.amount:
                times.append(c.amount)
    print('name        :', m.name)
    print('triggers    :', m.trigger_count)
    print('locations   :', len(m.locations))
    print('strings      :', len(m.strings.entries))
    print('korean strs :', len(m.find_korean_strings()))
    if times:
        print('timeline    : %d..%d s  (%.1f min max)' % (min(times), max(times), max(times) / 60.0))


def cmd_strings(a):
    m = SCMap.open(a.map)
    if a.korean:
        data = m.find_korean_strings()
    else:
        data = dict(m.strings.items())
    if a.json:
        json.dump({str(k): v for k, v in data.items()},
                  open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('wrote %d strings -> %s' % (len(data), a.json))
    else:
        for i in sorted(data):
            t = data[i].replace('\r', '\\r').replace('\n', '\\n')
            print('[%d] %s' % (i, t))


def cmd_triggers(a):
    m = SCMap.open(a.map)
    strings, locs = m.strings, m.locations
    n = 0
    for idx, tr in enumerate(m.triggers):
        text = _fmt_trigger(tr, idx, strings, locs)
        if a.grep and a.grep.lower() not in text.lower():
            continue
        print(text)
        n += 1
        if a.limit and n >= a.limit:
            break


def cmd_extract_chk(a):
    m = SCMap.open(a.map)
    open(a.out, 'wb').write(m.chk.serialize())
    print('wrote CHK -> %s (%d bytes)' % (a.out, len(m.chk.serialize())))


def cmd_rescale(a):
    m = SCMap.open(a.map)
    changes = m.rescale_time(a.factor)
    m.save(a.out)
    latest = max((c[2] for c in changes), default=0)
    print('rescaled %d values x%.3f; latest event ~%d s (%.1f min) -> %s'
          % (len(changes), a.factor, latest, latest / 60.0, a.out))


def cmd_translate(a):
    m = SCMap.open(a.map)
    raw = json.load(open(a.mapping, encoding='utf-8'))
    mapping = {int(k): v for k, v in raw.items()}
    n = m.translate(mapping, encoding=a.encoding)
    m.save(a.out)
    print('translated %d strings -> %s (korean left: %d)'
          % (n, a.out, len(m.find_korean_strings())))


def main(argv=None):
    p = argparse.ArgumentParser(prog='claude-scmap')
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('info'); s.add_argument('map'); s.set_defaults(fn=cmd_info)
    s = sub.add_parser('strings'); s.add_argument('map')
    s.add_argument('--korean', action='store_true'); s.add_argument('--json')
    s.set_defaults(fn=cmd_strings)
    s = sub.add_parser('triggers'); s.add_argument('map')
    s.add_argument('--grep'); s.add_argument('--limit', type=int)
    s.set_defaults(fn=cmd_triggers)
    s = sub.add_parser('extract-chk'); s.add_argument('map'); s.add_argument('--out', required=True)
    s.set_defaults(fn=cmd_extract_chk)
    s = sub.add_parser('rescale'); s.add_argument('map'); s.add_argument('factor', type=float)
    s.add_argument('--out', required=True); s.set_defaults(fn=cmd_rescale)
    s = sub.add_parser('translate'); s.add_argument('map'); s.add_argument('mapping')
    s.add_argument('--out', required=True); s.add_argument('--encoding', default='cp949')
    s.set_defaults(fn=cmd_translate)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == '__main__':
    main()
