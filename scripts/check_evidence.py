#!/usr/bin/env python3
"""Audit committed compact evidence without the VM's ignored result directories."""
import argparse,csv,hashlib,json,math,pathlib,statistics,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('evidence',type=pathlib.Path);a=p.parse_args();r=a.evidence.resolve()
manifest=json.loads((r/'manifest.json').read_text())
for name,expected in manifest['files'].items():
 actual=hashlib.sha256((r/name).read_bytes()).hexdigest();assert actual==expected,name
rows=list(csv.DictReader((r/'timings.csv').open()));summary=json.loads((r/'summary.json').read_text())
lookup={(x['variant'],int(x['size'])):x for x in summary['measurements']}
for key,item in lookup.items():
 values=[float(x['wall_seconds']) for x in rows if x['variant']==key[0] and int(x['size'])==key[1]]
 assert item['values_seconds']==values and item['count']==len(values),key
 computed=dict(median_seconds=statistics.median(values),min_seconds=min(values),max_seconds=max(values),mean_seconds=statistics.mean(values),sample_sd_seconds=statistics.stdev(values) if len(values)>1 else None)
 for name,value in computed.items():
  assert (item[name] is None and value is None) or (item[name] is not None and value is not None and math.isclose(item[name],value,rel_tol=1e-12,abs_tol=1e-12)),(key,name)
 for reference,field in [('original','speedup_original'),('row-intervals','speedup_row')]:
  expected=lookup[reference,key[1]]['median_seconds']/item['median_seconds'];assert math.isclose(item[field],expected,rel_tol=1e-12),key
for n in sorted({int(x['size']) for x in rows}):
 hashes={x['png_sha256'] for x in rows if int(x['size'])==n};assert len(hashes)==1,(n,hashes)
 if n==1001:assert hashes=={hashlib.sha256((ROOT/'identity-ref.png').read_bytes()).hexdigest()}
source_checks=0
for directory in sorted(r.iterdir()):
 if not directory.is_dir() or not (directory/'build-hashes.json').exists():continue
 meta=json.loads((directory/'manifest.json').read_text());sha=meta['source_commit']
 actual=hashlib.sha256(subprocess.check_output(['git','show',sha+':sandpile.c'],cwd=ROOT)).hexdigest()
 assert actual==json.loads((directory/'build-hashes.json').read_text())['source'],directory
 assert json.loads((directory/'small-correctness/report.json').read_text())['status']=='PASS'
 assert all(x['status']=='PASS' for x in json.loads((directory/'memory-safety.json').read_text()))
 assert all(x['status']=='PASS' for x in json.loads((directory/'stages.json').read_text()))
 if any(x['variant']==directory.name and int(x['size'])==1001 for x in rows):
  assert json.loads((directory/'target-correctness/report.json').read_text())['status']=='PASS'
 parent_csv=directory/'parent-measurements.csv'
 if parent_csv.exists():
  for x in csv.DictReader(parent_csv.open()):
   assert x['source_commit']==summary['variants'][x['variant']]['source_commit']
   assert x['png_sha256']==next(y['png_sha256'] for y in rows if int(y['size'])==int(x['size']))
 source_checks+=1
selected=json.loads((r/'selection.json').read_text())['selected'];expected=json.loads((r/selected['name']/'build-hashes.json').read_text())['source']
assert hashlib.sha256((ROOT/'sandpile.c').read_bytes()).hexdigest()==expected,'working C source differs from selected measured source'
print(f'PASS: {len(manifest["files"])} file hashes, {len(rows)} observations, {len(lookup)} statistical groups, {source_checks} source commits, all PNG hashes, and selected source')
