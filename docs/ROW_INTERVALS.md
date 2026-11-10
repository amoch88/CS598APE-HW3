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
R="results/row-intervals-$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/row_intervals_study.py \
  --baseline-results "$HOME/CS598APE-HW3/results/20261110T013855Z-baseline" \
  --candidate-commit 7fd71987e27f00d690e5e0348d5701a76a12ca0b \
  --output "$R"
python3 scripts/summarize_row_intervals.py "$R"
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

## Completed measurements and recommendation

The VM study completed with status PASS. Implementation commit:
`7fd71987e27f00d690e5e0348d5701a76a12ca0b`; baseline-study parent:
`cd3c4b43e7e8eab30df1f562d4efbd6daa8ba367`.
Full artifacts: `~/CS598APE-HW3/results/20261110T023926Z-row-intervals/`.
[Compact raw evidence](../measurements/20261110T023926Z-row-intervals) includes all
individual timings, min/max/mean/sample SD, source/binary hashes, environment,
correctness results, counters and instruction profiles. PNGs, full grids, source
archives, executables and raw profiler traces are excluded from Git.

### Release results

All values below are medians of three GNU time end-to-end observations, including
interval construction/allocation, both stabilizations, PNG writing, and cleanup.
N=101/251/501 baselines are fresh randomized paired blocks; N=1001 reuses the
preserved original distribution exactly as requested. Environment checks matched
GCC 15.2.0, Xeon Silver 4216 CPU, kernel 7.0.0-31-generic, hostname and CPU 0
availability. The four-vCPU VM runs Ubuntu 26.04.1 LTS with approximately 15 GiB RAM.
All measurements are pinned to CPU 0 and use -O3 -lm -g -Werror.

| N | Baseline median (s) | Row intervals median (s) | Speedup |
|---|---:|---:|---:|
| 101 | 0.09 | 0.04 | 2.25x |
| 251 | 2.73 | 1.30 | 2.10x |
| 501 | 41.18 | 19.69 | 2.09x |
| 1001 | 646.93 | 304.82 | 2.12x |

N=1001 optimized observations: **304.82, 304.34, 307.08 s**. Median **304.82 s**;
minimum **304.34 s**; maximum **307.08 s**; mean **305.4133 s**;
sample standard deviation **1.4632 s**. The original observations were
646.93, 645.67, 655.74 s (median 646.93 s; sample SD 5.4865 s).
The observed median speedup is **2.1223x**, corresponding to
**52.88% less elapsed time**. Every measured image passed exact decoded
comparison outside the timer; all three optimized target PNGs are also
byte-identical to the supplied reference.

Speedup is approximately constant near 2.1x for N>=251, with no convincing
monotonic increase or decrease across those sizes. The apparent 2.25x at N=101
is sensitive to GNU time's 0.01-second resolution. Reported zero sample SD at
N=101/251 for the candidate reflects quantization, not zero underlying variation.
Three observations and an unpaired historical target baseline do not establish a
precise population confidence interval. VM-host scheduling/frequency is not
controlled; no baseline N=1001 executions were repeated in this experiment.

### Correctness and isolation

All existing 62 correctness entries plus an added N=501 identity entry passed
(**63 total**). Every allocated signed integer and decoded pixel matched the
original baseline for all 16 identity sizes, including all 1,002,001 N=1001 cells.
This includes inactive sink values. The supplied N=1001 reference had **zero
mismatched channels**. The independent reverse-order mathematical oracle,
24 randomized stabilization/idempotence cases, recurrent/identity properties,
invalid CLI cases and PNG decoder tests all passed.

Exhaustive interval-mask checks passed across **138 sizes / 5,653,280 positions**,
including all identity sizes and nearby large odd/even sizes. Both stabilization
stages matched every allocated integer at N=2,31,32,251; small cases used the
independent Python solver and N=251 used saved baseline stage grids. At N=251,
sweeps, unit-toppling counts and encountered-height histograms were unchanged.

Seven ASan/UBSan sizes passed with halt-on-error enabled. N=101 Memcheck reported
zero errors, zero leaked bytes, and 588 allocations / 588 frees. The diagnostic
generator's original-baseline mode was also checked at N=1.
Source comparisons confirmed that rendering/prefix declarations, find_identity(),
main(), initialization/complementing and the toppling body are unchanged (aside
from indentation of that body). Makefile and stb_image_write.h are unchanged.
The original baseline branch still points to cd3c4b4; prior measurements and
preexisting root-level generated files are preserved.

### Work reduction and explanation

The original N=251 profile motivated this change: geometry-related source locations
received about 27.5% of sampled CPU time, and 22.1% of scanned positions were
inactive. These exploratory fractions were not target-size runtime fractions.

| N=251 instrumented work | Original | Row intervals |
|---|---:|---:|
| Phase 1 sweeps | 7,730 | 7,730 |
| Phase 2 sweeps | 3,235 | 3,235 |
| Phase 1 unit topplings | 131,945,672 | 131,945,672 |
| Phase 2 unit topplings | 47,820,430 | 47,820,430 |
| Total sweep positions visited | 519,477,840 | 404,564,640 |
| Source-level geometry predicate evaluations | 519,477,840 | 94,752 |

Scan visits fell **22.12%** at N=251. Geometry predicates are evaluated only in
two preprocessing scans (47,376 positions each), a **99.9818% source-level
reduction**; they disappear from the repeated sweep loop. Preprocessing work and
two small temporary allocations are included in the release timings. The exact
N=1001 mask independently establishes **752,001 -> 589,365 positions per sweep**,
a **21.63% reduction**; no target-size sweep count is inferred from N=251.

Separate N=101 Callgrind runs recorded **510,187,636 -> 184,285,289 instructions**,
a **63.88% reduction** for the full program, including setup and PNG handling.
This is exploratory instruction evidence, not target-size instruction counts or
hardware cache/IPC data. Instrumented/Valgrind times are excluded from release
measurements.

These observations support the hypothesis: eliminating repeated mask arithmetic
and branches, skipping inactive iterations, and tightening the compiled loop
reduce overhead while preserving the same toppling work. The gain cannot be
attributed solely to the 27.5% source sample group; the change also removes loop
work, and source attribution is approximate. We did not measure how much of the
remaining difference comes from particular CPU mechanisms.

**Recommendation: retain this optimization.** It gives about 2.1x end-to-end
speedup across the larger tested workloads, with exact state/output equivalence
and a simple correctness argument. Overall repeated-sweep scaling remains the
same; this is a reduction of work per sweep. No batching, worklist, parallelism,
grid-layout change, PNG tuning or further optimization was implemented.
