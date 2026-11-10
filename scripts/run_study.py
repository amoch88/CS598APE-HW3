#!/usr/bin/env python3
"""After release timing: inexpensive exploratory profiles, then full correctness."""
import argparse, datetime, json, pathlib, shutil, subprocess, sys, time, traceback
ROOT=pathlib.Path(__file__).resolve().parents[1]
SIZES=[1,2,3,4,5,6,7,8,15,16,31,32,101,251,1001]

def main():
    p=argparse.ArgumentParser(); p.add_argument('results',type=pathlib.Path); a=p.parse_args(); r=a.results.resolve()
    def event(phase,status='START'):
        value=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase=phase,status=status)
        (r/'workflow-status.json').write_text(json.dumps(value,indent=2)+'\n'); print(json.dumps(value),flush=True)
    def run(command,directory,name,check=True,timeout=None):
        with (directory/(name+'.stdout')).open('w') as out,(directory/(name+'.stderr')).open('w') as err:
            command=list(map(str,command)); print(json.dumps({'command':command,'cwd':str(directory)}),flush=True)
            result=subprocess.run(command,cwd=directory,stdout=out,stderr=err,timeout=timeout)
        if check and result.returncode: raise RuntimeError(f'{name} failed with exit {result.returncode}')
        return result.returncode
    try:
        event('waiting-for-three-release-timings')
        pid=int((r/'benchmark.pid').read_text())
        while not (r/'timing/summary.json').exists():
            stat=pathlib.Path(f'/proc/{pid}/stat')
            if not stat.exists() or stat.read_text().split()[2]=='Z': raise RuntimeError('benchmark exited without summary')
            time.sleep(2)
        event('release-timings','PASS')
        prof=r/'profiles'
        event('gprof-exploratory-n251')
        run(['gcc','-O3','-g','-pg',r/'source/sandpile.c','-o',r/'bin/baseline-gprof.exe','-lm'],prof,'build-gprof')
        d=prof/'gprof-n251'; d.mkdir()
        run(['/usr/bin/time','-v','-o',d/'resource-time.txt','taskset','-c','0',r/'bin/baseline-gprof.exe','251'],d,'run',timeout=120)
        run(['gprof','-b','-p',r/'bin/baseline-gprof.exe',d/'gmon.out'],d,'flat-profile')
        run(['gprof','-b','-p','-l',r/'bin/baseline-gprof.exe',d/'gmon.out'],d,'line-profile')
        event('gprof-exploratory-n251','PASS')
        event('diagnostic-exploratory-n251')
        generated=prof/'diagnostic.c'
        run([sys.executable,ROOT/'scripts/diagnostic_source.py',r/'source/sandpile.c',generated],prof,'generate-diagnostic')
        run(['gcc','-O3','-g','-Werror','-I',r/'source',generated,'-o',r/'bin/diagnostic.exe','-lm'],prof,'build-diagnostic')
        d=prof/'diagnostic-n251'; d.mkdir()
        run(['/usr/bin/time','-v','-o',d/'resource-time.txt','taskset','-c','0',r/'bin/diagnostic.exe','251'],d,'run',timeout=120)
        event('diagnostic-exploratory-n251','PASS')
        event('callgrind-exploratory-n101')
        d=prof/'callgrind-n101'; d.mkdir()
        run(['taskset','-c','0','valgrind','--tool=callgrind','--callgrind-out-file='+str(d/'callgrind.out'),r/'bin/baseline.exe','101'],d,'run',timeout=600)
        run(['callgrind_annotate','--inclusive=no','--threshold=99',d/'callgrind.out'],d,'annotated')
        event('callgrind-exploratory-n101','PASS')
        run(['taskset','-c','0',sys.executable,'-m','unittest','discover','-s',ROOT/'tests','-p','test_*.py','-v'],prof,'decoder-tests')
        event('correctness-including-full-target')
        cmd=['taskset','-c','0',sys.executable,ROOT/'scripts/check.py','--source',r/'source/sandpile.c','--binary',r/'bin/baseline.exe',
            '--output',r/'correctness','--reference-png',r/'source/identity-ref.png','--target-png',r/'timing/run-01/identity.png']
        correctness_rc=run(cmd,r,'correctness',check=False)
        event('correctness-including-full-target','PASS' if correctness_rc==0 else 'FAIL')
        sys.path.insert(0,str(ROOT/'scripts'))
        from check import load_grid,compare_grids
        from png_pixels import compare
        d=prof/'diagnostic-n251'
        compare_grids(load_grid(r/'correctness/n251/identity.grid'),load_grid(d/'phase-2.grid'))
        pixel_check=compare(r/'correctness/n251/identity.png',d/'identity.png')
        (d/'comparison.json').write_text(json.dumps({'all_integer_cells':'PASS','decoded_pixels':pixel_check},indent=2)+'\n')
        compare(r/'correctness/n251/identity.png',prof/'gprof-n251/identity.png')
        compare(r/'correctness/n101/identity.png',prof/'callgrind-n101/identity.png')
        event('profile-output-comparisons','PASS')
        event('memory-safety')
        run(['gcc','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',r/'source/sandpile.c','-o',r/'bin/baseline-asan.exe','-lm'],prof,'build-sanitizers')
        memory_checks=[]
        for n in [1,2,3,4,31,32,101]:
            d=prof/f'asan-n{n}'; d.mkdir()
            rc=run(['env','UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1','ASAN_OPTIONS=detect_leaks=1:halt_on_error=1',r/'bin/baseline-asan.exe',n],d,'run',check=False,timeout=120)
            memory_checks.append({'tool':'ASan/UBSan','size':n,'exit_status':rc,'status':'PASS' if rc==0 else 'FAIL','log':str(d/'run.stderr')})
        d=prof/'memcheck-n101'; d.mkdir()
        rc=run(['valgrind','--leak-check=full','--show-leak-kinds=all','--errors-for-leak-kinds=all','--error-exitcode=99',r/'bin/baseline.exe','101'],d,'run',check=False,timeout=600)
        memory_checks.append({'tool':'Valgrind Memcheck','size':101,'exit_status':rc,'status':'PASS' if rc==0 else 'FAIL','log':str(d/'run.stderr')})
        memory_ok=all(v['status']=='PASS' for v in memory_checks)
        (r/'memory-safety.json').write_text(json.dumps(memory_checks,indent=2)+'\n')
        event('memory-safety','PASS' if memory_ok else 'FAIL')
        for n in SIZES:
            dest=r/'golden'/f'n{n}'; dest.mkdir()
            for name in ['identity.grid','identity.png']:
                shutil.copy2(r/'correctness'/f'n{n}'/name,dest/name); (dest/name).chmod(0o444)
        (r/'golden/manifest.json').write_text(json.dumps({'source_commit':(r/'source-commit.txt').read_text().strip(),'sizes':SIZES},indent=2)+'\n')
        for directory in (r/'golden').iterdir():
            if directory.is_dir(): directory.chmod(0o555)
        event('complete',('PASS' if memory_ok else 'COMPLETE_WITH_FINDINGS') if correctness_rc==0 else 'FAIL')
        if correctness_rc: raise RuntimeError('correctness checks reported failure; see report')
    except BaseException:
        (r/'workflow-error.txt').write_text(traceback.format_exc()); event('workflow','FAIL'); raise
if __name__=='__main__': main()
