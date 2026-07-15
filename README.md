# Aventine

[![CI](https://github.com/Drlinglong/remis-aventine/actions/workflows/ci.yml/badge.svg)](https://github.com/Drlinglong/remis-aventine/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

**A reproducible evaluation ground for translation recipes, born from
[Remis](https://github.com/Drlinglong/Remis).**

Aventine evaluates complete translation pipelines, not isolated model names. A recipe may include
a provider, model revision, prompts, decoding settings, context, glossary handling,
post-processing, repair, and optional deterministic validators.

> Status: pre-alpha. The repository provides versioned recipe, run-result, and judge contracts;
> deterministic calibration summaries; a reproducible 48-case multilingual calibration pack;
> bounded DeepSeek V4 Pro, xAI Grok 4.5, and Google-hosted Gemma 4 judge adapters; synthetic
> fixtures; bounded `mt-metrics-eval` MQM and ACES/SPAN-ACES adapters; a read-only Remis
> result adapter; hard-veto-aware Remis pairwise/repair-restraint reports; and isolated,
> schema-bound MetricX-24/xCOMET baselines with gold/judge/metric alignment reports. A recorded
> four-recipe Remis pilot now exercises the complete compatibility and evaluation path.
> It does not yet execute a full Aventine-native recipe benchmark.

## Why Aventine?

Translation evaluation already has strong individual components: WMT/MQM data,
`mt-metrics-eval`, COMET/xCOMET, ACES, and LLM judges. Aventine connects those components into a
developer-oriented regression workflow with explicit trust boundaries and reproducible artifacts.

The project follows four rules:

1. **Hard validators have veto power.** An LLM judge cannot rescue a structurally unsafe output.
2. **The judge evaluates soft quality.** Semantics, terminology, style, naturalness, and
   repair-track over-editing belong to the judge.
3. **Judge output is structured data.** Parse failures are benchmark failures, not prose to guess at.
4. **External datasets stay external.** Large WMT/ACES downloads and generated results do not enter Git.

## Core workflow

```text
recipe manifest
    -> adapter executes translation / repair stages
    -> deterministic validators apply optional vetoes
    -> automatic metrics and a calibrated judge inspect eligible outputs
    -> aggregator writes a versioned result artifact
    -> reports compare recipes, failure modes, latency, and confidence
```

The judge is calibrated against small samples derived from professional human evaluation and
contrastive challenge sets. Those external resources calibrate the evaluation tool; they do not
replace project-specific frozen benchmarks or user preference data.

## Quick start

```bash
git clone https://github.com/Drlinglong/remis-aventine.git
cd remis-aventine
python -m venv .venv
python -m pip install -e ".[dev]"

aventine doctor --json
aventine validate-recipe examples/recipes/remis-lm-studio.example.json
aventine summarize-calibration examples/calibration/fake-mqm-v1.json --json
pytest --cov
```

On PowerShell, activate the environment with `.venv\Scripts\Activate.ps1` if desired. Activation is
optional when invoking the environment's Python directly.

## CLI

```text
aventine doctor [--remis-root PATH] [--json]
aventine validate-recipe PATH [--json]
aventine validate-result PATH [--json]
aventine validate-judge PATH [--json]
aventine summarize-calibration PATH [--json]
aventine adapt-remis-result INPUT OUTPUT [--recipe-id ID] [--json]
aventine build-remis-pairwise-pack LEFT_RUN RIGHT_RUN OUTPUT [--json]
aventine report-remis-pairwise INPUT OUTPUT_JSON OUTPUT_MARKDOWN [--json]
aventine build-calibration-pack SOURCE_ROOT OUTPUT [--remis-fixture PATH] [--json]
aventine build-mtme-mqm-pack TEST_SET LANGUAGE_PAIR RATING_SET DATASET_REVISION OUTPUT
  [--data-root PATH] [--limit N] [--system NAME] [--json]
aventine build-aces-pack INPUT OUTPUT --kind aces|span-aces --dataset-revision REVISION
  --expected-sha256 SHA256 [--limit N] [--language-pair PAIR] [--phenomenon NAME] [--json]
aventine run-judge INPUT OUTPUT [--case-id ID] [--max-calls N] [--workers N]
  [--provider deepseek|xai|google] [--resume-from PATH] [--env-file PATH] [--json]
aventine run-metric INPUT OUTPUT --metric metricx-24|xcomet --runtime-python PATH
  --model-path PATH --model-id ID --model-sha256 SHA256 [--mode qe|reference]
  [--tokenizer-path PATH] [--metricx-source PATH] [--hf-home PATH] [--json]
aventine build-metric-pack CALIBRATION_PACK OUTPUT [--json]
aventine report-metric-calibration METRIC_PACK METRIC_RESULT OUTPUT_JSON OUTPUT_MARKDOWN
  [--json]
aventine report-evidence-alignment CALIBRATION_PACK JUDGE_RESULT OUTPUT_JSON OUTPUT_MARKDOWN
  --metric METRIC_PACK METRIC_RESULT [--metric METRIC_PACK METRIC_RESULT ...] [--json]
aventine --version
```

`doctor` is read-only. It does not download datasets or run models. The validation commands check
documents against the packaged, versioned JSON Schemas. The calibration command counts malformed
judge output as benchmark failure and reports recall, false-good, pairwise, confidence, phenomenon,
and confusion metrics. The Remis adapter converts existing
`evaluate_translation_quality.py` artifacts without copying raw provider responses.

The Remis V4 path stays artifact-first. Adapt two production-backed benchmark outputs, build the
pairwise pack, reuse the existing judge, then render JSON and Markdown reports:

```text
aventine adapt-remis-result remis-a.json a.json
aventine adapt-remis-result remis-b.json b.json
aventine build-remis-pairwise-pack a.json b.json pairwise.json
aventine run-judge pairwise.json judged.json --provider deepseek --max-calls 100
aventine report-remis-pairwise judged.json report.json report.md
```

Cases decided by execution status or hard-validator veto are excluded from judge calls. Eligible
cases are evaluated in both A/B orders; position-inconsistent judgments remain unresolved. Repair
reporting reuses Remis's `valid_items_unchanged` and `reference_exact_match` evidence.

The real multilingual pack is rebuilt from SHA-256-pinned external MQM/ACES files. Raw upstream
text and generated judge results remain outside Git. `run-judge` reads the selected provider's
`DEEPSEEK_API_KEY`, `XAI_API_KEY`, or `GEMINI_API_KEY` from the process environment or a Git-ignored
project `.env`, enforces a total HTTP request budget, retries transient/empty JSON responses, strips
reasoning content, and can resume only failed outputs from a configuration-compatible artifact. See the
[multilingual calibration guide](docs/zh/developer/multilingual_calibration.md).

Known limitation: `--max-calls` currently caps HTTP attempts, including retries, while the runner also
uses it when checking planned logical outputs. Until these budgets are separated, leave retry headroom
above the planned output count. Split budgets, incremental checkpoints, progress telemetry, and a more
compact long-text judge profile are tracked in
[issue #5](https://github.com/Drlinglong/remis-aventine/issues/5).

`build-mtme-mqm-pack` reads an already-installed, already-downloaded `mt-metrics-eval` EvalSet. It
never downloads the multi-gigabyte WMT bundle itself. The adapter skips unrated segments, preserves
MQM spans and provenance, applies deterministic severity-balanced selection capped at 50 cases by
default, and writes external text/results only to the caller-selected path.

`build-aces-pack` reads a SHA-256-pinned ACES or SPAN-ACES JSONL file and produces pairwise cases
with deterministic candidate order and language-pair/phenomenon coverage. SPAN-ACES annotations are
stored only as human gold and never included in the judge input.

`run-metric` keeps heavyweight and mutually incompatible ML dependencies outside Aventine's core
environment. It launches a caller-selected Python runtime without a shell, uses only local pinned
weights/cache, verifies the model SHA-256, records runtime package versions, and validates both input and
output. MetricX-24 supports reference and QE modes; xCOMET currently requires references. See the
[isolated metric runtime guide](docs/zh/developer/external_metric_runtimes.md).

`build-metric-pack` preserves gold/provenance metadata while flattening a single case to one
hypothesis and a pairwise case to two hypotheses. It excludes missing-reference cases explicitly.
`report-metric-calibration` then reports score distributions for MQM-style single cases and
threshold-free winner accuracy for ACES-style pairs. Raw external text and per-case scores remain in
Git-ignored `benchmark_results`; a hash-only aggregate manifest may be committed.

`report-evidence-alignment` joins the same calibration cases across human gold, a structured judge,
and one or more automatic metrics. It does not invent a pass/fail threshold for continuous MQM
scores. For pairwise cases it reports both-correct, judge-only, metric-only, both-wrong, position
inconsistency, and a review queue.

## Remis compatibility

During the early phases, Aventine intentionally reuses Remis production behavior instead of
reimplementing it. Remis remains the source of truth for provider calls, prompt and glossary
assembly, deterministic validators, and repair execution. The compatibility adapter creates a
validated Aventine result envelope around Remis benchmark artifacts and records a
`compatibility_snapshot` recipe hash. General schemas, calibration, aggregation, and reporting stay
in Aventine core so the dependency can be inverted gradually when those boundaries stabilize.

## Scope

Initial suites:

- `mqm`: calibrate severe-error detection against professional MQM annotations.
- `aces`: test whether a judge detects fluent but meaningfully wrong translations.
- `remis`: compare real game-localization recipes, including translation and repair tracks.

Optional baselines include MetricX-24 and xCOMET. Aventine is CLI-first; no graphical
interface is planned for the initial releases.

## Non-goals

Aventine is not a WMT leaderboard implementation, a translation model trainer, a production
translation approval system, or a self-improving prompt router. It never presents LLM judgments as
human gold labels.

**Aventine is not training a translation model. Aventine is calibrating and running an evaluation
tool for regression testing translation recipes.**

## Documentation

- [中文开发者文档：愿景、边界与核心工作流](docs/zh/developer/vision_and_workflow.md)
- [中文开发者文档：Judge 校准与 Remis 兼容层](docs/zh/developer/calibration_and_remis_compat.md)
- [中文开发者文档：多语言小样本与远程 Judge](docs/zh/developer/multilingual_calibration.md)
- [中文开发者文档：mt-metrics-eval / WMT MQM adapter](docs/zh/developer/mt_metrics_eval_adapter.md)
- [中文开发者文档：ACES / SPAN-ACES adapter](docs/zh/developer/aces_adapter.md)
- [中文开发者文档：MetricX / xCOMET 隔离 runtime](docs/zh/developer/external_metric_runtimes.md)
- [Judge provider 三方对照](docs/zh/developer/judge_provider_comparison_2026-07-15.md)
- [首届 Remis recipe pilot](docs/zh/developer/first_remis_tournament_2026-07-16.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Name

In the Roman foundation myth, Remus observes the augury from the Aventine Hill. The name connects
this evaluation ground to Remis without making it a Remis-only component.

## License

Code and repository-authored content are licensed under the
[GNU Affero General Public License v3.0](LICENSE). External datasets, model weights, and imported
annotations retain their upstream licenses and must not be committed to this repository.
