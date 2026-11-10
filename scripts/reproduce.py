#!/usr/bin/env python3
"""Build the immutable starter, measure release runs, then check and profile it."""
import argparse, datetime, hashlib, json, os, pathlib, shutil, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='15fe837445b8e32a15ac61fcfa388980b54d9173'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--runs',type=int,default=3)
    a=p.parse_args(); r=a.output.resolve(); r.mkdir(parents=True,exist_ok=False)
    for name in ['source','bin','golden','profiles']: (r/name).mkdir()
    with (r/'baseline-source.tar').open('wb') as archive:
        subprocess.run(['git','archive','--format=tar',BASE],cwd=ROOT,stdout=archive,check=True)
    subprocess.run(['tar','-xf',r/'baseline-source.tar','-C',r/'source'],check=True)
    (r/'source-commit.txt').write_text(BASE+'\n')
    (r/'infrastructure-commit.txt').write_text(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True))
    (r/'infrastructure-status.txt').write_text(subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT,text=True))
    command=['make','-C',str(r/'source'),'all','FUNC=gcc','FLAGS=-O3 -lm -g -Werror']
    (r/'build-command.json').write_text(json.dumps(command)+'\n')
    with (r/'build.log').open('w') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    shutil.copy2(r/'source/sandpile.exe',r/'bin/baseline.exe')
    commands=[['date','-u','--iso-8601=seconds'],['hostname','-f'],['uname','-a'],['cat','/etc/os-release'],
        ['lscpu'],['free','-b'],['gcc','--version'],['make','--version'],['python3','--version'],
        ['perf','--version'],['valgrind','--version'],['/usr/bin/time','--version'],['taskset','-pc',str(os.getpid())],
        ['cat','/proc/sys/kernel/perf_event_paranoid'],['uptime']]
    with (r/'environment.txt').open('w') as out:
        for cmd in commands:
            out.write('$ '+' '.join(cmd)+'\n'); out.flush()
            subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,check=False)
    with (r/'build.sha256').open('w') as out:
        for file in [r/'baseline-source.tar',r/'bin/baseline.exe',r/'source/sandpile.c',r/'source/stb_image_write.h']:
            out.write(hashlib.sha256(file.read_bytes()).hexdigest()+'  '+str(file)+'\n')
    for name,events in [('software','task-clock'),('hardware','cycles,instructions')]:
        with (r/'profiles'/f'perf-{name}-check.txt').open('w') as out:
            result=subprocess.run(['perf','stat','-e',events,'--','true'],stdout=out,stderr=subprocess.STDOUT)
        (r/'profiles'/f'perf-{name}-exit-status.txt').write_text(str(result.returncode)+'\n')
    with (r/'benchmark.log').open('w') as out:
        process=subprocess.Popen([sys.executable,'-u',str(ROOT/'scripts/benchmark.py'),'--binary',str(r/'bin/baseline.exe'),
            '--output',str(r/'timing'),'--runs',str(a.runs),'--cpu','0'],stdout=out,stderr=subprocess.STDOUT)
        (r/'benchmark.pid').write_text(str(process.pid)+'\n')
        if process.wait(): raise RuntimeError('benchmark failed; inspect benchmark.log')
    with (r/'workflow.log').open('w') as out:
        subprocess.run([sys.executable,'-u',ROOT/'scripts/run_study.py',r],stdout=out,stderr=subprocess.STDOUT,check=True)
    subprocess.run([sys.executable,ROOT/'scripts/summarize.py',r],check=True)
    print('Completed study: '+str(r))
if __name__=='__main__': main()
