#!/usr/bin/env python3
"""Emit an evidence summary from saved raw results, never invented defaults."""
import argparse, csv, json, pathlib, statistics, re


def profile_summary(r):
    d=json.loads((r/'profiles/diagnostic-n251/diagnostics.json').read_text()); phases=d['phases']
    scans=sum(p['scan_visits'] for p in phases); active=sum(p['active_visits'] for p in phases)
    topples=sum(p['unit_topplings'] for p in phases)
    q2=sum(p['q_histogram_0_to_7_then_8plus'][2] for p in phases)
    by_line={}
    for line in (r/'profiles/gprof-n251/line-profile.stdout').read_text().splitlines():
        match=re.search(r'^\s*([\d.]+).*stabilize \(sandpile.c:(\d+)',line)
        if match: by_line[int(match[2])]=by_line.get(int(match[2]),0)+float(match[1])
    return dict(exploratory_size=251,total_sweeps=sum(p['sweeps'] for p in phases),scan_visits=scans,
        active_visits=active,unit_topplings=topples,inactive_scan_percent=100*(scans-active)/scans,
        stable_active_visit_percent=100*(active-topples)/active,unstable_scan_visit_percent=100*topples/scans,
        q2_at_unstable_visit_percent=100*q2/topples,
        gprof_geometry_lines_81_82_percent=sum(by_line.get(n,0) for n in [81,82]),
        gprof_loop_lines_79_80_percent=sum(by_line.get(n,0) for n in [79,80]),
        gprof_stability_line_83_percent=by_line.get(83,0),
        gprof_neighbor_lines_87_to_94_percent=sum(by_line.get(n,0) for n in range(87,95)),
        gprof_subtract_line_86_percent=by_line.get(86,0))

def main():
    p=argparse.ArgumentParser(); p.add_argument('results',type=pathlib.Path); a=p.parse_args(); r=a.results.resolve()
    rows=list(csv.DictReader((r/'timing/timings.csv').open()))
    t=[float(row['wall_seconds']) for row in rows]
    result={'baseline_source_commit':(r/'source-commit.txt').read_text().strip(),'runs':rows,
        'timing_summary':json.loads((r/'timing/summary.json').read_text()),
        'correctness':json.loads((r/'correctness/report.json').read_text()),
        'diagnostics':json.loads((r/'profiles/diagnostic-n251/diagnostics.json').read_text()),
        'workflow':json.loads((r/'workflow-status.json').read_text()),
        'memory_safety':json.loads((r/'memory-safety.json').read_text()),
        'profile_derived':profile_summary(r)}
    if result['workflow']['phase']!='complete' or result['workflow']['status'] not in ('PASS','COMPLETE_WITH_FINDINGS'):
        raise RuntimeError('workflow did not complete successfully')
    expected=json.loads((r/'timing/manifest.json').read_text())['runs']
    if len(rows)!=expected or any(int(row['exit_status']) for row in rows): raise RuntimeError('incomplete or failed timing runs')
    if len({row['png_sha256'] for row in rows})!=1: raise RuntimeError('baseline output hashes differ')
    if abs(statistics.median(t)-result['timing_summary']['median_seconds'])>1e-9: raise RuntimeError('summary mismatch')
    derived=r/'profiles/derived-n251.json'
    if derived.exists():
        if json.loads(derived.read_text())!=result['profile_derived']: raise RuntimeError('derived profile mismatch')
    else:
        with derived.open('x') as f: f.write(json.dumps(result['profile_derived'],indent=2)+'\n')
    dest=r/'study-summary.json'
    with dest.open('x') as f: f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'timing':result['timing_summary'],'correctness':result['correctness']['status'],
        'diagnostics':result['diagnostics']},indent=2))
if __name__=='__main__': main()
