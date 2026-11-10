#!/usr/bin/env python3
"""Complete two target-verified distributions in reproducible paired order."""
import argparse,csv,datetime,json,pathlib,random,statistics,subprocess,time
from zoneinfo import ZoneInfo
from benchmark import run_one,digest
from png_pixels import compare
p=argparse.ArgumentParser();p.add_argument('candidate',type=pathlib.Path);p.add_argument('parent',type=pathlib.Path);p.add_argument('--runs',type=int,default=3);p.add_argument('--seed',type=int,default=598);p.add_argument('--deadline');a=p.parse_args()
roots=[a.candidate.resolve(),a.parent.resolve()];items=[]
for r in roots:
 m=json.loads((r/'manifest.json').read_text());state=json.loads((r/'status.json').read_text())
 assert state['phase']=='complete' and state['status']=='PASS'
 assert json.loads((r/'target-correctness/report.json').read_text())['status']=='PASS'
 binary=r/'source/sandpile.exe';assert digest(binary)==json.loads((r/'build-hashes.json').read_text())['binary']
 records=list(csv.DictReader((r/'measurements.csv').open()));target=[x for x in records if int(x['size'])==1001]
 assert len(target)==1,'This paired continuation expects exactly one preserved target run per study'
 items.append(dict(root=r,manifest=m,binary=binary,records=records,target=target))
rng=random.Random(a.seed);order=[]
for k in range(2,a.runs+1):
 block=[0,1];rng.shuffle(block);order.extend([(k,x) for x in block])
metadata=dict(seed=a.seed,initial_observations_preserved=True,initial_target_count=1,requested_target_count=a.runs,deadline=a.deadline,order=[dict(run=k,variant=items[i]['manifest']['name']) for k,i in order],note='Runs 2 and 3 are paired blocks; original run 1 observations remain historical/unpaired')
for x in items:
 with (x['root']/'paired-target-manifest.json').open('x') as f:json.dump(metadata,f,indent=2)
deadline=datetime.datetime.fromisoformat(a.deadline).replace(tzinfo=ZoneInfo('America/Chicago')).timestamp() if a.deadline else float('inf')
for k,i in order:
 item=items[i];r=item['root'];m=item['manifest'];subprocess.run(['env','TZ=America/Chicago','date'],check=True)
 estimate=max(float(x['wall_seconds']) for x in item['target'])
 if deadline-time.time()<estimate*1.2+60:raise RuntimeError('deadline guard: insufficient time for paired continuation')
 x=dict(variant=m['name'],source_commit=m['source_commit'],run=k,**run_one(item['binary'],r/'timing'/f'n1001-run{k}',1001,0,timeout=min(estimate*1.5+30,deadline-time.time()-30)))
 compare(pathlib.Path(m['baseline'])/'source/identity-ref.png',pathlib.Path(x['directory'])/'identity.png')
 item['records'].append(x);item['target'].append(x)
 with (r/'measurements.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(x));w.writeheader();w.writerows(item['records'])
 print(json.dumps(x),flush=True)
summary=[]
for item in items:
 v=[float(x['wall_seconds']) for x in item['target']]
 summary.append(dict(variant=item['manifest']['name'],source_commit=item['manifest']['source_commit'],values_seconds=v,median_seconds=statistics.median(v),min_seconds=min(v),max_seconds=max(v),mean_seconds=statistics.mean(v),sample_sd_seconds=statistics.stdev(v)))
for item in items:(item['root']/'paired-target-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary),flush=True)
