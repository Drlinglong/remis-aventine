# ZH–EN fixed-anchor incremental evaluation, 2026-09-25

This revision adds models without replaying the historical 17-model tournament.
The sealed v0.3 exam, 44 translation prompts, two repetitions, deterministic
validators, and 60% soft / 40% hard formula remain unchanged. A new judge panel
and a new opponent panel require a new score version. Historical scores remain
available under `v0.3-zh-en-60soft-40hard`; incremental placements use
`v0.3-zh-en-anchors-20260925-v1`. Scores from these versions must not be mixed
into one ranking or Pareto frontier.

## Independent judges and cost accounting

The priority pool is MiMo V2.6 Pro, GPT-6 Luna, and DeepSeek V4.1 Flash, accessed
through OpenRouter. Exclude every contestant's whole model family before
selecting two judges. Thus GPT-6 Sol also excludes GPT-6 Luna. Each judge sees
anonymous candidates. Primary pairwise presentations use opposite orders;
20% of sampled cases receive additional swapped-order checks.

Gemini 3.8 Flash is a fallback when primary judgments are missing or disagree.
At least two matching valid votes are necessary. A lone successful fallback
never resolves a case; position-inconsistent audit cases remain unresolved.
If a future pair excludes two priority families, Gemini may fill the missing
independent seat. The three fixed anchors avoid that exception in this cohort.
Grok is outside this panel.

Judge calls have no client output-token cap. Provider failures, structured-JSON
failures, fallback calls, and audit calls retain their receipts. Only explicit
HTTP 429 responses receive bounded automatic retries (three attempts total).
Uncertain in-flight calls are not silently repeated. Pre-dispatch budget guards
are estimates, not a guarantee on uncapped provider charges. Exact observed
OpenRouter costs and token estimates are distinct; missing costs are not zero.
Translation cost is the chart's x-axis; judge cost is reported separately.
The incremental artifact reports `judge_cost_missing_calls`. When nonzero, the
website labels the judge total as a lower bound and shows the unverified count.
Generation billing metadata can reconcile a missing fee without resending the
request. Persisted responses can likewise restore an interrupted checkpoint
through local schema validation; recovered responses do not become extra votes.

The synthetic contract smoke checks JSON compliance and obvious correct/wrong
translations. Passing it is not evidence of human-calibrated judge accuracy or
proof that a model lies on the translation-judge Pareto frontier.

## Frozen opponent panel

| Role | Frozen historical translation outputs |
| --- | --- |
| High | `qwen/qwen3.8-max` |
| Middle | `meta/muse-spark-1.2` (age-confirmed run) |
| Low | `upstage/solar-pro4` |

These anchors were chosen from historical scores before new soft judgments and
belong to none of the priority judge families. Reuse their frozen translations;
only structural ambiguities are reviewed with the new panel. The private
manifest records exam, execution-plan, anchor-run, and execution-identity hashes.
Its hash is included in the public result.

For each entrant and anchor, deterministically sample up to ten eligible
occurrences per language direction with seed `20260925`. Deterministic hard
failures and unresolved structural reviews cannot enter soft comparisons.
The maximum is 60 soft cases per entrant. Eligibility and unresolved decisions
can change the effective sample; report both hard and soft coverage alongside
scores. Every anchor must contribute resolved evidence in both directions.

For each direction, soft score is `100 × (wins + 0.5 × ties) / resolved cases`.
Losses and `neither` receive zero points. Hard score is the resolved hard pass
rate, including deterministic failures in its denominator. Direction score is
`0.6 × soft + 0.4 × hard`; the bilingual score averages both directions equally.
The soft score pools resolved anchor cases; it is not a fitted Bradley–Terry
rating, and unequal resolution can change effective anchor weights. This is a
small, coverage-qualified benchmark, not a significance claim.

## Incremental publication and model selection

The cohort evaluates MiMo V2.6 Pro, DeepSeek V4.1 Flash, and GPT-6 Sol, and places
existing GPT-6 Luna outputs with the same anchors. GPT-5.6 Luna and DeepSeek V4
Flash outputs are also placed on this scale so users can compare generations.
Step 5 Preview is skipped at the user's request.

The website defaults to the newest available version within each explicit
product line. A searchable selector can add/remove individual models, select
all, clear, or restore defaults. The selection applies jointly to tables,
ranked charts, and the Pareto frontier and persists per score version. Historical
data remain accessible in a separate view. Vendor identity alone is not a
product line: Pro, Flash, and small models may coexist.

Public artifacts contain scores, coverage, telemetry, model IDs, and provenance
hashes only. Sealed questions, translations, raw receipts, and judge rationales
remain in the private benchmark corpus.

## Reproduction

The completed six-profile publication contains 360 soft cases, with unresolved
cases retained. Scores are DS V4.1 Flash 81.11, GPT-6 Sol 76.90, MiMo V2.6 Pro
74.20, GPT-6 Luna 64.19, GPT-5.6 Luna 62.99, and DS V4 Flash 50.50. These are
coverage-qualified placements, not significance claims.

Verified panel judging cost is at least $3.287166, including $0.289058 of shared
anchor review; three calls still have unverified cost. Gemini fallback accounts
for $1.619114, about 49% of verified judging cost. The Luna placement costs
$0.593558 in judging versus $0.02492947 for its reused translation run, so the
cost inversion remains despite the cheaper priority pool. Comparison with the
previous $1.811030 judging ledger uses different sample sizes and is not a
controlled savings estimate.

Public panel adapter: `src/remis_aventine/priority_panel.py`.
Private corpus scripts: `run_priority_candidates.py`,
`prepare_priority_anchors.py`, `run_priority_judges.py`, and
`summarize_priority_anchors.py`. Frozen plans and durable checkpoints permit
resuming only undispatched calls under the same identity. Do not regenerate
historical scores, replace provider/model versions behind old identities, or
change an already-dispatched plan to obtain a preferred result.
