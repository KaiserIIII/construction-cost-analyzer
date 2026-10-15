# Development input review implementation plan

> For agentic workers: execute inline using the existing calculation engine and test-first changes.

**Goal:** Make missing assumptions visible before users rely on development estimates.

**Architecture:** `cost_analyzer.review.review_development` returns a structured review containing issues, status, programme records and an input SHA-256. The CLI prints/saves that review and maps status to an exit code. Optional housing sales metadata passes through the existing engine and browser CSV.

**Tech stack:** Python 3.10+ standard library; existing JavaScript browser workspace.

## Constraints

No new dependencies, network calls, personal coursework data, grade predictions or certification claims. Existing calculation behavior stays compatible. Explicit zero is valid and distinct from absent input. Evidence presence is not evidence verification.

## Tasks

- [x] Add boundary tests in `tests/test_review.py`: missing defaults, explicit zeros, inherited option settings, sales evidence distinct from cost evidence, date order, assumed/asking price warnings, repeatable input hashing, invalid engine input, CLI exit codes and saved JSON.
- [x] Run those tests before implementation and confirm missing review behavior fails.
- [x] Add `review.py`; extend optional housing metadata validation in `development.py`; retain it through `web.py` and `static/app.js` CSV handling; add `review` CLI command.
- [x] Run targeted and complete standard-library suites. Verify an exported synthetic housing CSV preserves sales references/dates and existing estimate totals are unchanged. Include a regression check that a review cannot overwrite its original input.
- [x] Document command and limits in English/Chinese READMEs and `docs/development-workflow.md`. Add a complete synthetic review example.
- [x] Check the diff for private material, commit the tested change on a feature branch and publish a reviewable GitHub change. Draft PR #1 records the change and all 113 passing local tests (97 existing plus 16 added).
- [x] Create the classmate basic guide with accurate basic steps and a transparent project recommendation; render and inspect all four pages. The user requested sufficient detail without sharing private coursework calculations.
