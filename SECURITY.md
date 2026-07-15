# Security Policy

## Supported versions

Aventine is pre-alpha. Security fixes are applied to the latest `main` branch until the first stable
release policy is published.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting for this repository when available. Do not include API
keys, private benchmark samples, proprietary translations, or other secrets in a public issue.

The highest-risk areas are provider credential handling, malicious benchmark content embedded in
judge prompts, unsafe artifact deserialization, path traversal in adapters, and accidental leakage of
private translation data into reports.
