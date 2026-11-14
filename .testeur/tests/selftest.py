#!/usr/bin/env python3
"""Integration tests against an independent libc-backed fixture and mutants."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import SIGNATURES, FUNCTIONS, catalogue
from runner import compile_harness, command, headers, provenance

HERE=Path(__file__).parent

def fixture(project,mutation=0):
    project.mkdir(exist_ok=True)
    head='#ifndef LIBFT_H\n#define LIBFT_H\n#include <stddef.h>\n#include <stdlib.h>\n'
    head+='typedef struct s_list { void *content; struct s_list *next; } t_list;\n'
    head+=';\n'.join(SIGNATURES.values())+';\n#endif\n'
    (project/'libft.h').write_text(head)
    (project/'fixture.c').write_text((HERE/'fixture.c').read_text())
    (project/'Makefile').write_text('NAME = libft.a\nall: $(NAME)\n$(NAME): fixture.o\n\tar rcs $@ $^\nfixture.o: fixture.c libft.h\n\tcc -Wall -Wextra -Werror -fno-builtin -O0 -g -DMUTATION='+str(mutation)+' -c fixture.c -o $@\nclean:\n\trm -f fixture.o\nfclean: clean\n\trm -f $(NAME)\nre: fclean all\n.PHONY: all clean fclean re\n')
    code,out=command(['make','re'],project)
    assert code==0,out[:8000]


def run_suite(work,project,cases,name='all',valgrind=False):
    code,out=compile_harness(work,project,cases,'cc')
    assert code==0,out[:8000]
    args=[str(work/'suite'),name,'1' if not valgrind else '10']
    env={}
    if valgrind:
        args=['valgrind','--quiet','--leak-check=full','--errors-for-leak-kinds=definite,indirect',
              '--error-exitcode=97','--log-file='+str(work/'memory.log')]+args
        env['ULTIMATE_VALGRIND']='1'
    code,out=command(args,work,240,env)
    return code,[line.split('\t',2) for line in out.splitlines() if '\t' in line]


def main():
    cases=catalogue()
    assert len({c.id for c in cases})==len(cases)
    assert set(c.fn for c in cases)==set(FUNCTIONS)
    assert [c.id for c in cases]==[c.id for c in catalogue()]
    assert [c.id for c in cases]!=[c.id for c in catalogue(43)]
    summary={'cases':len(cases),'functions':43,'checks':[]}
    with tempfile.TemporaryDirectory(prefix='ultimate-selftest-') as tmp:
        work=Path(tmp); project=work/'reference'
        fixture(project)
        assert all(c['status']=='OK' for c in headers(project,work,FUNCTIONS,'cc'))
        code,rows=run_suite(work,project,cases)
        failed=[r for r in rows if r[1]!='OK']
        print('Reference:',len(rows),'cases;',len(failed),'failures',flush=True)
        for row in failed[:25]: print(row,flush=True)
        assert code==0 and len(rows)==len(cases) and not failed
        summary['checks'].append('reference_all_pass')
        for mutation,fn in [(1,'isalpha'),(2,'strlen'),(3,'strlen'),(4,'strlen'),
                            (5,'memset'),(6,'memcpy'),(7,'memmove'),(8,'strlcpy'),
                            (9,'strchr'),(10,'strncmp'),(11,'calloc'),(12,'calloc'),
                            (13,'strdup'),(14,'split'),(15,'striteri'),(16,'putstr_fd'),
                            (17,'lstdelone'),(18,'lstclear'),(19,'lstmap'),(20,'lstmap'),(21,'strlen')]:
            fixture(project,mutation)
            subset=[c for c in cases if c.fn==fn]
            if mutation==4: subset=subset[:1]
            code,rows=run_suite(work,project,subset,fn)
            bad=[r for r in rows if r[1]!='OK']
            assert code==0 and bad,(mutation,fn,rows)
            print('Mutant',mutation,fn,': detected',flush=True)
            summary['checks'].append('mutant_'+str(mutation))
        fixture(project,30)
        subset=[c for c in cases if c.fn in {'strncmp','memcmp','strdup'}]
        code,rows=run_suite(work,project,subset)
        assert code==0 and all(r[1]=='OK' for r in rows),rows
        summary['checks'].append('valid_alternative_sign_and_allocation_size')
        fixture(project)
        subset=[c for c in cases if c.fn in {'split','lstmap','strdup','memmove'} and (c.fail or len(c.a)<30)]
        code,rows=run_suite(work,project,subset,valgrind=True)
        log=(work/'memory.log').read_text()
        print('Valgrind reference:',len(rows),'cases',flush=True)
        assert code==0 and len(rows)==len(subset) and all(r[1]=='OK' for r in rows),(code,rows,log)
        assert 'Invalid ' not in log and 'are definitely lost' not in log,log
        summary['checks'].append('valgrind_reference')
    output=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'last-verification.json'
    output.write_text(json.dumps(summary,indent=2)+'\n')
    print('OK:',len(summary['checks']),'validation groups',flush=True)

if __name__=='__main__': main()
