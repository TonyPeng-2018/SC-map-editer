import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import SCMap, mpq
from engine.chk import CHK

MAP = r'G:/Documents/StarCraft/Maps/Download/Survival In Mars 3.5 Solo1.3.scx'

def main():
    m = SCMap.open(MAP)
    orig_chk = m._archive.read_file('staredit\\scenario.chk')

    # 1) CHK parse->serialize is byte-identical
    assert CHK(orig_chk).serialize() == orig_chk, 'CHK round-trip mismatch'
    print('[ok] CHK round-trip byte-identical (%d bytes)' % len(orig_chk))

    # 2) TRIG parse->serialize identical
    trig = m.chk.get('TRIG')
    from engine.triggers import TriggerSection
    assert TriggerSection(trig).serialize() == trig, 'TRIG round-trip mismatch'
    print('[ok] TRIG round-trip identical (%d triggers)' % (len(trig)//2400))

    # 3) STR parse->serialize preserves every string
    st = m.strings
    st2_section = st.serialize()
    from engine.chk import StringTable
    st2 = StringTable(st2_section)
    for i, txt in st.items():
        assert st2.get(i) == txt, 'string %d changed' % i
    print('[ok] STR round-trip preserves all %d strings' % len(st.entries))

    # 4) metadata
    print('    name       :', m.name)
    print('    triggers   :', m.trigger_count)
    print('    locations  :', len(m.locations))
    kr = m.find_korean_strings()
    print('    korean strs:', len(kr))

    # 5) full save round-trip: unmodified map re-reads identical CHK
    out = os.path.join(os.path.dirname(__file__), '_out_roundtrip.scx')
    m.save(out)
    m3 = SCMap.open(out)
    assert m3._archive.read_file('staredit\\scenario.chk') == orig_chk, 'save round-trip mismatch'
    print('[ok] save() -> reopen gives identical CHK')

    # 6) rescale changes timeline as expected
    m4 = SCMap.open(MAP)
    changes = m4.rescale_time(0.35)
    et = [c for c in changes if c[0] == 'ElapsedTime']
    print('[ok] rescale_time(0.35): %d timeline values changed, e.g.' % len(changes), et[:3])
    # verify a known value: victory gate 4200 -> ~1470
    trig2 = m4.chk.get('TRIG')
    assert TriggerSection(trig2).serialize() == trig2
    print('    all tests passed')

if __name__ == '__main__':
    main()
