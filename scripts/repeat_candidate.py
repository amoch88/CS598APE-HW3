#!/usr/bin/env python3
"""Add bounded release repetitions to a target-verified archived candidate."""
import argparse,csv,datetime,json,pathlib,statistics,subprocess,time
from zoneinfo import ZoneInfo
from benchmark import run_one,digest
from png_pixels import compare
p=argparse.ArgumentParser();p.add_argument('study',type=pathlib.Path);p.add_argument('--runs',type=int,default=3);p.add_argument('--deadline');p.add_argument('--resume',action='store_true')
a=p.parse_args();r=a.study.resolve();manifest=json.loads((r/'manifest.json').read_text());state=json.loads((r/'status.json').read_text())
assert state['phase']=='complete' and state['status']=='PASS'
assert json.loads((r/'target-correctness/report.json').read_text())['status']=='PASS'
binary=r/'source/sandpile.exe';assert digest(binary)==json.loads((r/'build-hashes.json').read_text())['binary']
records=list(csv.DictReader((r/'measurements.csv').open()));fieldnames=list(records[0]);target=[x for x in records if int(x['size'])==1001]
deadline=datetime.datetime.fromisoformat(a.deadline).replace(tzinfo=ZoneInfo('America/Chicago')).timestamp() if a.deadline else float('inf')
if a.resume:
 assert (r/'repeat-manifest.json').exists()
 assert json.loads((r/'repeat-manifest.json').read_text())['source_commit']==manifest['source_commit']
repeat_path=r/('repeat-continuation-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json' if a.resume else 'repeat-manifest.json')
with repeat_path.open('x') as f:json.dump(dict(source_commit=manifest['source_commit'],initial_target_count=len(target),requested_target_count=a.runs,deadline=a.deadline,reason='promising candidate already passed target integer correctness'),f,indent=2)
for k in range(len(target)+1,a.runs+1):
 subprocess.run(['env','TZ=America/Chicago','date'],check=True)
 estimate=max(float(x['wall_seconds']) for x in target)
 if deadline-time.time()<estimate*1.2+60:raise RuntimeError('deadline guard: insufficient time for another target run')
 limit=min(estimate*1.5+30,deadline-time.time()-30)
 x=dict(variant=manifest['name'],source_commit=manifest['source_commit'],run=k,**run_one(binary,r/'timing'/f'n1001-run{k}',1001,0,timeout=limit))
 compare(pathlib.Path(manifest['baseline'])/'source/identity-ref.png',pathlib.Path(x['directory'])/'identity.png')
 records.append(x);target.append(x)
 with (r/'measurements.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fieldnames);w.writeheader();w.writerows(records)
 print(json.dumps(x),flush=True)
print(json.dumps({'target_runs':len(target),'median':statistics.median(float(x['wall_seconds']) for x in target)}),flush=True)
