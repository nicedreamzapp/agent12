# Contamination policy — public tasks, held-out tasks, rotation

Public benchmarks leak into training data. Agent-12 assumes its public tasks
WILL eventually be trained on, and is structured so that doesn't quietly
corrupt the scoreboard.

## The three pools

1. **Public pool (this repo).** The 12 easy + 8 hard tasks, fully published:
   setup, prompts, judges, reference solutions. Anyone can reproduce any row.
2. **Held-out pool (private).** A parallel set of tasks of matched shape and
   difficulty (same categories: create/run, bug-fix with pinned tests, spec
   gauntlet, parsing-with-a-ban, etc.) that is never published. Held-out
   judges pass the same known-good/known-bad validation gate before use.
3. **Retired pool.** Tasks rotated out of the public pool stay visible in git
   history and remain runnable, but no longer count toward the headline score.

## Rotation

- On a regular cycle (and immediately if a task shows up in a model's
  verbatim training regurgitation), tasks rotate: public tasks retire,
  held-out tasks are promoted to public, and new held-out tasks are written.
- The suite version is stamped into every result (`harness_version`), and the
  scoreboard never mixes rows from different suite versions in one table.

## The contamination tell

Every new scoreboard entry runs both pools. The public/held-out gap is
reported per model. A model that aces the public pool and craters on the
held-out pool of matched difficulty earns a ⚠ contamination flag on its row —
the number stays, the flag tells you how to read it.

## Re-benchmarking

Because old rows can't be re-run on retired suites forever, each row records
suite version + exact weights + harness commit. Any row can be reproduced
bit-for-bit as long as the weights remain available.
