# Clean four-commit submission history

This submission history was reconstructed from preserved, correctly measured C
snapshots. **The reconstructed commits are new commits, not the original measured
commits.** No optimization or measurement was changed by this history cleanup.
The original measurement SHAs remain unchanged in every saved manifest/report.

Starter baseline: `15fe837445b8e32a15ac61fcfa388980b54d9173`.
Previous final artifact: `4014209c48f41173aa7359a6226aab445def0a90`.
Pushed backup branch: `hw3-final-before-four-commits-20261110T094313Z`.
The original experimental branches and evidence remain intact. A full clone
fetches these preserved objects, which the evidence-audit scripts reference.

| Order | Reconstructed submission commit | Purpose | Original measured source |
|---|---|---|---|
| 1 | `8f5753bf0240229477bace6ced0438244a3953f5` | Precompute active row intervals | `7fd71987e27f00d690e5e0348d5701a76a12ca0b` |
| 2 | `1a2c179657ea90a53761801755ed10ad0ba4a0e1` | Batch topplings with an overflow-safe bound and checked fallback | `50970858a53845220b44f604e62223c2ea7f1ea1` |
| 3 | `e4c2a64b041f4e63ccf1cddd416b3451626586ca` | Pad boundaries to remove neighbor checks | `1080490846c96703f0734771560e729b9224cf73` |
| 4 | Tip of `hw3-submission-clean` / cleaned `hw3-final` | Alternate sweep directions and finalize the reproducible artifact | `245fad1455fe7dd9033b64732e259534c40cd5a0` |

The fourth commit is this document's containing commit. Its stable branch tip
is used above to avoid a fabricated self-referential commit hash; obtain the
exact hash with `git rev-parse hw3-submission-clean` (or the cleaned `hw3-final`).
The delivery summary records its full hash. These four commits are linear and
are the only commits after the starter baseline on the cleaned branch.

## Snapshot correspondence

1. Row intervals use `sandpile.c` from `9082b1522ced1283e635a8741748d3bb32521425`.
   That file is byte-identical to the actual measured source
   `7fd71987e27f00d690e5e0348d5701a76a12ca0b` recorded in the row study.
2. Bounded batching uses `50970858a53845220b44f604e62223c2ea7f1ea1` verbatim,
   including its once-per-stabilization positive-grain bound and overflow-checked
   fallback. The earlier slower checked-only batching experiment is not introduced
   as a separate submission commit.
3. Padding uses `1080490846c96703f0734771560e729b9224cf73` verbatim.
4. Alternating sweeps use the final combined source
   `245fad1455fe7dd9033b64732e259534c40cd5a0` verbatim, also the C file in the
   previous final artifact `4014209c48f41173aa7359a6226aab445def0a90`.

All four C Git blobs and SHA256 hashes are recorded in
`measurements/history-cleanup/snapshot-map.json`. The final C SHA256 remains
`7dad0f3a4122f2d4e3e9693ccb9b2ec0a2ea5c4e07975b872a397d1664144b41`.
The Makefile, compiler flags (`-O3 -lm -g -Werror`), bundled PNG library and
reference image match the previous validated artifact. Its scripts, tests,
measurement files and figures are preserved byte-for-byte. Only supplementary
history documentation is added to the existing README/reproduction/report notes.

## Verification and interpretation

The first three commits each build independently using their own archived
Makefile and C source. Each passed 61 quick correctness checks through N=251;
stages 2 and 3 also passed all four arithmetic-bound/fallback cases. The final
draft is clean-built and receives quick integer, arithmetic, sanitizer, Memcheck,
mask and compact-evidence checks before the fourth commit is created. Exact
outcomes are in `measurements/history-cleanup/verification.json`.

No new N=1001 calculation or benchmark is run. Existing target correctness and
performance results apply by exact production-source/build-configuration identity,
not by pretending the new hashes were historically measured. Existing numerical
manifests and performance tables retain their original measured commit IDs.

The original report/README generators still regenerate the original measured
artifact's content; these supplementary history appendices are intentionally
maintained separately. All expensive reproduction commands and source references
in FINAL_REPRODUCTION.md remain valid through the preserved backup/experiment refs.

To inspect only the cleaned optimization history:

```bash
git log --first-parent --reverse --format='%H %s' \
  15fe837445b8e32a15ac61fcfa388980b54d9173..hw3-final
git rev-list --count 15fe837445b8e32a15ac61fcfa388980b54d9173..hw3-final
```

The count must be exactly four. The remote final update uses an explicit lease
against `4014209c48f41173aa7359a6226aab445def0a90` and is attempted only after verification succeeds.
