# Final experiment methods and correctness rationale

## Application

The active graph is a disk intersected with the starter's row-dependent prefix:
`j <= max(i,N-1-i)` and `(i-N/2)^2+(j-N/2)^2 <= (N/2)^2`, with integer division.
At N=1001 this is a radius-500 disk with a right-facing mouth. Boundary equality
is included. The original expression, including its even-N behavior, is retained.
There are 589,365 active cells among 1,002,001 allocated cells at the target size.

An unstable active cell sends one grain to each orthogonal neighbor and loses
four. Grains crossing the square boundary disappear. Excluded cells inside the
square never topple but retain incoming grains. Those sink counters matter for
exact starter compatibility, even though they are not elements of the sandpile
group. The identity construction fills the entire square with six grains,
stabilizes, complements every stored integer as `6 - height`, and stabilizes
again. Rendering maps heights 0..3 to four colors; every other value is black.
Consequently image equality alone cannot establish integer-grid equality.

The original repeatedly scans the mouth prefix, recomputes the circle predicate,
and topples each unstable cell once per visit. Stabilization dominates because
both the number of scanned cells and the number of sweeps grow with N. Do not
claim an asymptotic exponent from four measured sizes alone.

## Evidence motivating the experiments

The baseline's N=251 diagnostic recorded 10,965 sweeps, 519,477,840 prefix visits,
404,564,640 active visits, and 179,766,102 legal unit topplings across both phases.
Inactive cells were 22.12% of prefix visits; stable cells were 55.57% of active
visits. At unstable visits, 35.10% had quotient `height/4 == 2`. Separate N=251
gprof source attribution assigned approximately 27.5% to geometry lines and
23.7% to loop lines. These are approximate instrumented small-workload samples,
not hardware counter fractions at N=1001. N=101 Callgrind attributed 98.86% of
instructions to stabilization. `perf` was denied by VM policy, so there is no
measured IPC, cache-miss, or hardware branch-misprediction evidence.

## Isolated changes

1. **Row intervals (work reduction).** A row's disk intersection and its mouth
   prefix intersect in one interval. Precompute first/last active columns using
   widened integer arithmetic, then traverse exactly those cells in the original
   order. Two interval tables are built/freed per identity, one per stabilization.
   Since skipped cells performed no writes in the old loop, every active visit
   and unit toppling is preserved. N=251 counters confirm identical sweeps and
   legal topplings, with 22.12% fewer loop visits. N=101 Callgrind total
   instructions fell from 510,187,636 to 184,285,289 (63.88%). This supports reduced
   traversal/geometry overhead; it is not a full-size instruction count.

2. **Batched topplings (algorithmic work reduction).** For height h>=4, use
   q=h/4, subtract 4q, and send q to every in-bounds neighbor, including inactive
   sinks. This is q consecutive legal topplings: the pre-topple height before
   the last one is at least four. Multiplication 4q cannot overflow an int.
   Abelian stabilization has a unique final stable active state and odometer
   on this finite dissipative graph, so sink increments are also preserved.
   Batching can change sweep counts and the order of subsequent topplings.
   The first implementation checks each neighbor addition against INT_MAX.

3. **Overflow-bound refinement (batching implementation cost).** Before each
   stabilization, compute the sum of positive stored heights, stopping once it
   exceeds INT_MAX. A legal q-toppling removes 4q positive grains and adds at
   most q positive grains at each of at most four recipients, so that sum cannot
   increase. If it initially fits, every future cell fits in int; negative sink
   values only increase. This permits direct additions in a separate fast loop.
   Otherwise the implementation retains the individually checked loop. The
   accumulation uses int64_t and stops after at most INT_MAX plus INT_MAX.
   Both loops implement the same batching rule. This isolates the cost of the
   first implementation's safety checks without weakening arithmetic safety.

