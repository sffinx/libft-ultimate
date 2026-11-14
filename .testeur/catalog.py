"""One canonical case per (function, input, memory layout, failure policy).

The PDF 1.3 defines the contract. This catalogue is original code; upstream
testers supply scenario references, never an alternative grading contract.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import random
import re

SIGNATURES = {
    "isalpha": "int ft_isalpha(int)",
    "isdigit": "int ft_isdigit(int)",
    "isalnum": "int ft_isalnum(int)",
    "isascii": "int ft_isascii(int)",
    "isprint": "int ft_isprint(int)",
    "strlen": "size_t ft_strlen(const char *)",
    "memset": "void *ft_memset(void *, int, size_t)",
    "bzero": "void ft_bzero(void *, size_t)",
    "memcpy": "void *ft_memcpy(void *, const void *, size_t)",
    "memmove": "void *ft_memmove(void *, const void *, size_t)",
    "strlcpy": "size_t ft_strlcpy(char *, const char *, size_t)",
    "strlcat": "size_t ft_strlcat(char *, const char *, size_t)",
    "toupper": "int ft_toupper(int)",
    "tolower": "int ft_tolower(int)",
    "strchr": "char *ft_strchr(const char *, int)",
    "strrchr": "char *ft_strrchr(const char *, int)",
    "strncmp": "int ft_strncmp(const char *, const char *, size_t)",
    "memchr": "void *ft_memchr(const void *, int, size_t)",
    "memcmp": "int ft_memcmp(const void *, const void *, size_t)",
    "strnstr": "char *ft_strnstr(const char *, const char *, size_t)",
    "atoi": "int ft_atoi(const char *)",
    "calloc": "void *ft_calloc(size_t, size_t)",
    "strdup": "char *ft_strdup(const char *)",
    "substr": "char *ft_substr(const char *, unsigned int, size_t)",
    "strjoin": "char *ft_strjoin(const char *, const char *)",
    "strtrim": "char *ft_strtrim(const char *, const char *)",
    "split": "char **ft_split(const char *, char)",
    "itoa": "char *ft_itoa(int)",
    "strmapi": "char *ft_strmapi(const char *, char (*)(unsigned int, char))",
    "striteri": "void ft_striteri(char *, void (*)(unsigned int, char *))",
    "putchar_fd": "void ft_putchar_fd(char, int)",
    "putstr_fd": "void ft_putstr_fd(char *, int)",
    "putendl_fd": "void ft_putendl_fd(char *, int)",
    "putnbr_fd": "void ft_putnbr_fd(int, int)",
    "lstnew": "t_list *ft_lstnew(void *)",
    "lstadd_front": "void ft_lstadd_front(t_list **, t_list *)",
    "lstsize": "unsigned int ft_lstsize(t_list *)",
    "lstlast": "t_list *ft_lstlast(t_list *)",
    "lstadd_back": "void ft_lstadd_back(t_list **, t_list *)",
    "lstdelone": "void ft_lstdelone(t_list *, void (*)(void *))",
    "lstclear": "void ft_lstclear(t_list **, void (*)(void *))",
    "lstiter": "void ft_lstiter(t_list *, void (*)(void *))",
    "lstmap": "t_list *ft_lstmap(t_list *, void *(*)(void *), void (*)(void *))",
}
FUNCTIONS = tuple(SIGNATURES)
ALLOCATING = {"calloc", "strdup", "substr", "strjoin", "strtrim", "split",
              "itoa", "strmapi", "lstnew", "lstmap"}
SIZE_MAX = (1 << 64) - 1


@dataclass
class Case:
    fn: str
    label: str
    a: bytes = b""
    b: bytes = b""
    want: bytes = b""
    n: int = 0
    m: int = 0
    k: int = 0
    e: int = 0
    side: int = 0
    fail: int = 0

    @property
    def id(self):
        d = asdict(self)
        del d["label"]
        return self.fn + "." + hashlib.sha256(repr(d).encode()).hexdigest()[:12]


def cbytes(value):
    return '"' + ''.join('\\%03o' % b for b in value) + '"'


def preview(value):
    if isinstance(value, bytes):
        text = repr(value)[1:]
        return text if len(text) < 54 else text[:48] + '…'
    return str(value)


def scalar(fn, args):
    """Translate defined, literal inputs into a contract-derived oracle."""
    a = args[0]
    label = ', '.join(preview(x) for x in args)
    if fn in {"isalpha", "isdigit", "isalnum", "isascii", "isprint", "toupper", "tolower"}:
        if not isinstance(a, int) or (fn != 'isascii' and not -1 <= a <= 255):
            return None
        alpha = 65 <= a <= 90 or 97 <= a <= 122
        digit = 48 <= a <= 57
        e = {"isalpha": int(alpha), "isdigit": int(digit),
             "isalnum": int(alpha or digit), "isascii": int(0 <= a < 128),
             "isprint": int(32 <= a <= 126),
             "toupper": a - 32 if 97 <= a <= 122 else a,
             "tolower": a + 32 if 65 <= a <= 90 else a}[fn]
        return Case(fn, label, k=a, e=e)
    if fn in {'itoa', 'putnbr_fd', 'putchar_fd'}:
        if not isinstance(a, int) or not -(1 << 31) <= a < (1 << 31):
            return None
        return Case(fn, label, k=a, want=bytes([a & 255]) if fn == 'putchar_fd' else str(a).encode() + (b'\0' if fn == 'itoa' else b''))
    if fn == 'calloc':
        n, m = args
        if not (0 <= n <= SIZE_MAX and 0 <= m <= SIZE_MAX):
            return None
        if 0 < n * m <= SIZE_MAX and n * m > 2**20:
            return None  # Resource exhaustion is not a reproducible oracle.
        return Case(fn, label, n=n, m=m, e=int(n * m > SIZE_MAX))
    if not isinstance(a, bytes):
        return None
    s = a.split(b'\0')[0]
    common = dict(fn=fn, label=label, a=a + b'\0')
    if fn == 'strlen':
        return Case(**common, e=len(s))
    if fn == 'atoi':
        match = re.match(rb'[\x09-\x0d ]*([+-]?[0-9]+)', s)
        try:
            e = int(match[1]) if match else 0
        except ValueError:
            return None
        return Case(**common, e=e) if -(1 << 31) <= e < (1 << 31) else None
    if fn == 'strdup':
        return Case(**common, want=s + b'\0')
    if fn in {'putstr_fd', 'putendl_fd'}:
        return Case(**common, want=s + (b'\n' if fn == 'putendl_fd' else b''))
    if fn in {'strchr', 'strrchr'}:
        k = args[1]
        if not isinstance(k, int) or not -(1 << 31) <= k < (1 << 31):
            return None
        needle = bytes([k & 255])
        e = (s + b'\0').find(needle) if fn == 'strchr' else (s + b'\0').rfind(needle)
        return Case(**common, k=k, e=e)
    if fn == 'substr':
        start, length = args[1:]
        if not (0 <= start <= 2**32 - 1 and 0 <= length <= SIZE_MAX):
            return None
        return Case(**common, m=start, n=length, want=s[start:start + length] + b'\0')
    if fn == 'split':
        k = args[1]
        if not isinstance(k, int):
            return None
        words = [x for x in s.split(bytes([k & 255])) if x]
        return Case(**common, k=k & 255, e=len(words), want=b''.join(x + b'\0' for x in words))
    if fn in {'strjoin', 'strtrim', 'strncmp', 'strnstr'}:
        if not isinstance(args[1], bytes):
            return None
        b = args[1]
        t = b.split(b'\0')[0]
        common['b'] = b + b'\0'
        if fn == 'strjoin':
            return Case(**common, want=s + t + b'\0')
        if fn == 'strtrim':
            return Case(**common, want=(s.strip(t) if t else s) + b'\0')
        n = args[2]
        if not 0 <= n <= SIZE_MAX:
            return None
        if fn == 'strncmp':
            x, y = s[:n], t[:n]
            return Case(**common, n=n, e=(x > y) - (x < y))
        return Case(**common, n=n, e=s[:n].find(t))
    return None


def catalogue(seed=42):
    rows = {}
    source_rank = {}
    def add(c):
        if c:
            rows.setdefault(c.id, c)
    def sc(fn, *args):
        add(scalar(fn, args))

    for fn in list(FUNCTIONS[:5]) + ['toupper', 'tolower']:
        for value in range(-1, 256):
            sc(fn, value)
    for x in [-2**31, -129, -2, 256, 2**31 - 1]:
        sc('isascii', x)
    strings = [b'', b'a', b'42', b'abba', b'\t\n\r\v\f ', b'\x80\xffA',
               b'a\0hidden', b'aaaaabaaaaa', b'Hello, world!']
    for n in [7, 15, 16, 31, 32, 63, 64, 127, 128, 255, 256, 4095, 4096, 16384]:
        strings.append(bytes(33 + i % 94 for i in range(n)))
    for s in strings:
        for fn in ['strlen', 'strdup', 'putstr_fd', 'putendl_fd']:
            sc(fn, s)
        for fn in ['strchr', 'strrchr']:
            for k in [0, 97, 98, 255, 128, 256, 353, -1]:
                sc(fn, s, k)
    for s in strings[:9]:
        for t in strings[:9]:
            sc('strjoin', s, t)
            sc('strtrim', s, t)
            for n in sorted({0, 1, len(s), len(s) + 1, SIZE_MAX}):
                sc('strncmp', s, t, n)
                sc('strnstr', s, t, n)
        for start in sorted({0, 1, len(s), len(s) + 1, 2**32-1}):
            for n in [0, 1, 4, SIZE_MAX]:
                sc('substr', s, start, n)
        for delim in [0, 32, 97, 255]:
            sc('split', s, delim)
    for s in [b'  alpha   beta gamma  ', b'::::', b'::::one', b'one::::',
              b'one::::two::::three', b'\xffa\xffb\xff', b'word ' * 5000,
              b'a' * 16384, b'^^^1^^2a,^^^^3^^^^--h^^^^']:
        for delim in [32, 58, 255, 94]:
            sc('split', s, delim)
    for s, t in [(b'aaabcabcd', b'aabc'), (b'aaabcabcd', b'abcd'),
                 (b'aaaab', b'aaab'), (b'abababac', b'abac')]:
        for n in range(len(s) + 2):
            sc('strnstr', s, t, n)

    ints = sorted({0, -1, 1, -2**31, 2**31-1, -2**31+1, 2**31-2} |
                  {sign * (10**p + offset) for p in range(10)
                   for sign in [-1, 1] for offset in [-1, 0, 1]
                   if -(2**31) <= sign * (10**p + offset) < 2**31})
    for i in ints:
        for fn in ['itoa', 'putnbr_fd']:
            sc(fn, i)
        for prefix in [b'', b' \t\r\n\v\f', b'000' if i >= 0 else b'']:
            sc('atoi', prefix + str(i).encode() + b'!42')
    for s in [b'', b'+', b'-', b'--42', b'+-42', b'++42', b'-+42', b'0x42',
              b'0b10', b'4 2', b'- 42', b'+\n42', b'a42', b'\x8542']:
        sc('atoi', s)
    for ch in range(1, 256):
        sc('atoi', bytes([ch]) + b'42')
    for i in range(256):
        sc('putchar_fd', i)
    sc('strlen',b'X'*1_000_000)
    sc('putstr_fd',b'a'*20_000)
    for fn,args in [('putchar_fd',(0,)),('putstr_fd',(b'alpha\nbeta',)),
                    ('putendl_fd',(b'',)),('putnbr_fd',(-2**31,))]:
        for target in [1,2,17]:
            c=scalar(fn,args); c.m=target
            c.label+=f' ; fd={target}'
            add(c)
        c=scalar(fn,args); c.e=2; c.want*=2
        c.label+=' ; deux appels successifs'
        add(c)
    for n, m in [(0,0), (0,7), (7,0), (0,SIZE_MAX), (SIZE_MAX,0),
                 (1,1), (17,3), (1024,1024), (SIZE_MAX,2),
                 (SIZE_MAX//2+1,2), (SIZE_MAX//2+2,2), (SIZE_MAX,SIZE_MAX)]:
        sc('calloc', n, m)

    rng = random.Random(seed)
    for n in [0, 1, 2, 7, 15, 16, 31, 32, 63, 64, 255, 256, 4096]:
        src = bytes(rng.randrange(256) for _ in range(n))
        for side in [0, 1]:
            for offset in [0, 1, 3, 7]:
                a = b'\xa5' * (n + offset)
                for k in [0, 42, -1, 256, 511]:
                    add(Case('memset', f'n={n}, offset={offset}, c={k}', a=a,
                             n=n, m=offset, k=k, want=a[:offset]+bytes([k&255])*n, side=side))
                add(Case('bzero', f'n={n}, offset={offset}', a=a, n=n, m=offset,
                         want=a[:offset]+b'\0'*n, side=side))
                add(Case('memcpy', f'n={n}, offset={offset}', a=a, b=src, n=n,
                         m=offset, want=a[:offset]+src, side=side))
            for k in [0, 128, 255, 256, -1]:
                add(Case('memchr', f'n={n}, c={k}', a=src, n=n, k=k,
                         e=src.find(bytes([k&255])), side=side))
            for diff in sorted({-1, 0, max(0,n-1)}):
                other=bytearray(src)
                if n and diff >= 0:
                    other[diff] ^= 255
                b=bytes(other)
                add(Case('memcmp', f'n={n}, différence={diff}', a=src, b=b,
                         n=n, e=(src>b)-(src<b), side=side))
    for length in [0, 1, 7, 16, 63, 256, 4096]:
        for shift in [-17,-7,-1,0,1,7,17]:
            srcpos=max(0,-shift)
            dstpos=max(0,shift)
            a=bytes((i*37)%256 for i in range(length+abs(shift)))
            want=bytearray(a)
            want[dstpos:dstpos+length]=a[srcpos:srcpos+length]
            for side in [0,1]:
                add(Case('memmove', f'n={length}, décalage={shift}', a=a,
                         n=length, m=srcpos, k=dstpos, want=bytes(want), side=side))
    for src in strings[:12]:
        s=src.split(b'\0')[0]
        for size in sorted({0,1,2,len(s),len(s)+1,len(s)+4}):
            dest=b'\xa5'*max(size,1)
            want=(s[:size-1]+b'\0'+dest[min(len(s)+1,size):]) if size else dest
            add(Case('strlcpy', f'{preview(s)}, capacité={size}', a=dest,
                     b=src+b'\0', n=size, e=len(s), want=want))
            for initial in [b'',b'xy',b'longer']:
                raw=initial+b'\0'+b'\xa5'*max(0,size-len(initial)-1)
                d=min(len(initial),size)
                output=bytearray(raw)
                if d<size:
                    z=s[:size-d-1]+b'\0'
                    output[d:d+len(z)]=z
                add(Case('strlcat', f'{preview(initial)} + {preview(s)}, capacité={size}',
                         a=raw,b=src+b'\0',n=size,e=d+len(s),want=bytes(output)))
            raw=b'Q'*size
            add(Case('strlcat', f'destination sans NUL, capacité={size}', a=raw,
                     b=src+b'\0',n=size,e=size+len(s),want=raw))
    for s in strings[:12]:
        s=s.split(b'\0')[0]
        for fn in ['strmapi','striteri']:
            for kind in [0,1,2]:
                want=bytes((0 if kind==1 else ((v+i)%256 if kind==0 else v)) for i,v in enumerate(s))+b'\0'
                add(Case(fn, f'{preview(s)}, callback={kind}', a=s+b'\0',k=kind,want=want))
    for fn in FUNCTIONS:
        if fn.startswith('lst'):
            for n in [0,1,3,31,10000] if fn not in {'lstnew','lstdelone','lstmap'} else ([1,3] if fn=='lstdelone' else [0,1] if fn=='lstnew' else [0,1,3]):
                add(Case(fn, f'{n} élément(s)',n=n))
            if fn=='lstmap':
                for k in [1,2]:
                    add(Case(fn, f'contenu partagé ou NULL, callback={k}',n=3,k=k))
            if fn=='lstclear':
                add(Case(fn,'suppression depuis le milieu, préfixe conservé',n=3,k=1))

    # Deterministic differential samples extend edge partitions, never time-based.
    for _ in range(80):
        s=bytes(rng.randrange(1,256) for _ in range(rng.randrange(1,100)))
        t=s[rng.randrange(len(s)):]
        n=rng.randrange(len(s)+2)
        for fn in ['strncmp','strnstr']:
            sc(fn,s,t,n)
        sc('substr',s,rng.randrange(len(s)+2),n)
        sc('split',s,s[rng.randrange(len(s))])
    path=Path(__file__).with_name('corpus.json')
    if path.exists():
        for record in json.loads(path.read_text()):
            args=[bytes.fromhex(x['hex']) if isinstance(x,dict) else x for x in record['args']]
            try:
                c=scalar(record['fn'],args)
                add(c)
                if c:
                    source_rank[c.id]=0 if any(s['repo']=='Tripouille/libftTester' for s in record['sources']) else 1
            except (ValueError,TypeError,IndexError):
                raise ValueError('Corpus invalide : '+str(record)) from None

    # Failure sweeps have a different contract from normal calls, thus distinct IDs.
    choices={
        'calloc':[(3,7),(0,0)], 'strdup':[(b'abc',),(b'',)],
        'substr':[(b'abc',1,9),(b'abc',99,1)], 'strjoin':[(b'ab',b'cd')],
        'strtrim':[(b' xxx ',b' '),(b'xxx',b'x')],
        'split':[(b' a bb ccc d ',32),(b'',32)],
        'itoa':[(-2**31,),(0,)],
    }
    for fn,inputs in choices.items():
        for args in inputs:
            c=scalar(fn,args)
            c.fail=1
            c.label='échec de chaque allocation : '+c.label
            add(c)
    for fn,c in [('strmapi',Case('strmapi','échec de chaque allocation',a=b'abc\0',want=b'ace\0')),
                 ('lstnew',Case('lstnew','échec de chaque allocation',n=1)),
                 ('lstmap',Case('lstmap','échec de chaque allocation et nettoyage',n=3))]:
        c.fail=1
        add(c)
    # A leading guard is distinct from a trailing guard: catches s[-1], for
    # example reverse scans on an empty string. Only targeted cases are doubled.
    for fn,args in [('strlen',(b'',)),('strlen',(b'abc',)),
                    ('strrchr',(b'',97)),('strrchr',(b'abc',120)),
                    ('strtrim',(b'',b' ')),('strtrim',(b'xxxx',b'x')),
                    ('split',(b'::abc::',58)),('substr',(b'abc',0,1)),
                    ('atoi',(b'42',)),('strnstr',(b'aaaab',b'aaab',5))]:
        c=scalar(fn,args); c.side=1
        c.label+=' ; garde avant l’entrée'
        add(c)
    return sorted(rows.values(),key=lambda c:(FUNCTIONS.index(c.fn),source_rank.get(c.id,2),c.fail,c.id))


def write_c(cases, target):
    lines=['static const struct test_case cases[] = {']
    for c in cases:
        lines.append('{'+', '.join([
            'F_'+c.fn,cbytes(c.id.encode()),cbytes(c.label.encode()),
            cbytes(c.a),str(len(c.a)),cbytes(c.b),str(len(c.b)),
            cbytes(c.want),str(len(c.want)),str(c.n)+'ULL',str(c.m)+'ULL',
            str(c.k)+'LL',str(c.e)+'LL',str(c.side),str(c.fail)])+'},')
    lines.append('};')
    Path(target).write_text('\n'.join(lines)+'\n')


def write_api(target):
    text='#ifndef ULTIMATE_API_H\n#define ULTIMATE_API_H\n#include <stddef.h>\n'
    text+='typedef struct s_list { void *content; struct s_list *next; } t_list;\n'
    for fn,sig in SIGNATURES.items():
        text+=sig+';\n#pragma weak ft_'+fn+'\n'
    text+='enum function { '+', '.join('F_'+f for f in FUNCTIONS)+' };\n'
    text+='static const char *const names[] = {'+', '.join('"'+f+'"' for f in FUNCTIONS)+'};\n'
    text+='static int available(int f) { switch (f) {\n'
    for fn in FUNCTIONS:
        text+='case F_'+fn+': return ft_'+fn+' != NULL;\n'
    text+='} return 0; }\n#endif\n'
    text=text.replace('#endif\n','static int may_allocate(int f) { return '+
                      ' || '.join('f == F_'+f for f in sorted(ALLOCATING))+'; }\n#endif\n')
    Path(target).write_text(text)
