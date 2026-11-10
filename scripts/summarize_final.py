#!/usr/bin/env python3
"""Preserve compact original evidence and derive paper tables from measured CSVs."""
import argparse,csv,hashlib,json,pathlib,shutil,statistics,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--baseline',type=pathlib.Path,required=True);p.add_argument('--row',type=pathlib.Path,required=True)
p.add_argument('--studies',nargs='+',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True)
a=p.parse_args();out=a.output.resolve();out.mkdir();b=a.baseline.resolve();row=a.row.resolve();records=[];variants={}
def ingest(path,variant,commit,filter_fn=lambda x:True):
    for x in csv.DictReader(path.open()):
        if filter_fn(x): records.append(dict(variant=variant,source_commit=commit,size=int(x['size']),run=int(x['run']),wall_seconds=float(x['wall_seconds']),user_seconds=float(x['user_seconds']),system_seconds=float(x['system_seconds']),max_rss_kib=int(x['max_rss_kib']),png_sha256=x['png_sha256'],origin=str(path),run_directory=x['directory']))
base='15fe837445b8e32a15ac61fcfa388980b54d9173';ri='7fd71987e27f00d690e5e0348d5701a76a12ca0b'
ingest(b/'timing/timings.csv','original',base)
ingest(row/'timing/measurements.csv','original',base,lambda x:x['variant']=='baseline' and int(x['size'])!=1001)
ingest(row/'timing/measurements.csv','row-intervals',ri,lambda x:x['variant']=='candidate')
variants['original']={'source_commit':base,'results':str(b),'status':'previously verified'}
variants['row-intervals']={'source_commit':ri,'results':str(row),'status':'previously verified'}
for study in a.studies:
    study=study.resolve();m=json.loads((study/'manifest.json').read_text());name=m['name'];status=json.loads((study/'status.json').read_text())
    variants[name]={'source_commit':m['source_commit'],'results':str(study),'status':status}
    if (study/'measurements.csv').exists(): ingest(study/'measurements.csv',name,m['source_commit'])
    dest=out/name;dest.mkdir()
    names=['manifest.json','status.json','environment.txt','environment-comparison.json','build-hashes.json','commands.jsonl','measurements.csv','stages.json','memory-safety.json','error.txt','workflow-interruption.json','repeat-manifest.json','final-validation.json','final-clean-build.log','post-rebuild-correctness/report.json','post-rebuild-overflow/report.json','callgrind-n101/summary.json','callgrind-n101/run.stderr','callgrind-n101/annotated.txt']
    names += ['small-correctness/report.json','target-correctness/report.json','overflow-checks/report.json','memcheck-n101/run.stderr']
    names += [f'diagnostic-n{n}/phase-{k}.json' for n in [2,31,32,251] for k in [1,2]]
    names += [f'asan-n{n}/run.stderr' for n in [1,2,3,4,31,32,101]]
    for name2 in names:
        src=study/name2
        if src.is_file():
            d=dest/name2;d.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(src,d)
    for path in sorted((study/'timing').glob('*/run.json')):
        d=dest/'timing'/path.parent.name;d.mkdir(parents=True)
        for name2 in ['run.json','gnu-time.csv']:
            shutil.copy2(path.parent/name2,d/name2)
with (out/'timings.csv').open('x',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
summary=[]
for name in variants:
    for n in [101,251,501,1001]:
        values=[v['wall_seconds'] for v in records if v['variant']==name and v['size']==n]
        if not values: continue
        med=statistics.median(values)
        refs={v:statistics.median(x['wall_seconds'] for x in records if x['variant']==v and x['size']==n) for v in ['original','row-intervals']}
        summary.append(dict(variant=name,size=n,count=len(values),values_seconds=values,median_seconds=med,min_seconds=min(values),max_seconds=max(values),mean_seconds=statistics.mean(values),sample_sd_seconds=statistics.stdev(values) if len(values)>1 else None,speedup_original=refs['original']/med,speedup_row=refs['row-intervals']/med))
(out/'summary.json').write_text(json.dumps(dict(variants=variants,measurements=summary),indent=2)+'\n')
lines=['| Configuration | N | Runs (seconds) | Median | Range | Sample SD | vs original | vs rows |','|---|---:|---|---:|---|---:|---:|---:|']
for x in summary:
    sd='unavailable (one run)' if x['sample_sd_seconds'] is None else f"{x['sample_sd_seconds']:.4f}"
    lines.append(f"| {x['variant']} | {x['size']} | {', '.join(f'{v:.2f}' for v in x['values_seconds'])} | {x['median_seconds']:.2f} | {x['min_seconds']:.2f}?{x['max_seconds']:.2f} | {sd} | {x['speedup_original']:.3f}x | {x['speedup_row']:.3f}x |")
(out/'tables.md').write_text('\n'.join(lines)+'\n')
hashes={str(x.relative_to(out)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(out.rglob('*')) if x.is_file()}
(out/'manifest.json').write_text(json.dumps(dict(files=hashes,baseline_results=str(b),row_results=str(row),generator_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),generator_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
print(out/'tables.md')
