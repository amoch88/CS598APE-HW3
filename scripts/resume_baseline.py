#!/usr/bin/env python3
"""Finish an in-flight timed run after changing the requested total to three.
Only the Python controller is replaced; its GNU time child keeps running.
"""
import csv,datetime,hashlib,json,os,pathlib,statistics,sys,time
from benchmark import run_one,digest
r=pathlib.Path(sys.argv[1]).resolve(); d=r/'timing'; timed=d/'run-02'
rows=list(csv.DictReader((d/'timings.csv').open()))
if len(rows)!=1 or (d/'run-03').exists(): raise RuntimeError('expected exactly run 1 saved and run 2 in flight')
manifest=json.loads((d/'manifest.json').read_text())
(d/'manifest.initial-five.json').write_text(json.dumps(manifest,indent=2)+'\n')
manifest['runs']=3
manifest['run_count_revision']='User requested three total while run 2 was in progress; its sandpile and GNU time processes were not interrupted.'
(d/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
pid=int((r/'second-time.pid').read_text())
while True:
    process=pathlib.Path(f'/proc/{pid}/stat')
    finished=not process.exists() or process.read_text().split()[2]=='Z'
    if finished: break
    time.sleep(1)
fields=(timed/'gnu-time.csv').read_text().strip().split(',')
if len(fields)!=5 or int(fields[4])!=0: raise RuntimeError('second GNU time run failed')
(timed/'proc-stat.after').write_text(pathlib.Path('/proc/stat').read_text())
record=dict(run=2,start_utc=datetime.datetime.fromtimestamp((timed/'proc-stat.before').stat().st_mtime,datetime.timezone.utc).isoformat(),
    size=1001,cpu=0,wall_seconds=float(fields[0]),user_seconds=float(fields[1]),system_seconds=float(fields[2]),
    max_rss_kib=int(fields[3]),exit_status=int(fields[4]),launcher_wall_seconds='',png_sha256=digest(timed/'identity.png'),directory=str(timed))
(timed/'run.json').write_text(json.dumps(record,indent=2)+'\n')
(timed/'controller-transition.json').write_text(json.dumps({'measurement_interrupted':False,
    'gnu_time_metrics':'original uninterrupted GNU time child',
    'start_utc_source':'mtime of original proc-stat.before; approximate process launch timestamp',
    'launcher_wall_seconds':'unavailable after controller replacement; intentionally blank',
    'post_stat_snapshot':'captured within polling interval after GNU time exited'},indent=2)+'\n')
with (d/'timings.csv').open('a',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writerow(record); f.flush(); os.fsync(f.fileno())
rows.append(record); print(json.dumps(record),flush=True)
third={'run':3,**run_one(r/'bin/baseline.exe',d/'run-03',1001,0)}
with (d/'timings.csv').open('a',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writerow(third); f.flush(); os.fsync(f.fileno())
rows.append(third); print(json.dumps(third),flush=True)
t=[float(row['wall_seconds']) for row in rows]; q=statistics.quantiles(t,n=4,method='inclusive')
summary=dict(n=3,median_seconds=statistics.median(t),min_seconds=min(t),max_seconds=max(t),mean_seconds=statistics.mean(t),
    sample_sd_seconds=statistics.stdev(t),q1_seconds=q[0],q3_seconds=q[2],all_png_hashes_equal=len({row['png_sha256'] for row in rows})==1)
(d/'summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary),flush=True)
