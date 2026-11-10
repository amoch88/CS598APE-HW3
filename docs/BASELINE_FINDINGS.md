# HW3 baseline evidence and next experiments

The study completed on the UIUC VM, with no performance optimization applied.
Production `sandpile.c`, `Makefile`, and `stb_image_write.h` match baseline commit
`15fe837445b8e32a15ac61fcfa388980b54d9173` exactly. Windows was the SSH client;
all builds, executions, file edits, commits and pushes occurred on the VM.

Raw evidence is in
[`measurements/20261110T013855Z-baseline`](../measurements/20261110T013855Z-baseline).
The complete generated artifacts remain on the VM under
`~/CS598APE-HW3/results/20261110T013855Z-baseline/`.

## Environment and release timing

- Host: fa26-cs598a-022.cs.illinois.edu; VMware VM.
- CPU: Intel Xeon Silver 4216 @ 2.10 GHz; four available vCPUs.
- Memory: approximately 15 GiB; exact bytes and CPU details in environment.txt.
- OS: Ubuntu 26.04.1 LTS; Linux 7.0.0-31-generic.
- GCC: 15.2.0; original Makefile, flags `-O3 -lm -g -Werror`.
- Sequential runs pinned to CPU 0. One excluded N=101 preflight; no full-size warmup.
- GNU time measures the full executable, including PNG creation and buffered writes.

| N=1001 run | Wall seconds | User seconds | System seconds | Max RSS KiB |
|---|---:|---:|---:|---:|
| 1 | 646.93 | 646.81 | 0.05 | 12628 |
| 2 | 645.67 | 645.50 | 0.09 | 12492 |
| 3 | 655.74 | 655.48 | 0.19 | 12588 |

Median **646.93 s**; minimum **645.67 s**; maximum **655.74 s**;
mean **649.4467 s**; sample standard deviation **5.4865 s**.
Inclusive quartiles: Q1=646.300 s, Q3=651.335 s, IQR=5.035 s.
All observations are retained. Three runs provide limited statistical precision;
no confidence interval or significance claim is made. A pinned vCPU does not
reserve a physical core or control host scheduling/frequency.

The user reduced five planned runs to three during run 2. Its sandpile process
and original GNU time process were not interrupted. Only the controller changed.
Primary GNU time values are intact; the auxiliary Python launcher time for run 2
is intentionally blank. Its recorded start time comes from the original pre-run
snapshot mtime. The initial plan and transition note are preserved. Brief CPU-2
infrastructure smoke tests/builds occurred during run 2 and are documented in the
protocol; no timing observation was discarded because of them.

## Correctness results

All **62 correctness entries passed**:

- 15 identity sizes: 1,2,3,4,5,6,7,8,15,16,31,32,101,251,1001.
- At all sizes: active-cell stability, integer-grid-to-palette consistency, and
  decoded image equality between the adapter and the original release executable.
- At 12 sizes through N=32: every allocated integer compared against an independent
  Python reverse-order stabilizer, including inactive cells.
- 24 seeded arbitrary stabilization cases plus repeat-stabilization idempotence.
- 16 independent identity-idempotence/recurrent-action cases at N=1..8.
- Seven invalid command-line cases rejected.

The N=1001 image matches the supplied reference at every decoded RGB channel:
1001x1001 pixels, **zero mismatched channels**. All three release PNGs are also
byte-identical to the supplied reference (SHA-256
`4883dba5b09236b78477ca25c9395411fc1f82f4233aaa378193d7925269dbbe`).

The baseline adapter preserves all 1,002,001 N=1001 integers for future comparison:
589,365 active cells; 412,636 inactive cells. There are 2,829 negative inactive
values; the overall range is -6047..3. Stable active heights alone do not justify
unsigned storage or discarding inactive-cell writes. The full target grid is a
frozen compatibility oracle, not a claim of independent mathematical verification
of every target integer. The independent integer solver was run at small sizes.

The instrumented N=251 final grid matches the uninstrumented adapter at every
allocated integer; its image and both other profiler images match the baseline.
The PNG decoder's synthetic five-filter/CRC test passed. ASan/UBSan passed at
N=1,2,3,4,31,32,101 with halt-on-error enabled. Valgrind Memcheck at N=101 reported
zero errors and zero bytes in use at exit (586 allocations and 586 frees).

