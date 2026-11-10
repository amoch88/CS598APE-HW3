# Reproducing the final experiments

Repository: **private** `git@github.com:amoch88/CS598APE-HW3.git`.
All reported performance comes from the UIUC VM, never Windows. Run the
following from a Linux checkout. The final README identifies the selected source.

## Build and execute an archived variant without replacing existing outputs

```bash
git clone git@github.com:amoch88/CS598APE-HW3.git
cd CS598APE-HW3
git switch hw3-final
make clean all
mkdir -p results
RUN=$(mktemp -d "$PWD/results/manual-XXXXXX")
(cd "$RUN" && taskset -c 0 "$OLDPWD/sandpile.exe" 1001)
```

`identity.png` is written in the current directory; a fresh directory prevents
replacing a prior image. The Makefile uses `gcc -O3 -lm -g -Werror`.
For a decoded comparison with the supplied reference, from the repository root:

```bash
PYTHONPATH=scripts python3 - "$RUN/identity.png" <<'PY'
import pathlib, sys
from png_pixels import compare
print(compare(pathlib.Path('identity-ref.png'), pathlib.Path(sys.argv[1])))
PY
```

This image check supplements, rather than replaces, the full integer checks below.
Requirements for builds: GCC, Make and libm. Experiment tools: Python 3 standard
library, GNU time, util-linux taskset, Git, GNU tar, Valgrind and binutils for
profiling. CPU 0 must be available. Plotting alone requires the pinned packages
in `scripts/plot-requirements.txt`; it is not a build/test dependency.

## Existing VM evidence

Preserved baseline:
`results/20261110T013855Z-baseline` (`results/latest-baseline`).
Preserved row-interval study:
`results/20261110T023926Z-row-intervals` (`results/latest-row-intervals`).
New checked batching:
`results/20261110T033438Z-batch`.
FIFO unit screening:
`results/20261110T035004Z-worklist-unit`.
FIFO batched screening:
`results/20261110T035055Z-worklist-batch`.
Overflow-bound batching:
`results/20261110T035148Z-batch-bounded`.

Large result directories are ignored by Git and stay on this VM. The committed
`measurements/final-study` directory contains compact raw observations, provenance,
correctness reports and profiler extracts; figures are under `figures/final`.
Source archives, executables, complete integer grids, PNGs and raw Callgrind
traces are deliberately not added to Git. New runs refuse existing directories.

## Fresh-clone reference and candidate reproduction

First create an original baseline, including frozen integer oracles:

```bash
B="$PWD/results/baseline-$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/reproduce.py --output "$B"
```

This is expensive: it includes three approximately 11-minute original release
runs on the measured VM and a separate target integer-grid calculation. The
existing study reused those results; it did not repeat them for every candidate.
The baseline launcher archives source `15fe837445b8e32a15ac61fcfa388980b54d9173`.

Validate and measure the bounded batching implementation in a fresh directory:

```bash
R="$PWD/results/batch-bound-$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/final_experiment.py \
  --commit 50970858a53845220b44f604e62223c2ea7f1ea1 \
  --name row-batch-bounded --baseline "$B" \
  --row-results "$PWD/results/no-existing-row-study" --output "$R"
python3 scripts/repeat_candidate.py "$R" --runs 3
```

The nonexistent row-study path deliberately selects the fresh-clone path: reuse
baseline goldens and generate only the missing N=501 original grid once. It does
not rerun the row-only timing study. On this VM use the existing row-results path
to reuse its N=501 golden too. The experiment performs all smaller correctness,
stage, arithmetic and memory checks, three small release timings per size, one
target release timing, then a separate full target integer check that reuses the
release PNG. `repeat_candidate.py` accepts only a completed, target-verified
study and appends the other target observations. All image comparisons are outside
the timer. Optional `--deadline YYYY-MM-DDTHH:MM:SS` on either launcher is interpreted
in America/Chicago; command timeouts remain bounded even without a deadline.
Target timing/check commands are capped at 480 seconds in `final_experiment.py`;
this is designed for these optimized variants on comparable VMs, not for timing
the slower original implementation. Use the baseline launcher for the original.

For already-existing VM goldens, pass these instead:

```bash
--baseline "$PWD/results/latest-baseline" \
--row-results "$PWD/results/latest-row-intervals"
```

