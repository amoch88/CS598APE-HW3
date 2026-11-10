# Experiments after recovery

The deadline extension allowed four independent screens after bounded batching
had three target observations and all target correctness checks were verified.
All changes start from source `50970858a53845220b44f604e62223c2ea7f1ea1` (plus
experiment infrastructure). They do not incorporate each other's algorithm changes.

Each screen uses the shared archived-source workflow, all smaller integer checks,
both-stage comparisons at N=2/31/32/251, arithmetic boundary tests, seven ASan/UBSan
sizes and N=101 Memcheck. Three parent/candidate pairs at N=101/251/501 run in
seeded order (seed 598), with a preflight for each binary. Every raw observation
is retained, including the parent measurements; these fresh parent samples are
not pooled into the earlier bounded-batching distributions. A candidate advances
if its N=501 paired median speedup exceeds 1.01 and its N=251 ratio is at least
1.0, after correctness passes. This practical screen is not a significance test.

## Contiguous storage

Source `fa762f0f0cb19e3a2d3dbd24e0a4e093cac86619`, branch
`hw3-contiguous-storage`. Hypothesis: reducing row allocations and gaps could
improve locality. The indexed `int **` access pattern remains unchanged, and
there is no cache-miss evidence; this is explicitly an empirical hypothesis.
A shared production allocator is exposed to the test adapter so that integer
checks exercise the same contiguous layout as the CLI. The checked size product
and allocation failures are handled, and one backing block plus row pointers
is released normally.

N=501 candidate observations: 17.23, 17.29, 17.38 seconds, median 17.29.
Paired parent: 17.21, 17.23, 17.21 seconds, median 17.21.
At N=251 both medians are 1.14 seconds. No useful gain; rejected before a target
run. N=101's rounded 0.03/0.04 values are too coarse to override the larger sizes.
This is not evidence that all contiguous implementations or hardware are equal.

## Alternating sweep direction

Source `c248ea4ea6ea2c5705e2579fd20e0e47e7599f7d`, branch
`hw3-alternating-sweeps`. Hypothesis: forward-only sweeps propagate updates quickly
toward later positions, while earlier recipients wait for the next pass. Reverse
alternate complete passes to reduce this directional delay without per-cell
queue or membership management. The branch deciding direction runs once per pass;
there are separate forward/reverse loops. Every active cell is visited each pass,
all topplings are legal, and an unchanged full pass establishes stability. The
finite dissipative Abelian graph gives the same final active state and odometer,
so inactive sink counters also match.

At N=251, sweeps fell from 9,007 to 8,707 and visits from 332,322,272 to
321,253,472; unit topplings remain 179,766,102. N=501 candidate observations:
16.81, 16.81, 16.90 seconds (median 16.81), versus paired parent
17.31, 17.27, 17.31 (median 17.31), a 1.030x screen speedup.
This ordering change needs its own target integer check; smaller counter results
must not be presented as target-size work counts.

## Padded physical boundaries

Source `1080490846c96703f0734771560e729b9224cf73`, branch
`hw3-padded-boundaries`. In the bounded N=101 instruction profile, the source
lines for the bottom/right tests account for 33,311,928 instructions, 20.27% of
program Ir. Optimized source attribution is approximate and is not a CPU-time
fraction. Hypothesis: remove hot neighbor conditions with a one-cell sink halo.
Rows remain separately allocated; this does not depend on the contiguous variant.

Allocate N+2 rows with N+2 cells each and shift public row/cell pointers so physical
`grid[0..N-1][0..N-1]` is unchanged. In the proven-safe kernel, all four neighbor
updates are unconditional. Halo cells never topple, feed back, render, complement,
or appear in integer dumps. Absorbing outgoing grains in the halo is equivalent
to discarding them at the physical square boundary. Clear the halo before every
stabilization so the positive-grain bound also covers its initially zero cells.
Negative indices stay inside their allocated objects. The checked fallback keeps
the original physical guards, preserving its behavior when the sufficient bound
does not hold. The test adapter uses the production padded allocator and cleanup.

N=251 sweeps, visits, batched events and unit topplings exactly match the parent.
N=501 candidate observations: 16.67, 16.76, 16.74 seconds (median 16.74),
versus parent 17.25, 17.39, 17.39 (median 17.39), a 1.039x screen speedup.
The first N=1001 release observation is 259.78 seconds. Target verification and
any final combinations are reported in FINAL_REPORT_NOTES.md, not inferred here.

## Direct remainder mask

Source `7c76fc29cad53b7bfa2c9d6351369a7705c07131`, branch
`hw3-remainder-update`. At an unstable visit h>=4, `h & 3` is exactly
`h - 4*(h/4)`. Hypothesis: stating the remainder directly might remove unnecessary
arithmetic if GCC missed the quotient/remainder relationship. Both checked and
bounded kernels use the same equivalent replacement; update order is unchanged.

N=501 candidate: 17.31, 17.42, 17.32 seconds (median 17.32), versus parent
17.25, 17.47, 17.29 (median 17.29). N=251 medians are both 1.15 seconds.
Rejected. GNU objcopy extraction proves the parent and candidate `.text` sections
are byte-identical, each 56,810 bytes, SHA256
`88134e5330d52582b604d469dcd3da69a82bf1e85648f97bef5560bed09348a0`.
GCC already performs the desired transformation; timing differences are noise,
not an optimization benefit. The comparison JSON is preserved with this study.

## Selection and limits

Only target-verified improvements are eligible for a final combination. A
combination must be measured and integer-validated again; independent gains are
not multiplied to invent a combined result. See the final notes for actual
selection, complete target observations, profiles and statistics.

All timing includes preparation, allocation, rendering and cleanup. These are
single-threaded experiments with unchanged release flags, pinned to CPU 0.
There is no hardware cache/IPC evidence, no target extrapolation for rejected
screens, and no claim that three repetitions establish a confidence interval.
