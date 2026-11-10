#!/usr/bin/env python3
"""Bounded, sequential validation and release timing for an archived source commit."""
import argparse, csv, datetime, hashlib, json, os, pathlib, signal, subprocess, sys, time, traceback
from zoneinfo import ZoneInfo
from benchmark import run_one, digest
from check import compare_grids, load_grid, reference_stabilize
from png_pixels import compare
ROOT=pathlib.Path(__file__).resolve().parents[1]
SMALL=[1,2,3,4,5,6,7,8,15,16,31,32,101,251,501]
SUPPORT=r"""
struct work_stats { uint64_t sweeps, visits, events, unit_topplings; };
static struct work_stats work;
static int phase_number;
static void save_phase(void) {
  char name[64]; ++phase_number;
  snprintf(name,sizeof(name),"phase-%d.grid",phase_number);
  FILE *f=fopen(name,"wx"); if(!f) die("phase output exists");
  fprintf(f,"%d\n",N);
  for(int i=0;i<N;i++) for(int j=0;j<N;j++)
    fprintf(f,"%d%c",grid[i][j],j==N-1?'\n':' ');
  if(fclose(f)) die("phase write failed");
  snprintf(name,sizeof(name),"phase-%d.json",phase_number);
  f=fopen(name,"wx"); if(!f) die("counter output exists");
  fprintf(f,"{\"phase\":%d,\"sweeps\":%"PRIu64",\"visits\":%"PRIu64",\"events\":%"PRIu64",\"unit_topplings\":%"PRIu64"}\n",
    phase_number,work.sweeps,work.visits,work.events,work.unit_topplings);
  if(fclose(f)) die("counter write failed");
}
"""
def instrument(source):
    s=source.read_text()
    s=s.replace('static void stabilize() {',SUPPORT+'\nstatic void stabilize() {\n  memset(&work,0,sizeof(work));',1)
    if 'while (pending)' in s:
        s=s.replace('  while (pending) {','  while (pending) {\n    work.visits++;',1)
    else:
        s=s.replace('    changed = 0;','    changed = 0;\n    work.sweeps++;',1)
        s=s.replace('        if (grid[i][j] < 4)','        work.visits++;\n        if (grid[i][j] < 4)',1)
    anchor='grid[i][j] -= 4 * q;'
    if s.count(anchor)!=1: raise ValueError('missing unique toppling instrumentation anchor')
    s=s.replace(anchor,'work.events++; work.unit_topplings += (uint64_t)q;\n        '+anchor,1)
    if s.count('  stabilize();')!=2: raise ValueError('expected two identity phases')
    return s.replace('  stabilize();','  stabilize();\n  save_phase();')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit',required=True); p.add_argument('--name',required=True)
    p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--baseline',type=pathlib.Path,default=ROOT/'results/latest-baseline')
    p.add_argument('--row-results',type=pathlib.Path,default=ROOT/'results/latest-row-intervals')
    p.add_argument('--target-runs',type=int,default=1)
    p.add_argument('--skip-target',action='store_true')
    p.add_argument('--deadline',help='ISO Central time; reserve 5 minutes after this workflow')
    a=p.parse_args(); r=a.output.resolve(); b=a.baseline.resolve(); row=a.row_results.resolve(); r.mkdir()
    deadline=datetime.datetime.fromisoformat(a.deadline).replace(tzinfo=ZoneInfo('America/Chicago')).timestamp() if a.deadline else float('inf')
    def remaining(): return deadline-time.time()
    def save(name,obj): (r/name).write_text(json.dumps(obj,indent=2)+'\n')
    def event(phase,status='START'):
        x=dict(central_time=datetime.datetime.now(ZoneInfo('America/Chicago')).isoformat(),phase=phase,status=status)
        save('status.json',x); print(json.dumps(x),flush=True)
    def run(cmd,d,name,timeout=300,pin=True):
        cmd=list(map(str,cmd)); cmd=(['taskset','-c','0']+cmd) if pin else cmd
        with (r/'commands.jsonl').open('a') as f: f.write(json.dumps(dict(command=cmd,cwd=str(d)))+'\n')
        with (d/(name+'.stdout')).open('w') as out,(d/(name+'.stderr')).open('w') as err:
            proc=subprocess.Popen(cmd,cwd=d,stdout=out,stderr=err,start_new_session=True)
            try: rc=proc.wait(timeout=max(1,min(timeout,remaining())))
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL); proc.wait(); raise
        if rc: raise RuntimeError(f'{name} exited {rc}; see {d}')
    try:
        commit=subprocess.check_output(['git','rev-parse',a.commit],cwd=ROOT,text=True).strip()
        save('manifest.json',dict(name=a.name,source_commit=commit,cpu=0,flags='-O3 -lm -g -Werror',baseline=str(b),row_results=str(row),target_runs_requested=a.target_runs,deadline=a.deadline))
        event('build-and-environment')
        with (r/'environment.txt').open('w') as f:
            for cmd in [['date'],['hostname','-f'],['uname','-a'],['lscpu'],['gcc','--version'],['python3','--version'],['uptime']]:
                subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
        old=(b/'environment.txt').read_text(); current=(r/'environment.txt').read_text()
        checks={k:subprocess.check_output(cmd,text=True).strip() in old for k,cmd in [('hostname',['hostname','-f']),('kernel',['uname','-r'])]}
        gcc=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0]
        model=next(x for x in subprocess.check_output(['lscpu'],text=True).splitlines() if x.startswith('Model name:'))
        checks.update(gcc=gcc in old,cpu_model=model in old,cpu0=0 in os.sched_getaffinity(0)); save('environment-comparison.json',checks)
        assert all(checks.values()),checks
        (r/'source').mkdir(); (r/'bin').mkdir(); (r/'timing').mkdir()
        with (r/'source.tar').open('wb') as f: subprocess.run(['git','archive',commit],cwd=ROOT,stdout=f,check=True)
        run(['tar','-xf',r/'source.tar','-C',r/'source'],r,'extract',pin=False)
        run(['make','clean','all'],r/'source','build',pin=False)
        source=r/'source/sandpile.c'; binary=r/'source/sandpile.exe'
        save('build-hashes.json',dict(source=digest(source),binary=digest(binary),archive=digest(r/'source.tar')))
        event('small-correctness')
        run([sys.executable,ROOT/'scripts/check.py','--source',source,'--binary',binary,'--output',r/'small-correctness','--reference-png',b/'source/identity-ref.png','--golden',row/'expected','--sizes',*SMALL],r,'small-correctness',timeout=600)
        assert json.loads((r/'small-correctness/report.json').read_text())['status']=='PASS'
        event('both-stages-and-work-counters')
        diag=r/'diagnostic.c'; diag.write_text(instrument(source)); exe=r/'bin/diagnostic.exe'
        run(['gcc','-O3','-g','-Werror','-I',r/'source',diag,'-o',exe,'-lm'],r,'build-diagnostic',pin=False)
        stages=[]
        for n in [2,31,32,251]:
            d=r/f'diagnostic-n{n}'; d.mkdir(); run([exe,n],d,'run',timeout=180)
            if n==251: expected=[load_grid(b/'profiles/diagnostic-n251'/f'phase-{k}.grid') for k in [1,2]]
            else:
                first=reference_stabilize([[6]*n for _ in range(n)])
                expected=[first,reference_stabilize([[6-v for v in line] for line in first])]
            for k,values in enumerate(expected,1): compare_grids(values,load_grid(d/f'phase-{k}.grid'))
            stages.append(dict(size=n,status='PASS',phases=[json.loads((d/f'phase-{k}.json').read_text()) for k in [1,2]]))
        save('stages.json',stages)
        event('memory-safety')
        asan=r/'bin/asan.exe'
        run(['gcc','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',source,'-o',asan,'-lm'],r,'build-asan',pin=False)
        memory=[]
        for n in [1,2,3,4,31,32,101]:
            d=r/f'asan-n{n}'; d.mkdir(); run(['env','UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1','ASAN_OPTIONS=detect_leaks=1:halt_on_error=1',asan,n],d,'run',timeout=120)
            memory.append(dict(tool='ASan/UBSan',size=n,status='PASS'))
        d=r/'memcheck-n101'; d.mkdir()
        run(['valgrind','--leak-check=full','--show-leak-kinds=all','--errors-for-leak-kinds=all','--error-exitcode=99',binary,101],d,'run',timeout=120)
        memory.append(dict(tool='Memcheck',size=101,status='PASS')); save('memory-safety.json',memory)
        event('small-release-timing')
        records=[]
        def measure(n,k,limit):
            # Read actual Central time immediately before every target measurement.
            subprocess.run(['env','TZ=America/Chicago','date'],check=True)
            if remaining()<limit+60: raise RuntimeError('deadline guard: insufficient time')
            record=dict(variant=a.name,source_commit=commit,run=k,**run_one(binary,r/'timing'/f'n{n}-run{k}',n,0,timeout=limit))
            compare(row/'expected'/f'n{n}'/'identity.png',pathlib.Path(record['directory'])/'identity.png')
            records.append(record)
            with (r/'measurements.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(record)); w.writeheader(); w.writerows(records)
            print(json.dumps(record),flush=True); return record
        # Same excluded N=101 preflight as prior studies; no target warmup.
        run_one(binary,r/'timing/preflight-n101',101,0,timeout=60)
        for n in [101,251,501]:
            for k in range(1,4): measure(n,k,90)
        if not a.skip_target:
            event('target-release-first')
            first=measure(1001,1,480)
            event('target-integer-correctness')
            subprocess.run(['env','TZ=America/Chicago','date'],check=True)
            if remaining()<first['wall_seconds']*1.3+60: raise RuntimeError('insufficient time for target correctness')
            run([sys.executable,ROOT/'scripts/check.py','--source',source,'--binary',binary,'--output',r/'target-correctness','--reference-png',b/'source/identity-ref.png','--golden',row/'expected','--sizes',1001,'--target-png',pathlib.Path(first['directory'])/'identity.png'],r,'target-correctness',timeout=480)
            assert json.loads((r/'target-correctness/report.json').read_text())['status']=='PASS'
            for k in range(2,a.target_runs+1): measure(1001,k,480)
        event('complete','PASS')
    except BaseException:
        (r/'error.txt').write_text(traceback.format_exc()); event('workflow','FAIL'); raise
if __name__=='__main__': main()
