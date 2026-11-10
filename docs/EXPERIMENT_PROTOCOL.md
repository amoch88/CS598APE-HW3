# HW3 experimental protocol

## Scope and frozen baseline

Primary workload: N=1001, exact starter Pac-Man mask, output identity.png.
Baseline source commit: 15fe837445b8e32a15ac61fcfa388980b54d9173.
Production sandpile.c, Makefile and stb_image_write.h remain unchanged.
All final measurements are made on the UIUC VM, not the Windows SSH client.
Untracked pre-study identity.png and sandpile.exe are preserved under the initial
study's prior-work directory and left intact at the repository root.

For odd N=1001, active cells satisfy (i-500)^2+(j-500)^2<=500^2 and
j-500<=abs(i-500). For general N, use the original integer expressions, including
all boundaries. Only active cells topple; every allocated cell participates in
initialization, complementing, and rendering. Inactive cells receive grains but
never return them. Discarding their accumulated values may alter the image.

## Release timing

- Original Makefile with GCC and -O3 -lm -g -Werror.
- One excluded N=101 preflight; no full-size warmup.
- Three sequential N=1001 runs pinned to logical CPU 0.
- GNU time elapsed seconds are the primary metric (0.01-second printed precision).
- Include process execution, allocation, both stabilizations, rendering, PNG
  compression and buffered writes, and cleanup. No fsync is added.
- Exclude output checks, diagnostic counters, gprof, sanitizers and Valgrind.
- Retain raw elapsed/user/system time, max RSS, exit status, output SHA-256,
  timestamps, and /proc/stat snapshots before and after each run.
- Report every observation, median, inclusive quartiles, min/max, mean, and
  sample standard deviation (denominator n-1). Three runs give limited statistical
  precision. Do not label an IQR as a confidence interval or silently omit outliers.
- A pinned vCPU is not a dedicated physical core. Record virtualization and load;
  VM host interference and unreported frequency changes remain limitations.

## Correctness acceptance

Production compatibility requires exact allocated integer-grid equality and
identical decoded RGB pixels, including inactive-cell behavior. PNG byte equality
is a stronger incidental check when the same encoder is used, not the general
acceptance criterion. Decode and compare the supplied reference independently;
never overwrite it after a mismatch. Keep outputs from the frozen baseline.

The independent small-grid reference uses Python integers and reverse row/column
order, scanning the entire square and applying the same graph rule. It checks
identity results for small odd/even sizes. Seeded arbitrary stabilization inputs
exercise heights above threshold and signed inactive values. Repeat stabilization
checks idempotence. Identity idempotence and action on recurrent examples test
active graph values independently; inactive accumulation is not a group element.
These finite tests support, but do not prove, correctness for every possible N.

Sanitizer and leak-check results are separate from mathematical and compatibility
checks. The baseline accepts sizes whose allocation/index arithmetic can overflow;
this study does not claim arbitrary-positive-int correctness.

## Profiling and evidence

Probe perf without changing system policy. If denied, retain error messages and
record the exact policy value. An N=251 gprof build supplies exploratory sampled CPU-time
attribution; report its sampling granularity, grid size and instrumentation effects.
An N=251 counter build gives phase/work diagnostics. Neither is a target-size
line-level runtime profile. The required N=1001 integer-grid adapter times the
unchanged computation and rendering calls externally, avoiding an additional
expensive full-size profiling run.
Callgrind N=101 supplies deterministic instruction attribution only for that size,
not target-size timing or hardware cache evidence.

The generated N=251 diagnostic copy preserves the toppling rule, traversal and mask.
Counters record each stabilization's sweeps, topplings, encountered heights and
phase time; exact geometry counts derive scan/active visits per sweep. It saves
both phase grids, and its final grid/image must match the uninstrumented adapter.
Instrumented phase times cannot be substituted for release timings. A source line
may mix arithmetic, branches and memory accesses; neither a line profile nor a
cache-sized grid alone establishes a hardware bottleneck.

For every optimization, write an evidence chain:
measured cost -> mechanism hypothesis -> isolated change -> correctness result ->
run distribution -> explanation, including negative results.

## Subsequent optimization experiments (not implemented)

Select implementation order from collected evidence, not a fixed prior ranking.
Measure worklists, batched legal topplings, precomputed row geometry and contiguous
storage separately against the same frozen baseline before combining changes.
Keep compiler flag changes, halo changes and parallelization as separate factors.
For batching, q=height/4 legal topplings must preserve every neighbor increment,
including sinks. For worklists, track reactivation and termination carefully.
For geometry, exhaustively compare the Boolean mask, including even N and edges.
For layouts, retain signed integer state and audit allocation/stride arithmetic.
Naive parallelization races on neighbor writes.

For final candidate comparisons, use paired baseline/candidate blocks with a
recorded fixed random seed, balanced randomized within-block ordering, fixed
compiler/CPU/filesystem and no overlapping compute workloads. Predeclare the
number of blocks (recommend at least ten if practical), keep all raw runs, report
median/IQR and paired speedup uncertainty using block resampling. Show individual
variants and the cumulative implementation to reveal interactions.

## Commit and paper structure

1. Frozen original source SHA.
2. Benchmark/correctness/profiling infrastructure and reproduction instructions.
3. Baseline raw timing CSV, environment, compact profile evidence and findings.
4. Later: one isolated optimization per commit, with its evidence and tests.
5. Later: combined implementation, final evaluation and report.

Keep large images, grid dumps, binaries and profiler traces under ignored results/.
Commit small raw tables, manifests, profile excerpts and analysis scripts. Build
from explicit SHAs after Git fetch; never assume local edits exist on the VM.

The report is at most three ACM SIGPLAN pages excluding references. Allocate
approximately half a page to the computation/semantics, one page to measured
motivation and changes, one page to evaluation/correctness, and half a page to
limitations and introspection. Include a compact profile table and a timing figure
with individual runs and dispersion. Put detailed commands in the artifact README.

## Initial run-count revision

The user reduced the initial five-run plan to three total observations while run
2 was active. Its GNU time child and sandpile child were not interrupted. Only
the orchestration process was replaced. The run's auxiliary launcher timer was
not recoverable and is deliberately blank; the start timestamp comes from the
original pre-run snapshot mtime. Primary elapsed/user/system/RSS/status values
come directly from its original GNU time output. The initial manifest and a
transition note are retained. Future fresh runs need no controller transition.
A brief infrastructure smoke test/build on CPU 2 occurred during run 2; its
artifacts and timestamps are retained under infrastructure-preflight/. All
full-size measurements and all substantive profile/correctness workloads run
sequentially on CPU 0; ordinary OS and VM-host activity remains uncontrolled.
