#!/usr/bin/env python3
"""Sequential end-to-end runs; each output directory must be new."""
import argparse, csv, datetime, hashlib, json, os, pathlib, statistics, subprocess, time

def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def run_one(binary, directory, n, cpu):
    directory.mkdir()
    (directory / 'proc-stat.before').write_text(pathlib.Path('/proc/stat').read_text())
    command = ['/usr/bin/time', '-f', '%e,%U,%S,%M,%x', '-o', str(directory/'gnu-time.csv'),
               'taskset', '-c', str(cpu), str(binary), str(n)]
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (directory/'stdout.txt').open('w') as out, (directory/'stderr.txt').open('w') as err:
        t0 = time.perf_counter_ns()
        p = subprocess.run(command, cwd=directory, stdout=out, stderr=err)
        duration = (time.perf_counter_ns()-t0)/1e9
    (directory/'proc-stat.after').write_text(pathlib.Path('/proc/stat').read_text())
    fields = (directory/'gnu-time.csv').read_text().strip().split(',')
    if p.returncode or len(fields) != 5:
        raise RuntimeError(f'run failed: {directory}, return code {p.returncode}')
    image = directory/'identity.png'
    if not image.is_file(): raise RuntimeError('missing identity.png')
    record = dict(start_utc=start, size=n, cpu=cpu, wall_seconds=float(fields[0]),
        user_seconds=float(fields[1]), system_seconds=float(fields[2]), max_rss_kib=int(fields[3]),
        exit_status=int(fields[4]), launcher_wall_seconds=duration, png_sha256=digest(image),
        directory=str(directory))
    (directory/'run.json').write_text(json.dumps(record, indent=2)+'\n')
    return record

def main():
    p=argparse.ArgumentParser(); p.add_argument('--binary', required=True, type=pathlib.Path)
    p.add_argument('--output', required=True, type=pathlib.Path); p.add_argument('--size', type=int, default=1001)
    p.add_argument('--runs', type=int, default=3); p.add_argument('--cpu', type=int, default=0)
    a=p.parse_args(); a.binary=a.binary.resolve(); a.output=a.output.resolve(); a.output.mkdir()
    if a.runs < 2: p.error('--runs must be at least 2 for sample standard deviation')
    manifest=dict(binary=str(a.binary), binary_sha256=digest(a.binary), size=a.size, runs=a.runs,
        cpu=a.cpu, warmup='one excluded N=101 preflight; no full-size warmup',
        timer='GNU /usr/bin/time; includes image creation and buffered PNG writing',
        flags='-O3 -lm -g -Werror', source_commit='15fe837445b8e32a15ac61fcfa388980b54d9173')
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    run_one(a.binary,a.output/'preflight-n101',101,a.cpu)
    records=[]
    with (a.output/'timings.csv').open('w',newline='') as f:
        writer=None
        for i in range(1,a.runs+1):
            r=run_one(a.binary,a.output/f'run-{i:02}',a.size,a.cpu); r={'run':i,**r}
            if writer is None: writer=csv.DictWriter(f,fieldnames=list(r)); writer.writeheader()
            writer.writerow(r); f.flush(); os.fsync(f.fileno()); records.append(r)
            print(json.dumps(r),flush=True)
    times=[r['wall_seconds'] for r in records]
    q=statistics.quantiles(times,n=4,method='inclusive')
    summary=dict(n=len(times),median_seconds=statistics.median(times),min_seconds=min(times),
        max_seconds=max(times),mean_seconds=statistics.mean(times),sample_sd_seconds=statistics.stdev(times),
        q1_seconds=q[0],q3_seconds=q[2],all_png_hashes_equal=len({r['png_sha256'] for r in records})==1)
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)
if __name__=='__main__': main()
