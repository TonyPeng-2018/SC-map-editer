"""PKWARE DCL 'explode' (blast) - Python port of Mark Adler's blast.c."""

class BitReader:
    def __init__(self, data):
        self.data = data; self.pos = 0; self.bitbuf = 0; self.bitcnt = 0
    def bits(self, need):
        val = self.bitbuf
        while self.bitcnt < need:
            if self.pos >= len(self.data):
                raise EOFError
            val |= self.data[self.pos] << self.bitcnt
            self.pos += 1; self.bitcnt += 8
        self.bitbuf = val >> need
        self.bitcnt -= need
        return val & ((1 << need) - 1)

def _construct(rep):
    length=[]
    for v in rep:
        n=(v>>4)+1; bl=v&0x0F
        length += [bl]*n
    n=len(length)
    count=[0]*16
    for l in length: count[l]+=1
    offs=[0]*16
    for i in range(1,15): offs[i+1]=offs[i]+count[i]
    symbol=[0]*n
    for sym in range(n):
        if length[sym]!=0:
            symbol[offs[length[sym]]]=sym; offs[length[sym]]+=1
    return count,symbol

def _decode(br,count,symbol):
    code=first=index=0; length=1
    while True:
        code |= br.bits(1) ^ 1          # PKWARE bits are inverted
        c=count[length]
        if code - c < first:
            return symbol[index + (code-first)]
        index+=c; first+=c; first<<=1; code<<=1; length+=1
        if length>15: raise RuntimeError("bad code")

LITLEN=[11,124,8,7,28,7,188,13,76,4,10,8,12,10,12,10,8,23,8,
9,7,6,7,8,7,6,55,8,23,24,12,11,7,9,11,12,6,7,22,5,
7,24,6,11,9,6,7,22,7,11,38,7,9,8,25,11,8,11,9,12,
8,12,5,38,12,38,12,11,15,13,8,19,11,19,11,9,29,16,31,
9,12,15,13,11,11,14,10,7,7,21,9,11,8,11,9,11,10,6,10,
7,7,9,4,8,8,8,7,9,10,10,8,9,10,10,10,9,3,8,4,3,5,
4,4,5,5,5,6,5]
LENLEN=[2,35,36,53,38,23]
DISTLEN=[2,20,53,230,247,151,248]

_lc,_ls=_construct(LITLEN)
_nc,_ns=_construct(LENLEN)
_dc,_ds=_construct(DISTLEN)

BASE=[3,2,4,5,6,7,8,9,10,12,16,24,40,72,136,264]
EXTRA=[0,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8]

def explode(data):
    br=BitReader(data)
    lit=br.bits(8)
    dictbits=br.bits(8)
    if lit>1: raise RuntimeError("bad lit flag")
    if dictbits<4 or dictbits>6: raise RuntimeError("bad dict")
    out=bytearray()
    while True:
        try:
            if br.bits(1):
                sym=_decode(br,_nc,_ns)
                length=BASE[sym]+ (br.bits(EXTRA[sym]) if EXTRA[sym] else 0)
                if length==519: break
                symd=_decode(br,_dc,_ds)
                if length==2:
                    dist=(symd<<2)+br.bits(2)+1
                else:
                    dist=(symd<<dictbits)+br.bits(dictbits)+1
                for _ in range(length):
                    out.append(out[-dist])
            else:
                c=_decode(br,_lc,_ls) if lit else br.bits(8)
                out.append(c)
        except EOFError:
            break
    return bytes(out)
