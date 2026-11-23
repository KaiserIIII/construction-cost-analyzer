# Contributing to Construction Cost Analyzer

Thanks for helping improve the estimating and development-appraisal toolkit. Small, reproducible changes with clear calculation assumptions are especially welcome.

## Before proposing a change

1. Check existing issues and describe the expected behavior, units, price basis, and rounding rule.
2. Keep changes focused. A defect fix should include a regression test; a change to a published formula or dataset should explain its provenance and compatibility impact.
3. Use synthetic or openly licensed examples. Never commit client quotations, project-identifying records, credentials, or private construction documents.
4. Keep generated outputs, local environments, and temporary reports out of commits.

## Run the project and tests

Python 3.10 or later is required for the core application and test suite. From the repository root:

```bash
python -m cost_analyzer serve
python -X utf8 -m unittest discover -s tests -v
```

The local browser workspace uses `http://127.0.0.1:8765/`. Test and validate your changed command or workflow using a small input from `examples/`. Additional utilities may require optional packages; see `README.md`, `requirements.txt`, and `docs/toolchain.md`.

## Calculation and data integrity

- Preserve `Decimal`-based monetary calculations, explicit rounding stages, and units.
- Distinguish direct cost from preliminaries, overheads/profit, contingency, fees, and VAT. Check for double-counting.
- Record the source, release date, geographic scope, currency, index basis, and license of new reference data.
- Label illustrative/synthetic scenarios as such; do not present them as observed market prices.
- Keep original inputs and calculation assumptions traceable in reports and exports.
- Add edge-case tests for malformed inputs, nonconventional cash flows, numerical boundaries, and differing cost scopes where relevant.

## Pull requests

Explain **what changed**, **why**, and **how you verified it**. Link the related issue, include sample input/output if calculations changed, and note any known limitations. The existing GitHub Actions checks are an additional safeguard, not a substitute for local tests. For reporting a security vulnerability, avoid posting an exploit or sensitive details in a public issue; contact the maintainer privately.

See the [method notes](docs/course-methods.md), [data sources](docs/data-sources.md), and [export formats](docs/exports.md) for project-specific conventions.
