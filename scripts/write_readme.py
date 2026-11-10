#!/usr/bin/env python3
"""Write the final README using measured statistics and the selected source."""
import argparse,json,pathlib
p=argparse.ArgumentParser();p.add_argument('summary',type=pathlib.Path);p.add_argument('--selection',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
d=json.loads(a.summary.read_text());s=json.loads(a.selection.read_text())['selected'];name=s['name'];sha=s['source_commit'];lookup={(x['variant'],x['size']):x for x in d['measurements']};f=lookup[name,1001]
features='exact active-row intervals, legal batched topplings, a once-per-stage arithmetic bound, and padded physical boundaries'
if name=='combined':features+=', with alternating forward/reverse sweeps'
labels={'original':'Original','row-intervals':'Row intervals','row-batch-bounded':'Bounded batching','padded':'Padded boundaries','combined':'Final combined'}
text=f'''# CS598APE HW3: Abelian Sandpile identity

Compute the identity sandpile on a Pac-Man-shaped grid. The square is filled with
six grains, active cells stabilize, every stored height is complemented as
`6-height`, and the graph stabilizes again. A toppling loses four grains and
sends one to each orthogonal neighbor. Excluded in-square cells retain grains but
never topple. The program writes `identity.png` in its current directory.

![N=1001 identity reference](identity-ref.png)

## Final implementation and results

Branch **`hw3-final`** uses {features}.
The measured C source is commit **`{sha}`**; later artifact commits add evidence,
tools and documentation without changing that source. Original and experimental
branches remain available; the repository remains private.

N=1001 observations: **{', '.join(f'{v:.2f}' for v in f['values_seconds'])} seconds**.
Median **{f['median_seconds']:.2f} s**, mean {f['mean_seconds']:.2f} s,
range {f['min_seconds']:.2f}-{f['max_seconds']:.2f} s, sample SD {f['sample_sd_seconds']:.2f} s.
Speedup: **{f['speedup_original']:.3f}x** over the 646.93 s original median and
**{f['speedup_row']:.3f}x** over the 304.82 s row-interval median.

| Cumulative configuration | N=101 | N=251 | N=501 | N=1001 |
|---|---:|---:|---:|---:|
'''
for variant in dict.fromkeys(['original','row-intervals','row-batch-bounded','padded',name]):
 text+='| '+labels[variant]+' | '+' | '.join(f"{lookup[variant,n]['median_seconds']:.2f}" for n in [101,251,501,1001])+' |\n'
text+=f'''
All entries above are three-run end-to-end medians in seconds. Complete individual
and negative results are in [report notes](docs/FINAL_REPORT_NOTES.md). Checked
batching slowed down; FIFO scheduling was much slower; contiguous storage and an
explicit remainder mask showed no useful larger-size improvement. GCC generated
identical machine-code text for the remainder rewrite.

## Build and run

Requires GCC, Make and libm on Unix; Linux on the course VM is tested. The bundled
PNG writer needs no external image library. The Makefile uses
**`gcc -O3 -lm -g -Werror`**.

```bash
git clone git@github.com:amoch88/CS598APE-HW3.git
cd CS598APE-HW3
git switch hw3-final
make clean all
mkdir -p results
RUN=$(mktemp -d "$PWD/results/manual-XXXXXX")
(cd "$RUN" && taskset -c 0 "$OLDPWD/sandpile.exe" 1001)
```

A fresh working directory preserves earlier images. For routine use,
`./sandpile.exe 1001` writes in the current directory. The reference image is
`identity-ref.png`. Exact integer comparison is stronger than image comparison
because multiple integer values can render as black.

## Correctness and data audit

The selected implementation passed 63 distinct established checks across 16
identity sizes, including every allocated signed integer at N=1001, negative sink
counters, active stability, decoded reference pixels, odd/even dimensions,
independent small-grid oracles, 24 seeded random cases, mathematical identity
properties and invalid CLI cases. Both intermediate stages were checked at
N=2/31/32/251. Seven ASan/UBSan sizes, N=101 Memcheck, four arithmetic-bound/fallback
cases, a byte-identical clean rebuild, post-rebuild checks and 138 mask sizes
(5,653,280 positions) passed. No full-target intermediate baseline dumps exist;
full-target verification compares the final grid, not both intermediate stages.

Audit committed data without large VM result directories:

```bash
python3 scripts/check_evidence.py measurements/final-study
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The audit checks file hashes, raw observations against derived statistics and
speedups, PNG hashes, source commits, completed correctness reports and selected
C source. Use a full clone with the experimental branch objects available.

## Reproduce correctness and optimized timing

On the study VM, reuse the frozen original goldens:

```bash
R="$PWD/results/final-reproduction-$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/final_experiment.py \\
  --commit {sha} --name {name} --output "$R" \\
  --target-runs 3 \\
  --baseline "$PWD/results/latest-baseline" \\
  --row-results "$PWD/results/latest-row-intervals"
python3 scripts/finalize_candidate.py "$R"
```

The launcher archives the exact source, builds cleanly, checks smaller integer
states and both phases, runs arithmetic and memory checks, measures three runs
at N=101/251/501, times N=1001, compares every target integer, and completes three
target release observations. The final step proves the clean rebuild is the
same binary as the fully validated executable and reruns smaller/mask checks.
Every result path must be new. Timings include allocation, preprocessing, both
stabilizations, PNG rendering/writing and cleanup; profiling/adapter times are
kept separate.

For a fresh clone, first generate original goldens:

```bash
B="$PWD/results/baseline-$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/reproduce.py --output "$B"
```

Then use `--baseline "$B"` and a nonexistent `--row-results` path with the candidate
launcher. It generates only the additional N=501 original golden. The baseline
launcher archives original commit `15fe837445b8e32a15ac61fcfa388980b54d9173` and
runs the expensive original study. The existing evidence was reused, rather than
repeating that study for every candidate. The complete expensive fresh-clone
workflow was not repeated solely to test its launcher; component paths and the
actual clean-clone smoke scope are recorded.

Experiment dependencies: Python 3 standard library, GNU time, util-linux taskset,
Git, tar and Valgrind. Binutils are used for optional profiles. Plotting uses an
isolated ignored environment via `python3 scripts/setup_plotting.py`; pinned
packages are committed and are not production build dependencies.

## Methods, source mapping and report material

- [Report-ready results and all timing observations](docs/FINAL_REPORT_NOTES.md)
- [Application, profiling and correctness arguments](docs/FINAL_METHODS.md)
- [Exact reproduction and experimental commit mapping](docs/FINAL_REPRODUCTION.md)
- [Independent post-recovery experiments](docs/ADDITIONAL_EXPERIMENTS.md)
- [Original baseline findings](docs/BASELINE_FINDINGS.md)
- [Row-interval experiment](docs/ROW_INTERVALS.md)
- [Compact raw evidence and hash manifest](measurements/final-study)
- [Vector speedup/scaling figures and plot selection](figures/final)

All performance measurements run directly on fa26-cs598a-022.cs.illinois.edu:
Intel Xeon Silver 4216 @2.10 GHz, four VMware vCPUs, Ubuntu 26.04.1 LTS,
GCC 15.2.0. Benchmarks run sequentially on logical CPU 0. Historical cohorts are
not all paired; the second/third padding and final observations use paired
blocks. Raw runs, ranges and sample SD are retained. Timer resolution is 0.01 s;
small reported SD=0 does not imply zero noise. Host scheduling/frequency is not
fully controlled. `perf` access was denied; no cache/IPC claims are made.

Large images, grids, source archives, binaries and raw profiler traces stay under
ignored `results/`. Git contains code, compact evidence, documentation and PDF/SVG
figures. No GPU, threading, compiler-flag, renderer, PNG-library or hardcoded-output
change is used. Tested identity sizes are <=1001; the starter's huge-N renderer
indexing/allocation limitations are outside this study. Rejected smaller screens
have no implied target-size correctness or timing results.
'''
smoke=pathlib.Path(__file__).resolve().parents[1]/'measurements/final-smoke/report.json'
if smoke.exists():
 text+='\nFresh GitHub clone smoke verification passed the data audit, clean default build,\n54 correctness entries and decoder tests. Its code/read-only-data/initialized-data\nsections match the measured executable. See [smoke evidence](measurements/final-smoke).\nThe authoritative VM checkout is built and ready; existing root output was preserved.\n'
a.output.write_text(text);print(a.output)
