# CS598APE HW3

This repository contains code for homework 3 of CS598APE. It is relatively
simple in comparison to HW1 and HW2 to ensure you have enough time to work on
the course project. 

`sandpile.c` contains the implementation of finding the identity element of a 2D
abelian sandpile.

![Identity sandpile on a 1001x1001 pacman grid](identity-ref.png)

*Identity sandpile on a 1001x1001 pacman grid*


To compile the program, run:

```bash
make all
```

To clean existing build artifacts, run:

```bash
make clean
```

Usage (after compiling):

```bash
./sandpile.exe <N> 
```

where `N` is the grid size

Consider speeding up the generation of this 1001x1001 identity sandpile (which
takes approximately ~3m 40s on my local laptop under the default setup)

```bash
./sandpile.exe 1001
```

For an optional, ungraded challenge, see how large a sandpile you can compute
on the course VMs and report the grid size and runtime. There is no prescribed
upper limit on `N` for this challenge.


## Baseline experiment artifact

The authoritative study runs on `fa26-cs598a-022.cs.illinois.edu` in
`~/CS598APE-HW3`. Windows is only the SSH client. The frozen production baseline
is commit `15fe837445b8e32a15ac61fcfa388980b54d9173`; the production algorithm and
Makefile are unchanged by this experiment infrastructure.

Requirements: Linux, GCC, Make, Git, Python 3 (standard library only), GNU time
at `/usr/bin/time`, util-linux `taskset`, GNU binutils (`gprof`), and Valgrind
with `callgrind_annotate`. `perf` is probed; blocked access is recorded rather
than changing the machine's security settings. CPU 0 must be available. Record
actual package/tool versions from `environment.txt`; exact historical timings
are not promised on another host or toolchain.

Run the complete study from the repository root, with a new output directory:

```bash
python3 scripts/reproduce.py --output "results/reproduction-$(date -u +%Y%m%dT%H%M%SZ)"
```

This may take substantial time: it executes five full-size baseline runs and
additional full-size correctness/diagnostic runs. Keep other compute workloads
idle. The launcher refuses an existing output directory, archives the exact
baseline Git commit, builds it using its original Makefile and flags
`-O3 -lm -g -Werror`, records source/binary hashes and environment information,
and executes workloads sequentially. It never changes the working production
source or overwrites root-level `identity.png` / `sandpile.exe`.

Timing uses GNU time, one process at a time pinned to logical CPU 0, including
allocation, both stabilizations, rendering, buffered PNG output, and cleanup.
An excluded N=101 preflight precedes five N=1001 observations; there is no
excluded full-size warmup. `timing/timings.csv` contains all raw observations;
`summary.json` reports median, min/max, mean, sample standard deviation, and
inclusive quartiles. Validation and profiling are outside these timed runs.
`launcher_wall_seconds` is auxiliary Python timing, not the reported metric.
Each run retains `/proc/stat` snapshots, exit status, stdout/stderr and PNG hash.

### Correctness and future candidates

`tests/grid_driver.c` includes the specified source without editing it, renames
its CLI main, and calls its existing `find_identity()` / `stabilize()` functions.
It dumps all allocated integer values and renders the same grid. This adapter
currently assumes the starter's `N`, `int **grid`, and function interface;
update the adapter explicitly if a future layout change replaces that interface.

`check.py` validates active-cell stability, exact palette rendering, and decoded
PNG equality between the adapter and release executable. For N<=32 it compares
every allocated integer cell against an independent reverse-order Python
stabilizer. It also runs 24 seeded random stabilization/idempotence cases,
identity/recurrent action checks on N=1..8, and invalid CLI cases. Inactive cells
receive grains and are compared too; they must never topple. Mathematical group
checks compare active cells only. The N=1001 decoded image is compared against
the repository reference; mismatches are saved as failures, never replaced.
The PNG decoder supports noninterlaced 8-bit RGB (the supplied image format),
verifies chunk CRCs, and has a synthetic test exercising all five PNG filters.

After a completed baseline study, validate a candidate with fresh output paths:

```bash
R=/absolute/path/to/completed/baseline-results
python3 scripts/check.py \
  --source /absolute/path/to/candidate/sandpile.c \
  --binary /absolute/path/to/candidate/sandpile.exe \
  --output results/candidate-check-001 \
  --reference-png "$R/source/identity-ref.png" \
  --golden "$R/golden"
```

This compares every final integer cell and decoded pixel against frozen golden
outputs for N=1,2,3,4,5,6,7,8,15,16,31,32,101,1001. Do not use a modified
production source as the baseline oracle. Retain the original source commit,
compiler flags, and golden manifests across future experiments.

### Profiling and interpretation

`run_study.py` waits for timing completion before running correctness or profiling.
It saves failed perf probes, a full-size `-pg` gprof sample profile, a Callgrind
instruction profile at N=101, full-size diagnostic phase timings/counters,
ASan/UBSan checks at N=1,2,3,4,31,32,101, and a Valgrind leak/memory check at
N=101. Every diagnostic image must match the baseline. The diagnostic final
integer grid must also match the uninstrumented adapter's full integer grid.

`diagnostic_source.py` generates a disposable instrumented source under results,
with a saved diff. It counts sweeps, unit topplings, and the distribution of
`height/4` at unstable visits; scan and active visits are derived from exact
per-sweep geometry counts. Both phase grids are saved. Its extra counter updates
perturb performance: diagnostic times are not release benchmark times. Gprof
also uses a separate instrumented binary. Callgrind N=101 instruction counts are
not N=1001 runtime evidence or hardware cache measurements.

Run the decoder test independently with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Large images, binaries, generated source, and raw profiler files stay under
ignored `results/`. Small raw timing CSVs, environment manifests, and evidence
extracts belong in `measurements/`, with interpretation in `docs/`. All final
performance claims must use VM measurements. For later optimizations, record one
source commit per isolated change, use paired seeded baseline/candidate run
orders, retain all observations, report dispersion, and show independent and
cumulative effects. No performance optimization is implemented in this phase.
