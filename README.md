# Aventine

[![CI](https://github.com/Drlinglong/remis-aventine/actions/workflows/ci.yml/badge.svg)](https://github.com/Drlinglong/remis-aventine/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

**A reproducible evaluation ground for translation recipes, born from
[Remis](https://github.com/Drlinglong/Remis).**

Aventine evaluates complete translation pipelines, not isolated model names. A recipe may include
a provider, model revision, prompts, decoding settings, context, glossary handling,
post-processing, repair, and optional deterministic validators.

> Status: pre-alpha. The repository provides versioned recipe, run-result, and judge contracts;
> deterministic calibration summaries; synthetic MQM/ACES fixtures; and a read-only Remis result
> adapter. It does not yet execute a full Aventine-native benchmark.

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
aventine --version
```

`doctor` is read-only. It does not download datasets or run models. The validation commands check
documents against the packaged, versioned JSON Schemas. The calibration command counts malformed
judge output as benchmark failure and reports recall, false-good, pairwise, confidence, phenomenon,
and confusion metrics. The Remis adapter converts existing
`evaluate_translation_quality.py` artifacts without copying raw provider responses.

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

Planned optional baselines include xCOMET and `mt-metrics-eval`. Aventine is CLI-first; no graphical
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
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Name

In the Roman foundation myth, Remus observes the augury from the Aventine Hill. The name connects
this evaluation ground to Remis without making it a Remis-only component.

## License

Code and repository-authored content are licensed under the
[GNU Affero General Public License v3.0](LICENSE). External datasets, model weights, and imported
annotations retain their upstream licenses and must not be committed to this repository.
