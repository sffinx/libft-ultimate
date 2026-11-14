#!/usr/bin/env python3
"""Check that the public checkout is self-contained and safe to share."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import catalogue
from runner import command

ROOT=Path(__file__).resolve().parents[2]


class Publication(unittest.TestCase):
    def test_relative_documentation_links(self):
        documents=[ROOT/'README.md',ROOT/'CONTRIBUTING.md',ROOT/'CREDITS.md',
                   ROOT/'CHANGELOG.md',*sorted((ROOT/'docs').glob('*.md'))]
        for doc in documents:
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',doc.read_text()):
                if target.startswith(('https://','http://','#')): continue
                path=unquote(target.split('#')[0])
                self.assertTrue((doc.parent/path).exists(),f'{doc.name}: {target}')

    def test_example_is_reproduced(self):
        sys.path.insert(0,str(Path(__file__).parent))
        from selftest import fixture
        with tempfile.TemporaryDirectory(prefix='libft-example-') as tmp:
            project=Path(tmp)/'libft'; fixture(project,2)
            code,out=command([sys.executable,str(ROOT/'libft-test'),str(project),'--only','strlen'],ROOT)
            self.assertEqual(code,1,out)
            self.assertIn('longueur en octets ; attendu=7 ; obtenu=8',out)
            self.assertIn("ft_strlen — 'Hello !'",out)

    def test_public_files_exclude_local_state(self):
        run=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,text=True,check=True)
        paths=[p for p in run.stdout.split('\0') if p]
        self.assertTrue(paths,'stage the publication files first')
        forbidden_parts={'.42manager','.organisation','__pycache__'}
        forbidden_suffixes={'.pdf','.zip','.o','.a','.so','.pyc','.log'}
        for rel in paths:
            p=Path(rel)
            self.assertFalse(set(p.parts)&forbidden_parts,rel)
            self.assertNotIn(p.suffix,forbidden_suffixes,rel)
            text=(ROOT/rel).read_text(errors='replace')
            self.assertNotRegex(text,r'/home/[a-zA-Z0-9_.-]+/',rel)
            self.assertNotRegex(text,r'github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----',rel)

    def test_documented_counts_and_credits(self):
        self.assertEqual(len(catalogue()),6765)
        sources=json.loads((ROOT/'.testeur/sources.json').read_text())
        self.assertEqual(len({s['repo'] for s in sources}),14)
        credits=(ROOT/'CREDITS.md').read_text()
        for source in sources:
            self.assertIn(source['url'],credits)
            self.assertIn(source['commit'],credits)


if __name__=='__main__': unittest.main(verbosity=2)
