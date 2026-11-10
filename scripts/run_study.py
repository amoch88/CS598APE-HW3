#!/usr/bin/env python3
"""Run correctness and diagnostic workloads only after release timing ends."""
import argparse, datetime, json, os, pathlib, shutil, subprocess, sys, time, traceback
ROOT=pathlib.Path(__file__).resolve().parents[1]

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
        event('waiting-for-release-timings')
        pid=int((r/'benchmark.pid').read_text())
        while not (r/'timing/summary.json').exists():
            stat=pathlib.Path(f'/proc/{pid}/stat')
            if not stat.exists() or stat.read_text().split()[2]=='Z': raise RuntimeError('benchmark exited without summary')
            time.sleep(2)
        event('release-timings','PASS')
        event('correctness')
        cmd=[sys.executable,ROOT/'scripts/check.py','--source',r/'source/sandpile.c','--binary',r/'bin/baseline.exe',
            '--output',r/'correctness','--reference-png',r/'source/identity-ref.png','--target-png',r/'timing/run-01/identity.png']
        correctness_rc=run(cmd,r,'correctness',check=False)
        event('correctness','PASS' if correctness_rc==0 else 'FAIL')
        event('diagnostic-full-size')
        prof=r/'profiles'; generated=prof/'diagnostic.c'
        run([sys.executable,ROOT/'scripts/diagnostic_source.py',r/'source/sandpile.c',generated],prof,'generate-diagnostic')
        run(['gcc','-O3','-g','-Werror','-I',r/'source',generated,'-o',r/'bin/diagnostic.exe','-lm'],prof,'build-diagnostic')
        d=prof/'diagnostic-n1001'; d.mkdir()
        run(['/usr/bin/time','-v','-o',d/'resource-time.txt','taskset','-c','0',r/'bin/diagnostic.exe','1001'],d,'run')
        # Compare every allocated final integer against the uninstrumented adapter.
        sys.path.insert(0,str(ROOT/'scripts'))
        from check import load_grid,compare_grids
        from png_pixels import compare
        compare_grids(load_grid(r/'correctness/n1001/identity.grid'),load_grid(d/'phase-2.grid'))
        pixel_check=compare(r/'timing/run-01/identity.png',d/'identity.png')
        (d/'comparison.json').write_text(json.dumps({'all_integer_cells':'PASS','decoded_pixels':pixel_check},indent=2)+'\n')
        event('diagnostic-full-size','PASS')
        event('gprof-full-size')
        run(['gcc','-O3','-g','-pg',r/'source/sandpile.c','-o',r/'bin/baseline-gprof.exe','-lm'],prof,'build-gprof')
        d=prof/'gprof-n1001'; d.mkdir()
        run(['/usr/bin/time','-v','-o',d/'resource-time.txt','taskset','-c','0',r/'bin/baseline-gprof.exe','1001'],d,'run')
        run(['gprof','-b','-p',r/'bin/baseline-gprof.exe',d/'gmon.out'],d,'flat-profile')
        run(['gprof','-b','-p','-l',r/'bin/baseline-gprof.exe',d/'gmon.out'],d,'line-profile')
        compare(r/'timing/run-01/identity.png',d/'identity.png')
        event('gprof-full-size','PASS')
        event('callgrind-n101')
        d=prof/'callgrind-n101'; d.mkdir()
        run(['taskset','-c','0','valgrind','--tool=callgrind','--callgrind-out-file='+str(d/'callgrind.out'),r/'bin/baseline.exe','101'],d,'run',timeout=600)
        run(['callgrind_annotate','--inclusive=no','--threshold=99',d/'callgrind.out'],d,'annotated')
        compare(r/'correctness/n101/identity.png',d/'identity.png')
        event('callgrind-n101','PASS')
        event('memory-safety')
        run(['gcc','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',r/'source/sandpile.c','-o',r/'bin/baseline-asan.exe','-lm'],prof,'build-sanitizers')
        for n in [1,2,3,4,31,32,101]:
            d=prof/f'asan-n{n}'; d.mkdir()
            run([r/'bin/baseline-asan.exe',n],d,'run',timeout=120)
        d=prof/'memcheck-n101'; d.mkdir()
        run(['valgrind','--leak-check=full','--show-leak-kinds=all','--errors-for-leak-kinds=all','--error-exitcode=99',r/'bin/baseline.exe','101'],d,'run',timeout=600)
        event('memory-safety','PASS')
        # Frozen copies remain available even after future candidate checks.
        for n in [1,2,3,4,5,6,7,8,15,16,31,32,101,1001]:
            dest=r/'golden'/f'n{n}'; dest.mkdir()
            for name in ['identity.grid','identity.png']:
                shutil.copy2(r/'correctness'/f'n{n}'/name,dest/name)
                (dest/name).chmod(0o444)
        (r/'golden/manifest.json').write_text(json.dumps({'source_commit':(r/'source-commit.txt').read_text().strip(),'sizes':[1,2,3,4,5,6,7,8,15,16,31,32,101,1001]},indent=2)+'\n')
        for directory in (r/'golden').iterdir():
            if directory.is_dir(): directory.chmod(0o555)
        event('complete','PASS' if correctness_rc==0 else 'FAIL')
        if correctness_rc: raise RuntimeError('correctness checks reported failure; see report')
    except BaseException:
        (r/'workflow-error.txt').write_text(traceback.format_exc()); event('workflow','FAIL'); raise
if __name__=='__main__': main()
