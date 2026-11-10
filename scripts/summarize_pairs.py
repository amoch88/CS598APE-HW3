#!/usr/bin/env python3
"""Summarize preserved paired small-grid observations without pooling cohorts."""
import argparse,csv,json,pathlib,statistics
p=argparse.ArgumentParser();p.add_argument('studies',nargs='+',type=pathlib.Path);a=p.parse_args()
for root in a.studies:
 r=root.resolve();candidate=list(csv.DictReader((r/'measurements.csv').open()));parent=list(csv.DictReader((r/'parent-measurements.csv').open()));out=[]
 for n in [101,251,501]:
  c=[x for x in candidate if int(x['size'])==n];b=[x for x in parent if int(x['size'])==n]
  assert len(c)==len(b)==3
  cv=[float(x['wall_seconds']) for x in c];bv=[float(x['wall_seconds']) for x in b]
  ratios=[float(next(x for x in b if x['run']==y['run'])['wall_seconds'])/float(y['wall_seconds']) for y in c]
  out.append(dict(size=n,candidate=cv,parent=bv,median_speedup=statistics.median(bv)/statistics.median(cv),paired_block_ratios=ratios,candidate_sample_sd=statistics.stdev(cv),parent_sample_sd=statistics.stdev(bv)))
 path=r/'paired-analysis.json'
 with path.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
 print(path)