4. **FIFO worklist (scheduling/data structure).** Seed currently unstable active
   cells in row order. Pop a unique scheduled cell, clear its flag, topple it,
   and enqueue unstable active recipients that are not already scheduled.
   A unit-toppling version also requeues itself if still unstable. A batched
   version uses the same queue but q=h/4. The only difference between those two
   source commits is q. Inactive recipients retain grains but are never queued.
   An enqueued cell cannot become stable before its unique entry is processed:
   no other operation decreases it. FIFO processing is fair, and termination
   follows from legal stabilization on the finite dissipative graph. A circular
   buffer has capacity equal to the active-cell count; one membership byte per
   allocated cell prevents duplicate entries. Space is O(N^2), with no growing
   queue or parallel races. Each variant retains checked neighbor additions.

The unit FIFO variant is relative to the row-only parent; its batched sibling
measures batching on that FIFO parent. They must not be described as an isolated
worklist benefit relative to a cumulative batching variant. The row-batch-bound
refinement is a separate measured configuration, not folded into the first
batching result. Raw source SHAs identify each configuration.

## Measurement and validation

All measurements run directly on fa26-cs598a-022.cs.illinois.edu: VMware,
Intel Xeon Silver 4216 @ 2.10 GHz, four exposed vCPUs, Ubuntu 26.04.1 LTS,
Linux 7.0.0-31-generic, GCC 15.2.0 (Ubuntu 15.2.0-16ubuntu1). Unchanged release
flags: `-O3 -lm -g -Werror`; taskset pins one process at a time to logical CPU 0.
GNU time reports elapsed, user/system CPU seconds and maximum RSS. End-to-end
elapsed time includes allocation, mask/worklist preparation, both stabilizations,
PNG rendering and buffered writing, and cleanup. No fsync is requested. There
is one excluded N=101 preflight and no excluded target-size warmup.

Original and row-only distributions are reused. Their target cohorts and new
variants are historical/unpaired, although recorded CPU, compiler, kernel and
hostname match. Small original/row results came from the earlier paired blocks.
New candidate sizes run sequentially, with three repetitions at each measured
small size. A single target observation is explicitly marked n=1, without a
sample standard deviation. Three-run distributions use median, min/max, mean,
and sample standard deviation; plot whiskers show observed ranges, not confidence
intervals. GNU time's 0.01-second precision makes N=101 ratios coarse and can
produce a reported SD of zero despite real variation. VM scheduling/frequency
and host interference are not fully controlled.

Correctness gates before release benchmarking include final integer comparisons
for all tested sizes through N=501 (or N=251 for worklist screening), active
stability, exact grid-to-palette correspondence, decoded adapter/release equality,
an independent reverse-order Python oracle for sizes <=32, 24 seeded randomized
stabilization/idempotence cases, independent small mathematical identity checks,
and seven invalid CLI cases. Both intermediate phase grids are compared at
N=2,31,32 against the independent oracle and at N=251 against preserved original
phase dumps. Seven ASan/UBSan sizes and Memcheck N=101 run before timing.

Promoted target candidates receive one release timing and then a separate
N=1001 adapter run comparing all 1,002,001 signed integers, active stability,
rendered pixels and the supplied reference. Subsequent release repetitions
compare decoded pixels outside the timer. Adapter and diagnostic timings are
never part of release distributions. Large-grain tests exercise the overflow
bound, checked fallback, negative sinks and explicit overflow rejection.

The 138-size row-mask proof-by-enumeration from the earlier study is retained;
this is not a claim that 138 full identity calculations were tested. Full-size
intermediate phase dumps are unavailable for the original baseline; numerical
stage-to-stage comparisons are limited to the listed smaller sizes. Every final
target integer is compared. No failing expectations are changed.

## Boundaries and deferred directions

This study concerns the 1001 target and the tested smaller odd/even dimensions.
The starter's CLI accepts much larger sizes, but its renderer indexing and
unchecked main-grid allocations are legacy limitations. The new grain arithmetic
checks do not constitute a general audit of arbitrary huge allocations.

Contiguous storage is deferred: no cache-miss profile establishes a layout
bottleneck, and completing validation and reproduction takes priority. No OpenMP,
GPU, compiler-flag, renderer, PNG-library or application-layout change is included.
There is no standalone original-geometry batching benchmark; batching is measured
relative to the retained row optimization. Worklist target measurements are
conditional on smaller-size evidence and the strict deadline.
