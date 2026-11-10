#!/usr/bin/env python3
"""Time and integer-validate a completed smaller-size candidate without rerunning it."""
import argparse,csv,datetime,json,pathlib,subprocess,sys,time
from zoneinfo import ZoneInfo
from benchmark import run_one,digest
from png_pixels import compare
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('study',type=pathlib.Path);p.add_argument('--deadline');a=p.parse_args();r=a.study.resolve()
m=json.loads((r/'manifest.json').read_text());old=json.loads((r/'status.json').read_text());assert old['phase']=='complete' and old['status']=='PASS'
assert json.loads((r/'small-correctness/report.json').read_text())['status']=='PASS'
assert all(x['status']=='PASS' for x in json.loads((r/'memory-safety.json').read_text()))
assert all(x['status']=='PASS' for x in json.loads((r/'stages.json').read_text()))
source=r/'source/sandpile.c';binary=r/'source/sandpile.exe';hashes=json.loads((r/'build-hashes.json').read_text())
assert digest(source)==hashes['source'] and digest(binary)==hashes['binary']
records=list(csv.DictReader((r/'measurements.csv').open()));assert not any(int(x['size'])==1001 for x in records)
with (r/'exploratory-completion.json').open('x') as f:json.dump(old,f,indent=2)
deadline=datetime.datetime.fromisoformat(a.deadline).replace(tzinfo=ZoneInfo('America/Chicago')).timestamp() if a.deadline else float('inf')
subprocess.run(['env','TZ=America/Chicago','date'],check=True)
if deadline-time.time()<1000:raise RuntimeError('insufficient reserved time for target timing and integer check')
(r/'status.json').write_text(json.dumps(dict(phase='target-promotion',status='START',deadline=a.deadline),indent=2)+'\n')
x=dict(variant=m['name'],source_commit=m['source_commit'],run=1,**run_one(binary,r/'timing/n1001-run1',1001,0,timeout=480))
b=pathlib.Path(m['baseline']);compare(b/'source/identity-ref.png',pathlib.Path(x['directory'])/'identity.png')
records.append(x)
with (r/'measurements.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(x));w.writeheader();w.writerows(records)
print(json.dumps(x),flush=True)
subprocess.run(['env','TZ=America/Chicago','date'],check=True)
goldens=pathlib.Path(m['row_results'])/'expected'
if not goldens.exists():goldens=r/'expected'
cmd=['timeout','--kill-after=5','480','taskset','-c','0',sys.executable,str(ROOT/'scripts/check.py'),'--source',str(source),'--binary',str(binary),'--output',str(r/'target-correctness'),'--reference-png',str(b/'source/identity-ref.png'),'--golden',str(goldens),'--sizes','1001','--target-png',str(pathlib.Path(x['directory'])/'identity.png')]
with (r/'target-correctness.stdout').open('x') as out,(r/'target-correctness.stderr').open('x') as err:subprocess.run(cmd,stdout=out,stderr=err,check=True)
assert json.loads((r/'target-correctness/report.json').read_text())['status']=='PASS'
(r/'promotion.json').write_text(json.dumps(dict(source_commit=m['source_commit'],command=cmd,status='PASS',deadline=a.deadline),indent=2)+'\n')
(r/'status.json').write_text(json.dumps(dict(phase='complete',status='PASS',scope='smaller checks plus target integer validation',central_time=datetime.datetime.now(ZoneInfo('America/Chicago')).isoformat()),indent=2)+'\n')
print('PASS: target release and all-integer correctness',flush=True)
