# Contributing Guide

Thank you for your interest in contributing! This guide explains how to set up your environment, propose changes, and comply with our security and community standards.

## Getting Started

- Requirements: Python >= 3.10
- Package manager: `uv` (https://github.com/astral-sh/uv)

Setup:

```
uv sync --dev
```

Run checks locally:

```
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/ --strict
uv run bandit -r src/adk_agui_middleware --skip B101,B601
PYTHONPATH=$PWD/src uv run python -m unittest discover -s tests -p "test_*.py" -v
```

## Development Flow

- Branching: create feature branches from `main` (e.g., `feat/...`, `fix/...`).
- Commit messages: concise, imperative style (e.g., "fix: handle SSE errors").
- Tests: add/update tests for new behavior; keep coverage healthy.
- Lint/Type/Security: ensure Ruff, mypy, Bandit pass before opening a PR.

## Pull Requests

- Target branch: `main` (unless release/hotfix).
- Required checks (CI): lint, type, tests, security scan, CodeQL (see below).
- Reviews: at least 1 approving review recommended; more for risky changes.
- Docs: update `README.md` and any relevant docstrings or examples.

## Security

- Never commit secrets (tokens, passwords, API keys). Use environment variables or secret managers.
- Before publishing: run internal and GitHub secret scans; fix alerts promptly.
- Vulnerability reports: see `SECURITY.md` for how to report and coordinate fixes.

## Repository Health & Governance

- Issue triage: respond within a reasonable time; label and prioritize.
- Dependency updates: handled via Dependabot; review and merge regularly.
- Release process: tag and publish via GitHub Releases; PyPI publish is automated.

## Branch Protection (Required - set in GitHub UI)

Maintain protection on sensitive branches (e.g., `main`):

1) Repository → Settings → Branches → Add rule → Branch name pattern: `main` (repeat for `develop`).
2) Enable:
    - Require a pull request before merging (with at least 1 approval).
    - Require status checks to pass before merging (select checks from the CI workflow and CodeQL; enable "Require branches to be up to date").
    - Require conversation resolution before merging.
    - Require signed commits (suggested; see below).
    - Lock branch (optional) for release stabilization.

## Commit Signature Verification (Suggested)

Enable repo-level requirement (Settings → Branches → Require signed commits), and configure your local signing:

GPG setup:

```
gpg --full-generate-key
gpg --list-secret-keys --keyid-format=long
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
```

SSH signing (alternative): https://docs.github.com/en/authentication/using-ssh/ssh-key-signing

## Personal Access Token Expiration

For any personal tokens used with this repo, set an expiration and rotate regularly. See: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token

## How to Contribute

1) Fork → create a feature branch → implement changes → add tests.
2) Run local checks (lint, type, tests, bandit).
3) Open a PR with a clear description, screenshots/logs as needed.
4) Address review feedback. Ensure CI and CodeQL are green.

Thank you for contributing to a secure and healthy open source project!

