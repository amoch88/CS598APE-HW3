#!/usr/bin/env python3
"""Bounded N=101 instruction profiles, kept separate from release timing."""
import argparse,json,pathlib,subprocess
from benchmark import digest
from png_pixels import compare
p=argparse.ArgumentParser();p.add_argument('studies',type=pathlib.Path,nargs='+');a=p.parse_args()
for root in a.studies:
 r=root.resolve();m=json.loads((r/'manifest.json').read_text());binary=r/'source/sandpile.exe'
 assert digest(binary)==json.loads((r/'build-hashes.json').read_text())['binary']
 d=r/'callgrind-n101';d.mkdir()
 cmd=['timeout','--kill-after=5','90','taskset','-c','0','valgrind','--tool=callgrind','--callgrind-out-file='+str(d/'callgrind.out'),str(binary),'101']
 with (d/'run.stdout').open('w') as out,(d/'run.stderr').open('w') as err:subprocess.run(cmd,cwd=d,stdout=out,stderr=err,check=True)
 with (d/'annotated.txt').open('w') as out:subprocess.run(['callgrind_annotate','--inclusive=no','--threshold=99',str(d/'callgrind.out')],stdout=out,check=True)
 total=int(next(line.split(':',1)[1].strip() for line in (d/'callgrind.out').open() if line.startswith('summary:')))
 comparison=compare(pathlib.Path(m['baseline'])/'golden/n101/identity.png',d/'identity.png')
 report=dict(size=101,events='Ir only; no hardware/cache counters',total_instructions=total,source_commit=m['source_commit'],command=cmd,pixel_comparison=comparison)
 (d/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
