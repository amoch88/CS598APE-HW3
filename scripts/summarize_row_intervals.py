#!/usr/bin/env python3
"""Recompute row-interval comparison metrics from completed raw evidence."""
import argparse, hashlib, json, pathlib, re

def read(path): return json.loads(path.read_text())
def instruction_refs(path):
    match=re.search(r'Collected\s*:\s*(\d+)',path.read_text())
    if not match: raise ValueError(f'missing Callgrind Ir total: {path}')
    return int(match[1])

def main():
    p=argparse.ArgumentParser(); p.add_argument('results',type=pathlib.Path); a=p.parse_args(); r=a.results.resolve()
    status=read(r/'status.json')
    if status['phase']!='complete' or status['status']!='PASS': raise RuntimeError('study is not complete')
    manifest=read(r/'experiment-manifest.json'); b=pathlib.Path(manifest['baseline_results'])
    correctness=read(r/'correctness/report.json'); masks=read(r/'mask-report.json'); stages=read(r/'stage-report.json')
    if correctness['status']!='PASS' or len(correctness['checks'])!=63: raise AssertionError('incomplete correctness')
    if masks['status']!='PASS' or stages['status']!='PASS': raise AssertionError('mask/stage failure')
    if any(x['exit_status'] for x in read(r/'memory-safety.json')): raise AssertionError('memory-safety failure')
    old=read(b/'profiles/diagnostic-n251/diagnostics.json'); new=read(r/'diagnostics/n251/diagnostics.json')
    for x,y in zip(old['phases'],new['phases']):
        for key in ['sweeps','unit_topplings','q_histogram_0_to_7_then_8plus']:
            if x[key]!=y[key]: raise AssertionError('toppling trace changed')
    old_scans=sum(x['scan_visits'] for x in old['phases']); new_scans=sum(x['scan_visits'] for x in new['phases'])
    predicate_evaluations=2*old['scan_cells_per_sweep']
    target=next(x for x in masks['checks'] if x['size']==1001)
    baseline_ir=instruction_refs(b/'profiles/callgrind-n101/run.stderr')
    candidate_ir=instruction_refs(r/'callgrind-n101/run.stderr')
    result=dict(candidate_source_commit=manifest['candidate_source_commit'],baseline_source_commit=manifest['baseline_source_commit'],
        correctness_entries=len(correctness['checks']),mask_sizes=len(masks['sizes']),mask_positions=masks['total_positions'],
        benchmarks=read(r/'benchmark-summary.json'),
        work_n251=dict(baseline_sweeps=[x['sweeps'] for x in old['phases']],candidate_sweeps=[x['sweeps'] for x in new['phases']],
            baseline_unit_topplings=[x['unit_topplings'] for x in old['phases']],candidate_unit_topplings=[x['unit_topplings'] for x in new['phases']],
            baseline_scan_visits=old_scans,candidate_scan_visits=new_scans,scan_reduction_percent=100*(1-new_scans/old_scans),
            baseline_geometry_evaluations=old_scans,candidate_precompute_geometry_evaluations=predicate_evaluations,
            geometry_evaluation_reduction_percent=100*(1-predicate_evaluations/old_scans)),
        per_sweep_n1001=dict(baseline_positions=target['original_scan_cells'],candidate_positions=target['active_cells'],
            reduction_percent=100*(1-target['active_cells']/target['original_scan_cells'])),
        callgrind_n101=dict(baseline_instruction_refs=baseline_ir,candidate_instruction_refs=candidate_ir,
            reduction_percent=100*(1-candidate_ir/baseline_ir)),
        limitations=['N=1001 baseline is historical and unpaired; three observations per retained variant',
            'GNU time 0.01-second resolution is coarse for N=101',
            'N=251 instrumented work counts and N=101 instruction counts are exploratory; no hardware cache/IPC measurements'],
        analysis_script_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
    with (r/'analysis.json').open('x') as out: out.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
