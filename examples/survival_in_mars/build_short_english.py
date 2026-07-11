# -*- coding: utf-8 -*-
"""Build a shorter (~25 min) English edition of Survival In Mars.

    python examples/survival_in_mars/build_short_english.py

Pipeline: open -> translate Korean strings to English -> rescale timeline x0.35
-> save. Demonstrates the whole claude-scmap engine end to end.
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from engine import SCMap
from translations import TRANS

SRC = r'G:/Documents/StarCraft/Maps/Download/Survival In Mars 3.5 Solo1.3.scx'
DST = r'G:/Documents/StarCraft/Maps/Download/Survival In Mars 25min ENG.scx'
SCALE = 0.35

def main():
    groups = json.load(open(os.path.join(HERE, 'korean_strings.json'), encoding='utf-8'))
    # fan each translation out to every index that shared the Korean text
    mapping = {}
    missing = []
    for g in groups:
        first = g['idxs'][0]
        if first in TRANS:
            for idx in g['idxs']:
                mapping[idx] = TRANS[first]
        else:
            missing.append((first, g['ko'][:30]))
    if missing:
        print('WARNING: %d untranslated groups:' % len(missing))
        for f, ko in missing:
            print('   [%d] %s' % (f, ko))

    m = SCMap.open(SRC)
    n = m.translate(mapping, encoding='cp949')
    print('translated %d string slots (%d unique)' % (n, len(TRANS)))

    changes = m.rescale_time(SCALE)
    et = [c for c in changes if c[0] == 'ElapsedTime']
    vic = max((c[2] for c in changes), default=0)
    print('rescaled %d timeline values (x%.2f); latest event now ~%d s (%.1f min)'
          % (len(changes), SCALE, vic, vic / 60.0))

    m.save(DST)
    print('saved ->', DST)

    # sanity: reopen and confirm English + shortened
    m2 = SCMap.open(DST)
    print('reopen name :', m2.name)
    print('reopen korean left:', len(m2.find_korean_strings()))

if __name__ == '__main__':
    main()
