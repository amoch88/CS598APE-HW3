#!/usr/bin/env python3
"""Emit an evidence summary from saved raw results, never invented defaults."""
import argparse, csv, json, pathlib, statistics

def main():
    p=argparse.ArgumentParser(); p.add_argument('results',type=pathlib.Path); a=p.parse_args(); r=a.results.resolve()
    rows=list(csv.DictReader((r/'timing/timings.csv').open()))
    t=[float(row['wall_seconds']) for row in rows]
    result={'baseline_source_commit':(r/'source-commit.txt').read_text().strip(),'runs':rows,
        'timing_summary':json.loads((r/'timing/summary.json').read_text()),
        'correctness':json.loads((r/'correctness/report.json').read_text()),
        'diagnostics':json.loads((r/'profiles/diagnostic-n1001/diagnostics.json').read_text()),
        'workflow':json.loads((r/'workflow-status.json').read_text())}
    if result['workflow']['phase']!='complete' or result['workflow']['status']!='PASS':
        raise RuntimeError('workflow did not complete successfully')
    if len(rows)!=5 or any(int(row['exit_status']) for row in rows): raise RuntimeError('not five successful runs')
    if len({row['png_sha256'] for row in rows})!=1: raise RuntimeError('baseline output hashes differ')
    if abs(statistics.median(t)-result['timing_summary']['median_seconds'])>1e-9: raise RuntimeError('summary mismatch')
    dest=r/'study-summary.json'
    with dest.open('x') as f: f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'timing':result['timing_summary'],'correctness':result['correctness']['status'],
        'diagnostics':result['diagnostics']},indent=2))
if __name__=='__main__': main()
