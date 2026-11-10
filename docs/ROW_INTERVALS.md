# Independent experiment: exact active row intervals

This branch changes only how stabilization enumerates cells. Each stabilize()
call precomputes a first/last active column for every row, using the original
mouth-prefix bound and a widened 64-bit integer disk predicate. A disk intersects
a row in an interval; intersecting with the mouth prefix remains an interval.
Scanning first through last therefore visits exactly the original active cells,
in the same row/column order. All toppling, initialization, complementing, sink
accumulation and rendering rules remain unchanged. Intervals are allocated once
per stabilization, reused across its sweeps, and freed afterward. Both setup
passes and allocations are included in release timing. No batching, worklists,
parallelization or layout change is included.

Validation includes exhaustive C mask comparisons for N=1..128 and
250,251,252,500,501,502,999,1000,1001,1002. The original int predicate is safe at
these sizes; production precomputation widens before squaring. Both stabilization
stages at N=2,31,32 are compared with an independent Python solver; both stages
at N=251 are compared with the frozen baseline, including all inactive integers
and sweep/unit-toppling counts. The existing 62 correctness entries are retained;
an N=501 identity check is added, for 63 entries. Every identity grid is compared
with a frozen baseline integer grid and decoded PNG. ASan/UBSan, Memcheck and the
PNG decoder tests run before benchmarking. Any failed check stops the workflow.

Run from the VM repository root with an existing completed baseline study:

```bash
python3 scripts/row_intervals_study.py \
  --baseline-results "$HOME/CS598APE-HW3/results/20261110T013855Z-baseline" \
  --candidate-commit HEAD \
  --output "results/row-intervals-$(date -u +%Y%m%dT%H%M%SZ)"
```

Use an explicit implementation commit when reproducing a historical result.
The launcher archives that source commit and builds with the original Makefile
and `-O3 -lm -g -Werror`. It records environment and binary/source hashes, checks
that host/CPU/GCC/kernel remain comparable, validates the old baseline archive
and executable, and runs all workloads sequentially pinned to CPU 0. An existing
experiment manifest/output is refused. The original baseline branch, golden
outputs, timings and root-level preexisting generated files are not modified.

Fresh clones first need a baseline result directory. Use the baseline reproduction
command in README.md; this is expensive but reconstructs all required golden
files from original commit 15fe837445b8e32a15ac61fcfa388980b54d9173.

After correctness passes, exploratory N=101,251,501 measurements use three
seeded randomized baseline/candidate blocks per size. N=1001 reuses the existing
three-run original distribution; it is not unnecessarily rerun. Three candidate
measurements are planned, with one sufficient for rejection if the first fails
to improve the historical median. An excluded N=101 preflight precedes target
measurements; no full-size warmup is added. GNU time includes all initialization,
stabilization, rendering, PNG writing and cleanup. Output validation is outside
the timer. Individual raw observations and sample standard deviations are saved.
The GNU time 0.01-second resolution is coarse for N=101. Historical N=1001
comparisons are unpaired and do not control VM-host scheduling or frequency.

N=251 instrumented counters and N=101 Callgrind are separate from release timing.
Their work/instruction reductions are exploratory, not target-size instruction
or hardware-cache measurements. Large images, grid dumps and raw profiler traces
stay in ignored results/. Compact evidence and final findings are committed after
the experiment finishes. No later optimization is part of this experiment.
