#!/usr/bin/env python3
"""Regression tests for reporting, origins, CLI scope and student preservation."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import catalogue, FUNCTIONS
from runner import command, headers
from selftest import fixture

ROOT=Path(__file__).resolve().parents[2]

def snapshot(project):
    return {str(p.relative_to(project)):(p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest())
            for p in project.rglob('*') if p.is_file()}

class CLI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ultimate-cli-')
        self.work=Path(self.temp.name)
        self.project=self.work/'référence avec espaces'
        fixture(self.project)

    def tearDown(self): self.temp.cleanup()

    def cli(self,*args):
        return command([sys.executable,str(ROOT/'libft-test'),str(self.project),*args],self.work,240)

    def test_success_preserves_every_original_file(self):
        before=snapshot(self.project)
        code,out=self.cli('--only','ft_strlen','--json',str(self.work/'rapport.json'))
        self.assertEqual(code,0,out)
        self.assertEqual(snapshot(self.project),before)
        self.assertNotIn('\x1b',out); self.assertNotIn('\b',out)
        self.assertEqual(out.count('Moulinette :'),1)
        report=json.loads((self.work/'rapport.json').read_text())
        self.assertEqual(report['selected'],['strlen'])
        self.assertTrue(all(r['status']=='OK' for r in report['results']))
        self.assertTrue(all('origin_kind' in r for r in report['results']))

    def test_failure_contains_input_expectation_and_github(self):
        fixture(self.project,1)
        code,out=self.cli('--only','isalpha','--json',str(self.work/'bad.json'))
        self.assertEqual(code,1,out)
        self.assertIn('attendu=1',out); self.assertIn('obtenu=',out)
        self.assertIn('https://github.com/Tripouille/libftTester/blob/',out)
        self.assertIn('test ajouté',out)
        data=json.loads((self.work/'bad.json').read_text())
        for row in data['results']:
            refs=row['origins']
            if any(r['repo']=='Tripouille/libftTester' for r in refs):
                self.assertEqual(refs[0]['repo'],'Tripouille/libftTester')

    def test_wrong_lstsize_signature_is_rejected(self):
        p=self.project/'libft.h'
        p.write_text(p.read_text().replace('unsigned int ft_lstsize','int ft_lstsize'))
        checks=headers(self.project,self.work,['lstsize'],'cc')
        self.assertEqual(checks[0]['status'],'FAIL')

    def test_missing_function_never_passes(self):
        p=self.project/'fixture.c'
        p.write_text(p.read_text().replace('int ft_isalpha(','int absent_isalpha('))
        code,out=self.cli('--only','isalpha')
        self.assertEqual(code,1,out)
        self.assertIn('ABSENT',out)
        self.assertIn('Fonctions absentes',out)

    def test_failed_build_has_useful_message(self):
        (self.project/'Makefile').write_text('all:\n\tfalse\n')
        code,out=self.cli('--only','strlen')
        self.assertEqual(code,1,out)
        self.assertIn('Construction',out)
        self.assertIn('Origine : Test ajouté',out)

    def test_valgrind_errors_are_attached_to_the_case(self):
        fixture(self.project,22)
        code,out=self.cli('--only','strdup','--valgrind','--json',str(self.work/'memory.json'))
        self.assertEqual(code,1,out)
        data=json.loads((self.work/'memory.json').read_text())
        errors=[r for r in data['results'] if r['status']=='MEMORY']
        self.assertTrue(errors,out)
        self.assertTrue(all('Invalid read' in r['detail'] for r in errors))
        self.assertTrue(all(r['id'].startswith('strdup.') for r in errors))

    def test_credits_have_fourteen_unique_projects(self):
        sources=json.loads((ROOT/'.testeur/sources.json').read_text())
        self.assertEqual(len({s['repo'] for s in sources}),14)
        code,out=self.cli('--credits')
        self.assertEqual(code,0)
        for s in sources: self.assertIn(s['url'],out)

    def test_all_cases_are_unique_and_reproducible(self):
        rows=catalogue(); ids=[c.id for c in rows]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(ids,[c.id for c in catalogue()])
        self.assertEqual(set(c.fn for c in rows),set(FUNCTIONS))

if __name__=='__main__': unittest.main(verbosity=2)
