#!/usr/bin/env python3
"""Recover completed raw runs after the documented golden-path logging error."""
import argparse,csv,datetime,json,pathlib,re,subprocess
from benchmark import run_one,digest
from png_pixels import compare
p=argparse.ArgumentParser();p.add_argument('study',type=pathlib.Path);a=p.parse_args();r=a.study.resolve()
m=json.loads((r/'manifest.json').read_text());source=r/'source/sandpile.c';binary=r/'source/sandpile.exe'
assert digest(source)==json.loads((r/'build-hashes.json').read_text())['source']
assert digest(binary)==json.loads((r/'build-hashes.json').read_text())['binary']
assert json.loads((r/'small-correctness/report.json').read_text())['status']=='PASS'
assert all(x['status']=='PASS' for x in json.loads((r/'stages.json').read_text()))
assert all(x['status']=='PASS' for x in json.loads((r/'memory-safety.json').read_text()))
assert "unsupported operand type(s) for /: 'list' and 'str'" in (r/'error.txt').read_text()
with (r/'workflow-interruption.json').open('x') as f:json.dump(dict(original_status=json.loads((r/'status.json').read_text()),reason='golden path was shadowed by intermediate reference list; no source or oracle failure',recovery='adopt preserved run.json only after pixel verification; complete remaining small timings'),f,indent=2)
records=[]
for n in [101,251]:
 for k in range(1,4):
  d=r/'timing'/f'n{n}-run{k}'
  subprocess.run(['env','TZ=America/Chicago','date'],check=True)
  if d.exists():x=json.loads((d/'run.json').read_text())
  else:x=run_one(binary,d,n,0,timeout=90)
  compare(pathlib.Path(m['row_results'])/'expected'/f'n{n}'/'identity.png',d/'identity.png')
  record=dict(variant=m['name'],source_commit=m['source_commit'],run=k,**x);records.append(record)
  with (r/'measurements.csv').open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(record));w.writeheader();w.writerows(records)
  print(json.dumps(record),flush=True)
(r/'status.json').write_text(json.dumps(dict(phase='complete',status='PASS',scope='N<=251 screening; harness failure recovered',time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2)+'\n')
