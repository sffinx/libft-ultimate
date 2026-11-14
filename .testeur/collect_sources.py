#!/usr/bin/env python3
"""Development-only: audit already downloaded sources; never executes them.

Extract only complete literal calls that can be interpreted unambiguously.
Variable-based suites remain documented as scenario references, not falsely
advertised as verbatim imported tests. All exclusions remain in the audit.
"""
import ast
from collections import Counter
import hashlib
import json
import operator
from pathlib import Path
import re
import sys
from catalog import scalar, FUNCTIONS, SIZE_MAX

ARITY={name:1 for name in ('isalpha isdigit isalnum isascii isprint toupper '
                          'tolower strlen atoi strdup itoa').split()}
ARITY.update({name:2 for name in 'strchr strrchr strjoin strtrim split calloc'.split()})
ARITY.update({name:3 for name in 'strncmp strnstr substr'.split()})
TOKEN=re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*[\s\S]*?\*/|//[^\n]*')

def arguments(text, start):
    parts=[]; begin=start; level=1; i=start
    while i<len(text):
        m=TOKEN.match(text,i)
        if m: i=m.end(); continue
        ch=text[i]
        if ch=='(': level+=1
        if ch==')':
            level-=1
            if level==0:
                return parts+[text[begin:i].strip()],i+1
        if ch==',' and level==1:
            parts.append(text[begin:i].strip()); begin=i+1
        i+=1
    raise ValueError('unclosed call')

def literal(expr, size=False):
    expr=re.sub(r'/\*[\s\S]*?\*/|//[^\n]*','',expr).strip()
    expr=re.sub(r'^\((?:const )?(?:void|char|size_t|unsigned int|int)(?:\s*\*)?\)\s*','',expr)
    if re.fullmatch(r'(?:"(?:\\.|[^"\\])*"\s*)+',expr):
        chunks=re.findall(r'"(?:\\.|[^"\\])*"',expr)
        chunks=[x.replace('\\e','\\x1b').replace('\\?','?') for x in chunks]
        return b''.join(ast.literal_eval('b'+x) for x in chunks)
    if re.fullmatch(r"'(?:\\.|[^'\\])*'",expr):
        b=ast.literal_eval('b'+expr)
        if len(b)==1: return b[0]
        raise ValueError('multichar')
    expr=re.sub(r'(?<=\d)[uUlL]+\b','',expr)
    constants={'INT_MAX':2**31-1,'INT_MIN':-2**31,'UINT_MAX':2**32-1,
               'SIZE_MAX':SIZE_MAX,'EOF':-1,'UCHAR_MAX':255,'CHAR_MAX':127}
    if expr in constants: value=constants[expr]
    elif re.fullmatch(r'[-+]?(?:0[xX][0-9a-fA-F]+|[0-9]+)',expr):
        value=int(expr,16 if 'x' in expr.lower() else 10)
    else:
        # Restricted arithmetic, never Python eval or arbitrary C execution.
        expr=expr.replace('sizeof(long)','8').replace('sizeof(int)','4')
        for name,v in constants.items(): expr=re.sub(r'\b'+name+r'\b',str(v),expr)
        expr=re.sub(r"'(?:\\.|[^'\\])*'",lambda m:str(literal(m[0])),expr)
        ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
             ast.LShift:operator.lshift,ast.RShift:operator.rshift,
             ast.BitOr:operator.or_,ast.BitAnd:operator.and_,ast.BitXor:operator.xor}
        def evaluate(node):
            if isinstance(node,ast.Constant) and isinstance(node.value,int): return node.value
            if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
                return -evaluate(node.operand) if isinstance(node.op,ast.USub) else evaluate(node.operand)
            if isinstance(node,ast.BinOp) and type(node.op) in ops:
                a,b=evaluate(node.left),evaluate(node.right)
                if isinstance(node.op,(ast.LShift,ast.RShift)) and not 0<=b<=64: raise ValueError('shift')
                return ops[type(node.op)](a,b)
            raise ValueError('nonliteral')
        value=evaluate(ast.parse(expr,mode='eval').body)
    return value & SIZE_MAX if size else value

