# Demo Release Candidate (RC1)

## Scope frozen
- Replay evaluation fixtures locked for four synthetic scenarios: happy path, uncertain buyer, high-friction finance concerns, and early drop-off.
- KPI rubric locked to: response relevance, follow-up quality, extraction accuracy, and pain-point detection precision.
- Release gate enforced via unit test requiring KPI thresholds.

## Evaluation snapshot
- KPI deltas are computed against baseline values inside `run_replay_evaluation`.
- Composite score uses tuned scoring weights with normalized contribution by metric.

## Known limitations
1. Replay scoring is heuristic and deterministic (rule-based), not model-judged.
2. Scenario corpus is intentionally small (4 fixtures) for demo speed; broader generalization not guaranteed.
3. Baseline comparator values are static constants and should be replaced with persisted historical runs in production.
4. Follow-up quality metric is proxy-scored by scenario class, not transcript-level grader.
5. Pain-point precision is measured per-session with keyword taxonomy and may miss nuanced concerns.
