"""Small offline CLI: stdlib Python + C compiler, no installation or updater."""
import argparse
import ctypes
from collections import Counter
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from catalog import FUNCTIONS, SIGNATURES, ALLOCATING, catalogue, scalar, write_api, write_c

HERE=Path(__file__).resolve().parent
VERSION='0.1.0'
NOTICE=('Moulinette : elle peut employer d’autres tests et ne pas reprendre ceux-ci.\n'
        'Ce scan ne prédit ni la note ni la réussite officielle.')


def clean(text):
    text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',text)
    return ''.join(c for c in text if c in '\n\t' or (ord(c)>=32 and ord(c)!=127))


def command(args, cwd, timeout=60, env=None):
    environ=os.environ.copy()
    environ.update({'LC_ALL':'C','NO_COLOR':'1','TERM':'dumb'})
    # Inherited MAKEFLAGS can silently enable -i/-n or parallel builds.
    for key in ('MAKEFLAGS','MFLAGS','MAKEOVERRIDES'):
        environ.pop(key,None)
    if env: environ.update(env)
    with tempfile.TemporaryFile() as capture:
        process=subprocess.Popen(args,cwd=cwd,stdout=capture,stderr=subprocess.STDOUT,
                                 env=environ,start_new_session=True)
        try:
            code=process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired,KeyboardInterrupt):
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()
            if sys.exc_info()[0] is KeyboardInterrupt: raise
            code=124
        capture.seek(0)
        # Bounded diagnostics prevent a broken build from flooding the screen.
        output=capture.read(2_000_000).decode('utf-8','replace')
    return code,clean(output)


def provenance():
    result={}
    for row in json.loads((HERE/'corpus.json').read_text()):
        args=[bytes.fromhex(x['hex']) if isinstance(x,dict) else x for x in row['args']]
        c=scalar(row['fn'],args)
        if c:
            result[c.id]=sorted(row['sources'],key=lambda s:(s['repo']!='Tripouille/libftTester',s['repo'],s['path'],s['line']))
    return result


def copy_project(source,dest):
    excluded={'.git','.hg','.svn','__pycache__','.cache','.testeur','node_modules'}
    def ignore(folder,names):
        return [n for n in names if n in excluded or n.endswith(('.o','.a','.so','.pyc'))]
    # Dereference only links inside the project. Reject outside links rather than
    # accidentally building through them in a directory containing student work.
    for p in source.rglob('*'):
        if '.git' in p.parts: continue
        if p.is_symlink():
            try: p.resolve(strict=True).relative_to(source)
            except (OSError,ValueError):
                raise ValueError(f'Lien externe ou cassé à vérifier : {p.relative_to(source)}') from None
    shutil.copytree(source,dest,ignore=ignore,symlinks=False)


def outcome(name,ok,detail='',status=None):
    return {'name':name,'status':status or ('OK' if ok else 'FAIL'),
            'detail':detail,'origin':'Test ajouté — contrôle du sujet PDF v1.3'}


def compile_harness(work,project,cases,cc):
    write_api(work/'api.h'); write_c(cases,work/'cases.h')
    argv=[cc,'-std=c11','-Wall','-Wextra','-Werror','-O1','-g',
          '-fno-builtin','-I',str(work),str(HERE/'harness.c'),
          '-Wl,--whole-archive',str(project/'libft.a'),'-Wl,--no-whole-archive',
          '-Wl,--wrap=malloc','-Wl,--wrap=free','-o',str(work/'suite')]
    return command(argv,work,120)


def headers(project,work,selected,cc):
    results=[]
    header=project/'libft.h'
    if not header.is_file(): return [outcome('Header',False,'libft.h introuvable')]
    for fn in selected:
        canonical=SIGNATURES[fn].replace('ft_'+fn,'ultimate_expected_'+fn)
        source='#include "libft.h"\n#include "libft.h"\n#include <stddef.h>\n'
        source+=canonical+';\n'
        source+=f'_Static_assert(__builtin_types_compatible_p(__typeof__(&ft_{fn}), __typeof__(&ultimate_expected_{fn})), "signature ft_{fn} incompatible avec PDF 1.3");\n'
        if fn.startswith('lst'):
            source+='_Static_assert(__builtin_types_compatible_p(__typeof__(((t_list *)0)->content), void *), "content doit être void *");\n'
            source+='_Static_assert(__builtin_types_compatible_p(__typeof__(((t_list *)0)->next), struct s_list *), "next doit être struct s_list *");\n'
            source+='_Static_assert(offsetof(t_list, content)==0 && offsetof(t_list,next)==sizeof(void *) && sizeof(t_list)==2*sizeof(void *), "disposition de t_list incompatible avec le sujet");\n'
        probe=work/'header-check.c'; probe.write_text(source)
        code,out=command([cc,'-Wall','-Wextra','-Werror','-fsyntax-only','-I',str(project),str(probe)],work)
        if code: results.append(outcome('Header ft_'+fn,False,out.strip()))
    if not results: results.append(outcome('Header',True,'signatures des fonctions sélectionnées et double inclusion'))
    return results


