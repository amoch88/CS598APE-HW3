#!/usr/bin/env python3
"""Validate and benchmark only active-row intervals; reuse a completed baseline."""
import argparse, csv, datetime, hashlib, json, os, pathlib, random, shutil, statistics, subprocess, sys, traceback
from benchmark import run_one, digest
from check import compare_grids, load_grid, reference_stabilize
from png_pixels import compare
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='15fe837445b8e32a15ac61fcfa388980b54d9173'
SIZES=[1,2,3,4,5,6,7,8,15,16,31,32,101,251,501,1001]
MASK_SIZES=sorted(set(range(1,129))|{250,251,252,500,501,502,999,1000,1001,1002})

def stats(records):
    values=[float(x['wall_seconds']) for x in records]
    return dict(n=len(values),values_seconds=values,median_seconds=statistics.median(values),
        min_seconds=min(values),max_seconds=max(values),mean_seconds=statistics.mean(values),
        sample_sd_seconds=statistics.stdev(values) if len(values)>1 else None)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-results',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--candidate-commit',default='HEAD')
    a=p.parse_args(); b=a.baseline_results.resolve(); r=a.output.resolve()
    r.mkdir(parents=True,exist_ok=True)
    if (r/'experiment-manifest.json').exists(): raise RuntimeError('refusing existing experiment')
    commit=subprocess.check_output(['git','rev-parse',a.candidate_commit],cwd=ROOT,text=True).strip()
    manifest=dict(baseline_source_commit=BASE,candidate_source_commit=commit,baseline_results=str(b),cpu=0,
        flags='-O3 -lm -g -Werror',historical_target_baseline=True,release_target_runs_requested=3,
        exploratory_sizes=[101,251,501],correctness_sizes=SIZES,seed=598)
    (r/'experiment-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    def save(name,value): (r/name).write_text(json.dumps(value,indent=2)+'\n')
    def event(phase,status='START'):
        value=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase=phase,status=status)
        save('status.json',value); print(json.dumps(value),flush=True)
    def run(command,directory,name,check=True,timeout=None,pin=True):
        command=list(map(str,command)); command=(['taskset','-c','0']+command) if pin else command
        with (directory/(name+'.stdout')).open('w') as out,(directory/(name+'.stderr')).open('w') as err:
            print(json.dumps({'command':command,'cwd':str(directory)}),flush=True)
            result=subprocess.run(command,cwd=directory,stdout=out,stderr=err,timeout=timeout)
        if check and result.returncode: raise RuntimeError(f'{name}: exit {result.returncode}; inspect logs')
        return result.returncode
    try:
        event('environment-and-build')
        baseline_env=(b/'environment.txt').read_text()
        current_gcc=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0]
        current_cpu=next(x.split(':',1)[1].strip() for x in subprocess.check_output(['lscpu'],text=True).splitlines() if x.startswith('Model name:'))
        current_kernel=subprocess.check_output(['uname','-r'],text=True).strip()
        current_host=subprocess.check_output(['hostname','-f'],text=True).strip()
        environment_matches=dict(gcc=current_gcc in baseline_env,cpu_model=current_cpu in baseline_env,
            kernel=current_kernel in baseline_env,hostname=current_host in baseline_env,cpu0_available=0 in os.sched_getaffinity(0))
        save('environment-comparison.json',environment_matches)
        if not all(environment_matches.values()): raise RuntimeError('environment differs; do not silently reuse historical baseline')
        with (r/'environment.txt').open('w') as out:
            for command in [['date','-u','--iso-8601=seconds'],['hostname','-f'],['uname','-a'],['cat','/etc/os-release'],
                ['lscpu'],['free','-b'],['gcc','--version'],['make','--version'],['python3','--version'],['valgrind','--version'],
                ['/usr/bin/time','--version'],['uptime']]:
                out.write('$ '+' '.join(command)+'\n'); out.flush()
                subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,check=True)
        run(['sha256sum','-c',b/'build.sha256'],r,'baseline-integrity',pin=False)
        for name in ['source','bin','expected','diagnostics','timing']: (r/name).mkdir()
        with (r/'candidate-source.tar').open('wb') as out:
            subprocess.run(['git','archive','--format=tar',commit],cwd=ROOT,stdout=out,check=True)
        run(['tar','-xf',r/'candidate-source.tar','-C',r/'source'],r,'extract',pin=False)
        if 'precompute_active_rows' not in (r/'source/sandpile.c').read_text(): raise RuntimeError('candidate is not the row-interval implementation')
        run(['make','-C',r/'source','all','FUNC=gcc','FLAGS=-O3 -lm -g -Werror'],r,'build',pin=False)
        shutil.copy2(r/'source/sandpile.exe',r/'bin/candidate.exe')
        source=r/'source/sandpile.c'; candidate=r/'bin/candidate.exe'; baseline=b/'bin/baseline.exe'
        save('build-hashes.json',{'candidate_source_sha256':digest(source),'candidate_binary_sha256':digest(candidate),
            'baseline_binary_sha256':digest(baseline),'candidate_archive_sha256':digest(r/'candidate-source.tar')})
        event('mask-equivalence')
        mask=r/'bin/mask.exe'
        run(['gcc','-O3','-g','-Werror',f'-DSANDPILE_SOURCE="{source}"',ROOT/'tests/row_intervals_driver.c','-o',mask,'-lm'],r,'build-mask',pin=False)
        checks=[]
        for n in MASK_SIZES:
            result=subprocess.check_output(['taskset','-c','0',str(mask),str(n)],text=True)
            item=json.loads(result); assert item['mismatches']==0; checks.append(item)
        save('mask-report.json',{'status':'PASS','sizes':MASK_SIZES,'checks':checks,'total_positions':sum(x['cells_compared'] for x in checks)})
        event('mask-equivalence','PASS')
        event('both-stabilization-stages')
        generated=r/'diagnostics/candidate.c'
        run([sys.executable,ROOT/'scripts/diagnostic_source.py',source,generated],r/'diagnostics','generate',pin=False)
        run(['gcc','-O3','-g','-Werror','-I',r/'source',generated,'-o',r/'bin/diagnostic.exe','-lm'],r/'diagnostics','build',pin=False)
        stage_checks=[]
        for n in [2,31,32,251]:
            d=r/'diagnostics'/f'n{n}'; d.mkdir()
            run([r/'bin/diagnostic.exe',n],d,'run')
            if n==251:
                expected=[load_grid(b/'profiles/diagnostic-n251'/f'phase-{k}.grid') for k in [1,2]]
                original=json.loads((b/'profiles/diagnostic-n251/diagnostics.json').read_text())
                actual=json.loads((d/'diagnostics.json').read_text())
                for old,new in zip(original['phases'],actual['phases']):
                    for key in ['sweeps','unit_topplings','max_height_at_visit','q_histogram_0_to_7_then_8plus']:
                        if old[key]!=new[key]: raise AssertionError(f'toppling trace count changed: {key}')
                    if new['scan_visits']!=old['active_visits']: raise AssertionError('candidate scan count not equal to active visits')
            else:
                first=reference_stabilize([[6]*n for _ in range(n)])
                expected=[first,reference_stabilize([[6-v for v in row] for row in first])]
            for k,values in enumerate(expected,1): compare_grids(values,load_grid(d/f'phase-{k}.grid'))
            stage_checks.append({'size':n,'both_stages_all_allocated_integers':'PASS'})
        save('stage-report.json',{'status':'PASS','checks':stage_checks})
        event('both-stabilization-stages','PASS')
        event('prepare-additional-n501-golden')
        for n in SIZES:
            if n!=501: (r/'expected'/f'n{n}').symlink_to(b/'golden'/f'n{n}',target_is_directory=True)
        base_driver=r/'bin/baseline-grid-driver.exe'
        run(['gcc','-O3','-g',f'-DSANDPILE_SOURCE="{b}/source/sandpile.c"',ROOT/'tests/grid_driver.c','-o',base_driver,'-lm'],r,'build-baseline-adapter',pin=False)
        d=r/'expected/n501'; d.mkdir()
        run([base_driver,'identity','501',d/'identity.grid'],d,'generate')
        for name in ['identity.grid','identity.png']: (d/name).chmod(0o444)
        event('all-existing-correctness-plus-n501')
        run([sys.executable,ROOT/'scripts/check.py','--source',source,'--binary',candidate,'--output',r/'correctness',
            '--reference-png',b/'source/identity-ref.png','--golden',r/'expected','--sizes',*SIZES],r,'correctness')
        report=json.loads((r/'correctness/report.json').read_text())
        if report['status']!='PASS' or len(report['checks'])!=63: raise AssertionError('expected all 63 correctness entries')
        run([sys.executable,'-m','unittest','discover','-s',ROOT/'tests','-p','test_*.py','-v'],r,'decoder-tests')
        event('all-existing-correctness-plus-n501','PASS')
        event('memory-safety')
        run(['gcc','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',source,'-o',r/'bin/asan.exe','-lm'],r,'build-asan',pin=False)
        memory=[]
        for n in [1,2,3,4,31,32,101]:
            d=r/f'asan-n{n}'; d.mkdir()
            rc=run(['env','UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1','ASAN_OPTIONS=detect_leaks=1:halt_on_error=1',r/'bin/asan.exe',n],d,'run',check=False)
            memory.append({'tool':'ASan/UBSan','size':n,'exit_status':rc})
        d=r/'memcheck-n101'; d.mkdir()
        rc=run(['valgrind','--leak-check=full','--show-leak-kinds=all','--errors-for-leak-kinds=all','--error-exitcode=99',candidate,'101'],d,'run',check=False)
        memory.append({'tool':'Valgrind Memcheck','size':101,'exit_status':rc}); save('memory-safety.json',memory)
        if any(x['exit_status'] for x in memory): raise RuntimeError('memory-safety failure; no benchmarking allowed')
        event('memory-safety','PASS')
        event('exploratory-release-benchmarks')
        rng=random.Random(598); measurements=[]
        csv_path=r/'timing/measurements.csv'
        def measure(variant,n,index):
            executable=baseline if variant=='baseline' else candidate
            record={'variant':variant,'run':index,**run_one(executable,r/'timing'/f'{variant}-n{n}-run{index}',n,0)}
            compare(r/'expected'/f'n{n}'/'identity.png',pathlib.Path(record['directory'])/'identity.png')
            first=not csv_path.exists()
            with csv_path.open('a',newline='') as out:
                writer=csv.DictWriter(out,fieldnames=list(record))
                if first: writer.writeheader()
                writer.writerow(record); out.flush(); os.fsync(out.fileno())
            measurements.append(record); print(json.dumps(record),flush=True)
            return record
        for n in [101,251,501]:
            for index in range(1,4):
                order=['baseline','candidate']; rng.shuffle(order)
                for variant in order: measure(variant,n,index)
        event('exploratory-release-benchmarks','PASS')
        event('target-release-benchmarks')
        historical=list(csv.DictReader((b/'timing/timings.csv').open()))
        historical_stats=stats(historical)
        run_one(candidate,r/'timing/preflight-n101',101,0)
        for index in range(1,4):
            record=measure('candidate',1001,index)
            if index==1 and record['wall_seconds']>=historical_stats['median_seconds']:
                print('First full-size result did not improve the baseline; stop at one as authorized.',flush=True)
                break
        summaries=[]
        for n in [101,251,501,1001]:
            old=historical_stats if n==1001 else stats([v for v in measurements if v['size']==n and v['variant']=='baseline'])
            new=stats([v for v in measurements if v['size']==n and v['variant']=='candidate'])
            summaries.append({'size':n,'baseline':old,'candidate':new,'speedup':old['median_seconds']/new['median_seconds'],
                'baseline_scope':'historical target distribution' if n==1001 else 'fresh exploratory paired blocks'})
        save('benchmark-summary.json',summaries)
        event('target-release-benchmarks','PASS')
        event('exploratory-instruction-count-n101')
        d=r/'callgrind-n101'; d.mkdir()
        run(['valgrind','--tool=callgrind','--callgrind-out-file='+str(d/'callgrind.out'),candidate,'101'],d,'run',timeout=600)
        run(['callgrind_annotate','--inclusive=no','--threshold=99',d/'callgrind.out'],d,'annotated')
        compare(r/'expected/n101/identity.png',d/'identity.png')
        event('complete','PASS')
    except BaseException:
        (r/'error.txt').write_text(traceback.format_exc()); event('workflow','FAIL'); raise
if __name__=='__main__': main()