def main(root):
    root=Path(root); records={}; inventory=[]; counts=Counter()
    sources=json.loads((root/'sources.json').read_text())
    for source in sources:
        repo=source['repo']; base=Path(source['local'])
        for p in sorted(base.rglob('*')):
            if p.suffix not in {'.c','.cpp'} or not p.is_file(): continue
            rel=str(p.relative_to(base))
            if any(x in rel for x in ['cpiscine/','printf/','get_next_line/','third_party/','fakes/']): continue
            text=p.read_text(errors='replace')
            # Remove comments but retain newlines/offsets for stable citations.
            clean=TOKEN.sub(lambda m: re.sub(r'[^\n]',' ',m[0]) if m[0].startswith(('/',)) else m[0],text)
            calls=[]
            candidates=[]
            for match in re.finditer(r'\b(ft_|test_single_|single_test_)([a-z_]+)\s*\(',clean):
                fn=match[2]
                if fn not in ARITY: continue
                try:
                    raw,end=arguments(clean,match.end())
                    if match[1]!='ft_':
                        if 'xicodomingues--francinette' not in str(base): continue
                        raw=raw[1:]
                        if fn=='itoa': raw=raw[1:]
                        raw=raw[:ARITY[fn]]
                    candidates.append((fn,raw,match.start()))
                except ValueError: continue
            # ylam21 stores literal input tables rather than direct calls.
            if repo=='ylam21/42_Libft_Tester' and p.stem.startswith('ft_'):
                fn=p.stem[3:]
                if fn in ARITY:
                    for match in re.finditer(r'\[\d+\]\s*=\s*\{\s*\.[a-z_]+\s*=\s*\{',clean):
                        end=clean.find('}',match.end())
                        if end<0: continue
                        try:
                            raw,_=arguments('('+clean[match.end():end]+')',1)
                            candidates.append((fn,raw[:ARITY[fn]],match.start()))
                        except ValueError: continue
            for fn,raw,position in candidates:
                if fn not in ARITY: continue
                line=clean.count('\n',0,position)+1
                try:
                    if len(raw)!=ARITY[fn]: raise ValueError('arity')
                    args=[literal(a,size=(fn=='calloc' or fn in {'strncmp','strnstr','substr'} and i==2)) for i,a in enumerate(raw)]
                    if fn=='substr' and isinstance(args[1],int): args[1]&=2**32-1
                    c=scalar(fn,args)
                    if c is None: raise ValueError('outside_defined_contract')
                    item={'repo':repo,'path':rel,'line':line,
                          'url':f"https://github.com/{repo}/blob/{source['commit'] or source['branch']}/{rel}#L{line}"}
                    record=records.setdefault(c.id,{'fn':fn,'args':[{'hex':a.hex()} if isinstance(a,bytes) else a for a in args],'sources':[]})
                    if item not in record['sources']: record['sources'].append(item)
                    counts['literal_occurrences']+=1
                    calls.append({'line':line,'function':fn,'case':c.id,'status':'literal_imported'})
                except (ValueError,SyntaxError,TypeError,IndexError,OverflowError):
                    counts['not_literal_or_excluded']+=1
                    calls.append({'line':line,'function':fn,'status':'scenario_review_required'})
            if calls:
                inventory.append({'repo':repo,'path':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'calls':calls})
    here=Path(__file__).parent
    (here/'corpus.json').write_text(json.dumps(list(records.values()),ensure_ascii=False,indent=2)+'\n')
    clean_sources=[{k:v for k,v in s.items() if k not in {'local'}} for s in sources]
    (here/'sources.json').write_text(json.dumps(clean_sources,ensure_ascii=False,indent=2)+'\n')
    (here/'audit-sources.json').write_text(json.dumps({'counts':dict(counts),'unique_literal_cases':len(records),'files':inventory},ensure_ascii=False,indent=2)+'\n')
    print(dict(counts),'unique_literal_cases',len(records))

if __name__=='__main__': main(sys.argv[1])