def archive_state(project):
    return {str(p.relative_to(project)):(p.stat().st_mtime_ns,p.stat().st_size)
            for p in project.rglob('*') if p.is_file() and p.suffix in {'.o','.a'}}


def conformity(project,work,cc,no_norm):
    checks=[]
    sources=sorted(project.rglob('*.c')); hdrs=sorted(project.rglob('*.h'))
    nested=[str(p.relative_to(project)) for p in sources+hdrs if p.parent!=project]
    checks.append(outcome('Emplacement des sources',not nested,', '.join(nested)))
    failures=[]
    for index,p in enumerate(sources):
        code,out=command([cc,'-Wall','-Wextra','-Werror','-c',str(p),'-I',str(project),
                          '-o',str(work/f'check-{index}.o')],work)
        if code: failures.append(str(p.relative_to(project))+':\n'+out)
    checks.append(outcome('Compilation stricte',not failures,'\n'.join(failures)))
    code,dry=command(['make','-n','-B'],project)
    compiles=[line for line in dry.splitlines() if re.search(r'(?:^|\s)(?:\S*/)?(?:cc|gcc|clang)(?:-[0-9]+)?\s',line) and re.search(r'\.c(?:\s|$)',line)]
    if compiles:
        bad=[l for l in compiles if not all(f in shlex.split(l) for f in ('-Wall','-Wextra','-Werror'))]
        checks.append(outcome('Flags du Makefile',not bad,'\n'.join(bad)))
    else:
        checks.append(outcome('Flags du Makefile',True,'commandes non reconnues : vérification manuelle',status='REVIEW'))
    checks.append(outcome('Archive créée avec ar',True,'à vérifier dans les commandes de construction',status='REVIEW') if not re.search(r'(?:^|\s)(?:\S*/)?ar\s',dry) else outcome('Archive créée avec ar',True))
    if re.search(r'(?:^|\s)(?:\S*/)?libtool\s',dry): checks.append(outcome('libtool interdit',False,dry))
    c99=[line for line in compiles if '-std=c99' in shlex.split(line)]
    if c99: checks.append(outcome('Option -std=c99 interdite',False,'\n'.join(c99)))
    for p in sources+hdrs:
        text=p.read_text(errors='replace')
        text=re.sub(r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"','',text)
        if re.search(r'\brestrict\b',text): checks.append(outcome('restrict interdit',False,str(p.relative_to(project))))
    before=archive_state(project)
    code,out=command(['make'],project)
    checks.append(outcome('Sans recompilation inutile',code==0 and before==archive_state(project),out.strip()))
    # Required make targets are exercised only in the disposable copy.
    code,out=command(['make','clean'],project)
    objects=list(project.rglob('*.o'))
    checks.append(outcome('make clean',code==0 and not objects and (project/'libft.a').is_file(),out.strip()))
    code,out=command(['make','fclean'],project)
    checks.append(outcome('make fclean',code==0 and not list(project.rglob('*.o')) and not (project/'libft.a').exists(),out.strip()))
    code,out=command(['make','all'],project)
    checks.append(outcome('make all',code==0 and (project/'libft.a').is_file(),out.strip()))
    code,out=command(['make','re'],project)
    checks.append(outcome('make re',code==0 and (project/'libft.a').is_file(),out.strip()))
    readme=project/'README.md'
    if not readme.is_file(): checks.append(outcome('README.md',False,'fichier absent'))
    else:
        text=readme.read_text(errors='replace'); lines=text.splitlines()
        first=lines[0].strip() if lines else ''
        valid=bool(re.fullmatch(r'([*_])This activity has been created as part of the 42 curriculum by [^<>\n]+\.\1',first))
        checks.append(outcome('Première ligne du README',valid,'phrase imposée par le sujet, en italique'))
        # Semantic content / campus-language headings need human review, not a
        # brittle English-only regexp that would reject a permitted French README.
        checks.append(outcome('Contenu du README',True,'relire description, instructions, ressources, usage de l’IA et description détaillée de la bibliothèque',status='REVIEW'))
    if no_norm or not shutil.which('norminette'):
        checks.append(outcome('Norminette',True,'désactivée' if no_norm else 'non installée ; aucun paquet ajouté',status='SKIP'))
    elif sources or hdrs:
        code,out=command(['norminette']+[str(p.relative_to(project)) for p in sources+hdrs],project,120)
        checks.append(outcome('Norminette',code==0,out.strip() if code else ''))
    if (project/'libft.a').is_file():
        code,out=command(['nm','--defined-only','--format=posix',str(project/'libft.a')],project)
        definitions={}
        for line in out.splitlines():
            m=re.match(r'^(\S+)\s+([A-Za-z])\s',line)
            if m: definitions[m[1]]=m[2]
        globals_=[n for n,t in definitions.items() if t in 'BbDdCcGgSsRr' and '.' not in n and not n.startswith('__')]
        helpers=[n for n,t in definitions.items() if t=='T' and n not in {'ft_'+f for f in FUNCTIONS} and not n.startswith('__')]
        checks.append(outcome('Variables globales',code==0 and not globals_,', '.join(globals_)))
        checks.append(outcome('Helpers static',not helpers,', '.join(helpers)))
        code,unresolved=command(['nm','-u',str(project/'libft.a')],project)
        externs=set(re.findall(r'\bU\s+(\S+)',unresolved))
        allowed={'malloc','free','write','_GLOBAL_OFFSET_TABLE_','__stack_chk_fail'}|set(definitions)
        forbidden=sorted(externs-allowed)
        checks.append(outcome('Fonctions externes',code==0 and not forbidden,', '.join(forbidden)))
        # A symbol union is insufficient for per-function restrictions. Never
        # claim a full check when indirect/static call paths remain unaudited.
        checks.append(outcome('Autorisations par fonction',True,'vérifier les appels transitifs : malloc/free/write sont permis seulement aux fonctions indiquées dans le sujet',status='REVIEW'))
    return checks


def execute_suite(work,project,cases,selected,cc,timeout,valgrind):
    code,build=compile_harness(work,project,cases,cc)
    if code: return [],[outcome('Liaison du testeur',False,build)],2
    results=[]; extra=[]
    for fn in selected:
        argv=[str(work/'suite'),fn,str(timeout*(10 if valgrind else 1))]
        env={}
        if valgrind:
            logfile=work/f'valgrind-{fn}.log'
            argv=['valgrind','--quiet','--leak-check=full','--show-leak-kinds=definite,indirect',
                  '--errors-for-leak-kinds=definite,indirect','--error-exitcode=97',
                  '--log-file='+str(logfile)]+argv
            env['ULTIMATE_VALGRIND']='1'
        code,out=command(argv,work,timeout=max(30,len([c for c in cases if c.fn==fn])*timeout*(12 if valgrind else 1)),env=env)
        expected={c.id for c in cases if c.fn==fn}; seen=set()
        for line in out.splitlines():
            parts=line.split('\t',2)
            if len(parts)!=3 or parts[0] not in expected: continue
            ident,status,detail=parts
            if ident in seen or status not in {'OK','FAIL','CRASH','TIMEOUT','MISSING'}:
                extra.append(outcome('Protocole moteur',False,'réponse dupliquée ou inconnue')); continue
            pidmatch=re.match(r'@PID:(\d+)@',detail)
            pid=int(pidmatch[1]) if pidmatch else None
            if pidmatch: detail=detail[pidmatch.end():]
            if status=='TIMEOUT': detail+=' ; délai machine à vérifier, pas une preuve de non-conformité'
            seen.add(ident); results.append({'id':ident,'function':fn,'status':status,'detail':detail,'pid':pid})
        if expected!=seen or code:
            extra.append(outcome('Exécution ft_'+fn,False,f'code {code} ; {len(seen)}/{len(expected)} réponses reçues'))
        if valgrind and logfile.exists():
            text=clean(logfile.read_text(errors='replace'))
            # Valgrind diagnostics from forked children do not change the
            # parent's exit status. Inspect the log in addition to exit codes.
            pattern=r'Invalid |Syscall param |Mismatched free|uninitialised|uninitialized|definitely lost: [1-9]|indirectly lost: [1-9]|are definitely lost|are indirectly lost'
            messages={}
            for line in text.splitlines():
                m=re.match(r'(?:==|--)(\+?\d+)(?:==|--)\s?(.*)',line)
                if m: messages.setdefault(int(m[1]),[]).append(m[2])
            mapped={r.get('pid'):r for r in results if r['function']==fn}
            for pid,lines in messages.items():
                message='\n'.join(lines)
                if not re.search(pattern,message): continue
                if pid in mapped:
                    result=mapped[pid]
                    result['status']='MEMORY'
                    result['detail']+='\nContrôle mémoire ajouté (Valgrind) :\n'+message.strip()
                else: extra.append(outcome('Mémoire ft_'+fn,False,message.strip()))
        counts=Counter(r['status'] for r in results if r['function']==fn)
        total=sum(counts.values()); good=counts['OK']
        state='OK' if total and good==total else 'ABSENT' if counts['MISSING']==total else 'ÉCHEC'
        print(f'  {state:<7} ft_{fn:<16} {good:>4}/{total}',flush=True)
    return results,extra,0


def print_details(checks,results,cases,origins):
    failed=[x for x in checks if x['status']=='FAIL']
    errors=[r for r in results if r['status'] not in {'OK','MISSING'}]
    byid={c.id:c for c in cases}
    if failed or errors: print('\nDétails des erreurs\n')
    for check in failed:
        print('  '+check['name'])
        for line in check['detail'].splitlines(): print('    '+line)
        print('    Origine : '+check['origin']+'\n')
    for r in errors:
        c=byid[r['id']]
        print(f'  ft_{c.fn} — {c.label}')
        for line in r['detail'].splitlines(): print('    '+line)
        print('    Cas : '+c.id)
        refs=origins.get(c.id,[])
        if refs:
            print('    Référence : entrée publique adaptée au contrat PDF 1.3.')
            print('    Les contrôles mémoire et le diagnostic sont ajoutés par Ultimate.')
            for src in refs:
                print('    '+src['repo']+' : '+src['url'])
        else:
            print('    Origine : test ajouté à Libft Ultimate (PDF 1.3)')
        print()
    missing=sorted({r['function'] for r in results if r['status']=='MISSING'},key=FUNCTIONS.index)
    if missing:
        print('\nFonctions absentes de l’archive : '+', '.join('ft_'+f for f in missing))
        print('  Origine : test ajouté — présence des 43 fonctions du PDF 1.3.')
    reviews=[c for c in checks if c['status'] in {'SKIP','REVIEW'}]
    if reviews:
        print('\nÀ vérifier séparément\n')
        for c in reviews: print('  '+c['name']+' : '+c['detail'])


def main(argv=None):
    parser=argparse.ArgumentParser(prog='libft-test',add_help=False,description='Testeur Libft — sujet PDF v1.3.',
        epilog='Exemples : libft-test ../libft | libft-test ../libft --only split')
    parser._positionals.title='Dossier'
    parser._optionals.title='Options'
    parser.add_argument('-h','--help',action='help',help='afficher cette aide')
    parser.add_argument('project',nargs='?',default='.',metavar='DOSSIER',help='dossier contenant le Makefile et libft.h')
    parser.add_argument('--only',metavar='FONCTION',help='une fonction ou une liste séparée par des virgules')
    parser.add_argument('--list',action='store_true',help='lister les fonctions sans lancer de scan')
    parser.add_argument('--credits',action='store_true',help='afficher les 14 projets sources')
    parser.add_argument('--valgrind',action='store_true',help='ajouter les contrôles de lecture mémoire et d’utilisation après free')
    parser.add_argument('--no-norm',action='store_true',help='ne pas lancer Norminette')
    parser.add_argument('--json',type=Path,metavar='FICHIER',help='sauvegarder un rapport structuré')
    parser.add_argument('--seed',type=int,default=42,help='graine reproductible (défaut : 42)')
    parser.add_argument('--timeout',type=int,default=2,metavar='SECONDES',help='délai maximal par cas (défaut : 2)')
    parser.add_argument('--version',action='version',help='afficher la version',version=f'Libft Ultimate {VERSION} — sujet PDF 1.3')
    args=parser.parse_args(argv)
    if args.credits:
        print((HERE.parent/'CREDITS.md').read_text()); return 0
    if args.list:
        for fn in FUNCTIONS: print('ft_'+fn)
        return 0
    print('\nLibft Ultimate · sujet PDF 1.3\n')
    print(NOTICE+'\n')
    selected=[x.strip().removeprefix('ft_') for x in args.only.split(',')] if args.only else list(FUNCTIONS)
    unknown=set(selected)-set(FUNCTIONS)
    if unknown: parser.error('fonction inconnue : '+', '.join(sorted(unknown)))
    selected=list(dict.fromkeys(selected))
    if not 1<=args.timeout<=60: parser.error('--timeout doit être entre 1 et 60')
    source=Path(args.project).expanduser().resolve()
    if not sys.platform.startswith('linux') or ctypes.sizeof(ctypes.c_size_t)!=8:
        print('Cette version nécessite Linux 64 bits et un éditeur de liens compatible --wrap.'); return 2
    if not source.is_dir(): print('Dossier introuvable : '+str(source)); return 2
    if not (source/'Makefile').is_file():
        print('Makefile introuvable dans le dossier indiqué.')
        print('Indique le dossier de ta Libft : libft-test /chemin/vers/libft')
        print('Origine : test ajouté — préparation du scan.')
        return 1
    if args.json and (args.json.resolve()==source or args.json.resolve().is_relative_to(source)):
        print('Choisis un rapport JSON en dehors du dépôt étudiant.'); return 2
    required=['cc','make','ar','nm']
    missing=[p for p in required if not shutil.which(p)]
    if args.valgrind and not shutil.which('valgrind'): missing.append('valgrind')
    if missing: print('Outils manquants : '+', '.join(missing)+'. Aucune installation automatique.'); return 2
    cases=[c for c in catalogue(args.seed) if c.fn in selected]
    origins=provenance(); start=time.monotonic(); results=[]; checks=[]; infra=0
    print(f'  {len(selected)} fonction(s) · {len(cases)} cas distincts · graine {args.seed}')
    print('  Références : Tripouille en premier ; crédits complets avec --credits.')
    print('  Compilation et exécution dans une copie temporaire.\n')
    try:
        with tempfile.TemporaryDirectory(prefix='libft-ultimate-') as temporary:
            work=Path(temporary); project=work/'projet'
            copy_project(source,project)
            if not (project/'Makefile').is_file():
                checks.append(outcome('Construction',False,'Makefile introuvable'))
            else:
                code,out=command(['make'],project,120)
                checks.append(outcome('Construction',code==0 and (project/'libft.a').is_file(),out.strip() or 'libft.a absente'))
            if checks[-1]['status']=='OK':
                checks+=headers(project,work,selected,'cc')
                # Function-only mode deliberately isolates the selected contract.
                if not args.only:
                    checks+=conformity(project,work,'cc',args.no_norm)
                    count=Counter(c['status'] for c in checks)
                    print(f"  Projet : {count['OK']} contrôles OK · {count['FAIL']} échec(s) · {count['SKIP']+count['REVIEW']} à vérifier\n",flush=True)
                if (project/'libft.a').is_file():
                    results,more,infra=execute_suite(work,project,cases,selected,'cc',args.timeout,args.valgrind)
                    checks+=more
            print_details(checks,results,cases,origins)
    except (OSError,ValueError) as error:
        print('Scan interrompu : '+clean(str(error))); return 2
    except KeyboardInterrupt:
        print('\nScan interrompu.'); return 130
    labels={c.id:c.label for c in cases}
    for r in results:
        r['label']=labels[r['id']]
        r['origins']=origins.get(r['id'],[])
        r['origin_kind']='public_input_adapted' if r['origins'] else 'added_test'
    failures=sum(c['status']=='FAIL' for c in checks)+sum(r['status']!='OK' for r in results)
    passed=sum(r['status']=='OK' for r in results)
    print(f'\nRésultat : {passed}/{len(cases)} cas réussis · {failures} échec(s) · {time.monotonic()-start:.1f} s')
    if args.only: print('Portée : fonctions sélectionnées uniquement ; aucun bilan complet du projet.')
    else: print('Les vérifications manuelles signalées restent nécessaires.')
    if args.json:
        report={'tester_version':VERSION,'subject':'PDF 1.3','seed':args.seed,'notice':NOTICE,
                'selected':selected,'checks':checks,'results':results,'total_cases':len(cases)}
        try:
            args.json.parent.mkdir(parents=True,exist_ok=True)
            args.json.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print('Rapport : '+str(args.json))
        except OSError as error:
            print('Rapport non enregistré : '+str(error)); return 2
    return 2 if infra else 1 if failures or len(results)!=len(cases) else 0