## Profiling evidence and limits

Perf is installed (7.0.14) but policy `perf_event_paranoid=4` denies access,
including software-event probes. Error logs are saved; security policy was not
changed. We have no hardware-counter evidence about cache misses or IPC.

To prioritize results, exploratory profiling used smaller grids:

| Evidence | Workload | Measured result |
|---|---|---|
| gprof, separate `-pg` build | N=251 | All sampled CPU time in stabilize: 2.58 sampled seconds, 0.01-second granularity |
| Callgrind, original release binary | N=101 | stabilize: 504,371,545 of 510,187,636 instructions, 98.86% |
| Diagnostic phase 1 | N=251 | 7,730 sweeps; 131,945,672 unit topplings |
| Diagnostic phase 2 | N=251 | 3,235 sweeps; 47,820,430 unit topplings |
| Diagnostic combined scans | N=251 | 519,477,840 scanned positions; 22.12% fail mask membership |
| Diagnostic active visits | N=251 | 404,564,640 visits; 55.57% find stable cells |
| Heights at unstable visits | N=251 | 35.10% have height 8, permitting two legal topplings at that instant; maximum observed height 8 |

Gprof's approximate source-line sample groups at N=251 were:
geometry lines 81-82, **27.52%**; loop lines 79-80, **23.65%**;
stability test line 83, **10.85%**; neighbor-update/boundary lines 87-94,
**30.61%**; subtraction line 86, **7.36%**. These are compiler-attributed source
locations, not isolated instruction-category timings. Coarse sampling and
instruction scheduling limit exact interpretation. Zero PNG samples do not mean
zero PNG cost. Callgrind recorded instructions only, not cache behavior.

The required N=1001 integer-grid adapter separately measured **666.6951 s** around
unchanged `find_identity()` and **0.07683 s** around rendering/PNG writing; grid
dumping took **0.08657 s** outside both. This is one diagnostic adapter run, not
one of the three release measurements. Its executable/context differs, so its
absolute runtime must not be substituted into the release distribution. It
supports prioritizing the computation over PNG tuning at the target size.

N=251 counter instrumentation perturbs execution (2.1131 s and 0.8394 s for the two
phases). Neither those times nor the smaller-grid sample fractions are claimed
as target-size phase or source-line runtime fractions. The same production
algorithm is being profiled, but scaling/cache effects may differ by N.

## Ranked next experiments

This ranks expected practical benefit from the available evidence, not measured
speedups. No candidate has been implemented or timed yet.

| Rank | Candidate and motivation | Correctness risks | Independent experiment |
|---|---|---|---|
| 1 | Exact precomputed active row intervals: remove repeated geometry work (~28% sampled source attribution) and the 22% inactive scans | Inclusive circle/mouth boundaries, even-N behavior, integer rounding; keep all inactive-cell writes | Change only scan bounds; exhaustively compare masks, preserve active visitation order and toppling counts; run golden checks and N=1001 paired timings |
| 2 | Batch legal topplings: 35.1% of original unstable visits had height 8, especially in phase 1 | Update every neighbor by q; preserve sinks, signed state, and legal schedule; observed height bounds do not automatically apply to a new schedule | Implement q=height/4 independently of geometry/worklists; compare all integer outputs, record batched visits/unit-equivalent work, and time N=1001 |
| 3 | Active-cell worklist: skip stable cells (55.6% of active visits), possibly eliminating whole sweeps | Missed reactivation, queue-membership bugs, premature termination, inactive-cell enqueueing | Keep baseline layout and toppling rule; measure queue operations/memory and N=1001 end-to-end time. Dense activity means queue overhead can offset savings |
| 4 | Contiguous grid layout: test indexing/locality improvements after the stronger work-reduction hypotheses | Stride/border errors, unsafe aliasing assumptions; adapt the test interface explicitly | Layout-only change with signed integer state; hold rule, geometry and ordering fixed; compare full grids and timing. No cache-bound claim without evidence |

Use one commit per isolated candidate and the same compiler flags/output path
policy. First pass correctness, then collect paired baseline/candidate observations
with fixed recorded randomization, report dispersion, and retain all raw data.
Measure cumulative combinations only after isolated effects are known. See the
[experimental protocol](EXPERIMENT_PROTOCOL.md) for the later paper/artifact plan.