The invocation above is an argument fragment, not a separate shell command.
`finalize_candidate.py "$R"` performs a clean rebuild, checks byte identity with
the target-validated executable, reruns small correctness and 138 mask cases,
and rechecks all target images. On a fresh clone its golden lookup also uses
`$R/expected`; on the study VM it uses the reused row-study goldens.

## Independent variants

| Configuration | Source commit | Preserved branch |
|---|---|---|
| Original | `15fe837445b8e32a15ac61fcfa388980b54d9173` | `hw3-baseline-study` (infrastructure head differs) |
| Row intervals | `7fd71987e27f00d690e5e0348d5701a76a12ca0b` | `hw3-row-intervals` (evidence head `9082b15`) |
| Rows + checked batching | `ec81307dbe61699fe7409aec0a9694aae7abce6c` | `hw3-batched-topplings` |
| Rows + bounded batching | `50970858a53845220b44f604e62223c2ea7f1ea1` | `hw3-batch-bounded` |
| FIFO unit, row parent | `d4c72a42e28ae690f40aefddd819456ec9d4778b` | `hw3-worklist-unit` |
| FIFO batched, FIFO parent | `c3e5a978bd9b7e7453f795e730f3ebf6a62a0a52` | `hw3-worklist-batch` |

Archive the exact source SHA, not a moving evidence-branch head, for reproduction.
For worklist screening use the corresponding commit and name with
`final_experiment.py --small-max 251 --skip-target`; other arguments are as above.
Checked batching uses the same entrypoint without `--small-max`/`--skip-target`.
The prior row-only study has its own complete reproduction in `docs/ROW_INTERVALS.md`.

Inspect the isolated source changes:

```bash
git diff 9082b15 ec81307 -- sandpile.c
git diff ec81307 5097085 -- sandpile.c
git diff 9082b15 d4c72a4 -- sandpile.c
git diff d4c72a4 c3e5a97 -- sandpile.c
```

The two FIFO histories preserve a direct one-line unit/batch comparison. The
batching branches preserve checked and bounded versions independently. Source
SHAs and source/executable hashes accompany every measured distribution.

## Analysis and figures

The final notes contain the exact commands used to aggregate this study's paths.
For any corresponding completed directories, use `scripts/summarize_final.py
--baseline B --row ROW --studies STUDY1 STUDY2 ... --output NEW_DIRECTORY`.
It copies compact evidence unchanged and derives tables from raw CSV values.

```bash
python3 scripts/setup_plotting.py
results/plot-venv/bin/python scripts/plot_final.py \
  measurements/final-study/summary.json --output figures/final
```

On the measured VM, venv/pip bootstrapping was necessary because system Python
had no pip/ensurepip. `setup_plotting.py` uses that same bootstrap procedure when needed. An isolated
ignored `results/plot-venv` was used; no sudo or
system package changes were made. The package lock records actual installed
versions. Plots are PDF and SVG, with editable text and vector geometry. Their
whiskers show measured min?max ranges, not confidence intervals. Worklist lines
stop at the largest measured N; absent full-size results are not extrapolated.

`python3 scripts/profile_final.py STUDY1 STUDY2` obtains bounded N=101 Callgrind
profiles in fresh subdirectories and compares output pixels. Raw traces stay
ignored. The baseline/row instruction results already exist in their studies.
Do not mix profiler or adapter timings with release measurements.

## Auditing failures and limitations

A variable shadowing bug in the new harness occurred after each FIFO variant
had passed correctness/memory checks and saved its first release `run.json`.
It affected timing logging, not the algorithm or measured process. The fix is
commit `6395e03`. Recovery revalidated the saved PNG, retained that observation,
and ran only missing small repetitions. Original errors and interruption records
remain in compact evidence. `resume_small_timings.py` is for that documented
historical interruption; a fresh run with the fixed launcher needs no recovery.

There are no full-target FIFO measurements or full-target FIFO integer claims
unless explicitly listed in the final results. Historical cohorts are not paired;
three repetitions are limited evidence, and 0.01-second timer resolution affects
small-size ratios. See `docs/FINAL_METHODS.md` for exact mathematical arguments,
correctness scope, profiling limits, legacy large-N limitations and deferred work.
